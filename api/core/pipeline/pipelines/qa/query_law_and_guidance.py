import re

from core.pipeline.base_pipeline import BasePipeline
from core.pipeline.entities.pipeline_entities import PipelineExecutionContext, BasePipelineData
from typing import List, Dict, Any

from core.pipeline.pipelines.qa.service.linyan_service import LinyanService
from libs.helper import try_parse_json_object, determine_language
from core.pipeline.pipelines.rag.simple_rag_pipeline import SimpleRAGPipeline
from core.pipeline.pipelines.llm.simple_llm_pipeline import SimpleLLMPipeline


class QueryLawAndGuidancePipeline(BasePipeline):
    def __init__(self, config: dict):
        super().__init__(config)
        self.pipeline_name = "QueryLawAndGuidancePipeline"

    def process(self, context: PipelineExecutionContext) -> PipelineExecutionContext:
        query = context.query.query
        language = determine_language(query)
        answer = ""
        laws = []
        if language == "chinese":
            answer, laws = self.query_zh_law_and_guidance(query)
            if answer == "":
                answer = self.config.get("default_zh_answer")
            else:
                answer += f"\n回答日期：{self.get_current_date()}"
        else:
            answer, laws = self.query_en_law_and_guidance(query)
            if answer == "":
                answer = self.config.get("default_en_answer")
            else:
                answer += f"\nAnswer date：{self.get_current_date()}"
        result_data = BasePipelineData()
        result_data.data = {
            "code": 200,
            "message": "success",
            "answer": answer,
            "references": [{
                "type": "QA_DATASET",
                "data": [{
                    "fagui": self.deal_linyan_result(laws)
                }]
            }]
        }
        result_data.data_from = "QueryLawAndGuidance"
        context.pipeline_datas.append(result_data)
        return context

    def deal_linyan_result(self, laws):
        linyan_service = LinyanService()
        result = []
        for law in laws:
            res = linyan_service.query_fagui(law)
            if len(res) > 0:
                result.append(res[0])
        return result

    def get_current_date(self):
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d')

    def query_zh_law_and_guidance(self, query):
        query_rag_config = {
            "dataset_ids": self.config["zh_dataset_ids"],
            "retrieval_mode": self.config["retrieval_mode"],
            "tenant_id": self.config["tenant_id"],
            "multiple_retrieval_config": self.config["multiple_retrieval_config"]
        }
        query_rag_pipeline = SimpleRAGPipeline(query_rag_config)
        relevant_docs = query_rag_pipeline.fetch_dataset_retriever(query, query_rag_config)
        context = []
        for doc in relevant_docs:
            context.append(doc.get("content", ""))

        if len(context) == 0:
            return "", []

        query_llm_config = {
            "model": self.config["model"],
            "tenant_id": self.config["tenant_id"],
            "prompt_template": self.config["zh_rag_check_prompt_template"],
        }
        query_llm_pipeline = SimpleLLMPipeline(query_llm_config)
        model_instance, model_config = query_llm_pipeline.fetch_model_config(query_llm_config["model"])
        prompt_messages = query_llm_pipeline.process_prompt_template(query_llm_config["prompt_template"], query, str(context))
        llm_result = query_llm_pipeline.invoke_llm(model_instance, model_config, prompt_messages)
        llm_data_json_str, llm_data_json = try_parse_json_object(llm_result.message.content)
        result = []
        if llm_data_json != {}:
            for index, item in enumerate(llm_data_json["data"]):
                if item == "True":
                    result.append(relevant_docs[index])

        answer_query_context = []
        answer_laws = set()
        for doc in result:
            content = doc.get("content", "")
            filename = doc.get("document", {}).get("name", "")
            if filename.endswith(".docx"):
                filename = filename[:-5]
            elif filename.endswith(".pdf"):
                filename = filename[:-4]
            answer_query_context.append(f"法规/指南名称：{filename}\n{content}")
            answer_laws.add(filename)

        if len(answer_laws) == 0:
            return "", []

        answer_query_llm_config = {
            "model": self.config["model"],
            "tenant_id": self.config["tenant_id"],
            "prompt_template": self.config["zh_prompt_template"],
        }
        answer_query_prompt_messages = query_llm_pipeline.process_prompt_template(answer_query_llm_config["prompt_template"], query,
                                                                     str(answer_query_context))
        answer_query_llm_result = query_llm_pipeline.invoke_llm(model_instance, model_config, answer_query_prompt_messages)
        answer_query_result_str = answer_query_llm_result.message.content
        return answer_query_result_str.replace("```", ""), list(answer_laws)

    def query_en_law_and_guidance(self, query):
        query_rag_config = {
            "dataset_ids": self.config["en_dataset_ids"],
            "retrieval_mode": self.config["retrieval_mode"],
            "tenant_id": self.config["tenant_id"],
            "multiple_retrieval_config": self.config["multiple_retrieval_config"]
        }
        query_rag_pipeline = SimpleRAGPipeline(query_rag_config)
        relevant_docs = query_rag_pipeline.fetch_dataset_retriever(query, query_rag_config)
        context = []
        for doc in relevant_docs:
            context.append(doc.get("content", ""))

        query_llm_config = {
            "model": self.config["model"],
            "tenant_id": self.config["tenant_id"],
            "prompt_template": self.config["en_rag_check_prompt_template"],
        }
        query_llm_pipeline = SimpleLLMPipeline(query_llm_config)
        model_instance, model_config = query_llm_pipeline.fetch_model_config(query_llm_config["model"])
        prompt_messages = query_llm_pipeline.process_prompt_template(query_llm_config["prompt_template"], query,
                                                                     str(context))
        llm_result = query_llm_pipeline.invoke_llm(model_instance, model_config, prompt_messages)
        llm_data_json_str, llm_data_json = try_parse_json_object(llm_result.message.content)
        result = []
        if llm_data_json != {}:
            for index, item in enumerate(llm_data_json["data"]):
                if item == "True":
                    result.append(relevant_docs[index])

        answer_query_context = []
        answer_laws = set()
        for doc in result:
            content = doc.get("content", "")
            filename = doc.get("document", {}).get("name", "")
            if filename.endswith(".docx"):
                filename = filename[:-5]
            elif filename.endswith(".pdf"):
                filename = filename[:-4]
            answer_query_context.append(f"law/guidance name：{filename}\n{content}")
            answer_laws.add(filename)
        answer_query_llm_config = {
            "model": self.config["model"],
            "tenant_id": self.config["tenant_id"],
            "prompt_template": self.config["en_prompt_template"],
        }
        answer_query_prompt_messages = query_llm_pipeline.process_prompt_template(
            answer_query_llm_config["prompt_template"], query,
            str(answer_query_context))
        answer_query_llm_result = query_llm_pipeline.invoke_llm(model_instance, model_config,
                                                                answer_query_prompt_messages)
        answer_query_result_str = answer_query_llm_result.message.content
        return answer_query_result_str.replace("```", ""), list(answer_laws)