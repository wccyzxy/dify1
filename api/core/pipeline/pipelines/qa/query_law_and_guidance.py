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
            if self.config.get("zh_answer_footer") != "":
                answer += f"\n\n{self.config.get('zh_answer_footer')}"
        else:
            answer, laws = self.query_en_law_and_guidance(query)
            if answer == "":
                answer = self.config.get("default_en_answer")
            else:
                answer += f"\nAnswer date：{self.get_current_date()}"
            if self.config.get("en_answer_footer") != "":
                answer += f"\n\n{self.config.get('en_answer_footer')}"
        result_data = BasePipelineData()
        result_data.data = {
            "code": 200,
            "message": "success",
            "answer": answer,
            "references": self.deal_linyan_result(laws, answer)
        }
        result_data.data_from = "QueryLawAndGuidance"
        context.pipeline_datas.append(result_data)
        return context

    def deal_linyan_result(self, laws, answer):
        linyan_service = LinyanService()
        fagui_regex = r'《(.*?)》'
        fagui_titles = re.findall(fagui_regex, answer, re.UNICODE | re.DOTALL)
        result = []
        for fagui_title in fagui_titles:
            res = linyan_service.query_fagui(fagui_title)
            if len(res) > 0:
                data = res[0]
                data["law"] = fagui_title
                result.append(data)
        
        new_laws = []
        for law in laws:
            doc_name = law.get("metadata", {}).get("document_name", "")
            for item in result:
                if item["law"] in doc_name:
                    law["metadata"]["fagui"] = item
                    new_laws.append(law)
        return new_laws

    def get_current_date(self):
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d')

    def query_zh_law_and_guidance(self, query):
        config = self.config["multiple_retrieval_config"]
        config['top_k'] = 10
        query_rag_config = {
            "dataset_ids": self.config["zh_dataset_ids"],
            "retrieval_mode": self.config["retrieval_mode"],
            "tenant_id": self.config["tenant_id"],
            "multiple_retrieval_config": config
        }
        print(f"multiple_retrieval_config: {config}")
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
        prompt_messages = query_llm_pipeline.process_prompt_template(query_llm_config["prompt_template"], query,
                                                                     str(context))
        print(f"query_llm_message: {prompt_messages}")
        llm_result = query_llm_pipeline.invoke_llm(model_instance, model_config, prompt_messages)
        llm_data_json_str, llm_data_json = try_parse_json_object(llm_result.message.content)
        print(f"llm_data_json_str: {llm_result.message.content}")
        result = []
        if llm_data_json != {}:
            for index, item in enumerate(llm_data_json["data"]):
                if item == "True":
                    result.append(relevant_docs[index])

        answer_query_context = []
        answer_laws = []
        for doc in result:
            print(f"doc: {doc}")
            content = doc.get("content", "")
            filename = doc.get("title", "")
            if filename.endswith(".docx"):
                filename = filename[:-5]
            elif filename.endswith(".pdf"):
                filename = filename[:-4]
            filename = filename.split(".")[-1]
            answer_query_context.append(f"法规/指南名称：{filename}\n{content}")
            answer_laws.append(doc)

        if len(answer_laws) == 0:
            return "", []

        answer_query_llm_config = {
            "model": self.config["model"],
            "tenant_id": self.config["tenant_id"],
            "prompt_template": self.config["zh_prompt_template"],
        }
        answer_query_prompt_messages = query_llm_pipeline.process_prompt_template(
            answer_query_llm_config["prompt_template"], query,
            str(answer_query_context))
        print(f"answer_query_prompt_messages: {answer_query_prompt_messages}")
        answer_query_llm_result = query_llm_pipeline.invoke_llm(model_instance, model_config,
                                                                answer_query_prompt_messages)
        answer_query_result_str = answer_query_llm_result.message.content
        return answer_query_result_str.replace("```", ""), answer_laws

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