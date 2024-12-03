import re
from libs.helper import determine_language
from core.pipeline.base_pipeline import BasePipeline
from core.pipeline.entities.pipeline_entities import PipelineExecutionContext, BasePipelineData
from core.pipeline.pipelines.qa.service.linyan_service import LinyanService
from typing import List, Dict, Any
from extensions.ext_database import db
from models.dataset import Dataset, Document, DocumentSegment
from sqlalchemy import func
from core.rag.retrieval.dataset_retrieval import DatasetRetrieval
from core.rag.retrieval.retrieval_methods import RetrievalMethod
from core.app.app_config.entities import DatasetRetrieveConfigEntity


class DealQueryQAPipeline(BasePipeline):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.pipeline_name = "DealQueryQAPipeline"

    def process(self, context: PipelineExecutionContext) -> PipelineExecutionContext:
        qa_data = context.pipeline_datas[-1].data
        print(f"qa_data: {qa_data}")
        result_data = BasePipelineData()
        qa_dataset_result = self.deal_qa_dataset(context.query.query, qa_data)
        high_related_qas = qa_dataset_result.get("high_related_qas", [])
        middle_related_qas = qa_dataset_result.get("middle_related_qas", [])
        low_related_qas = qa_dataset_result.get("low_related_qas", [])
        if len(high_related_qas) > 0:
            highest_related_qa = high_related_qas[0]
            answer = highest_related_qa.get("answer", "")
            result_data.data = {
                "code": 200,
                "message": "success",
                "answer": answer,
                "references": [{
                    "type": "QA_DATASET",
                    "data": [{
                        "question": highest_related_qa.get("question", ""),
                        "answer": highest_related_qa.get("answer", ""),
                        "score": highest_related_qa.get("score", 0),
                        "fagui": self.deal_linyan_result(answer) if len(answer) > 0 else []
                    }]
                }]
            }
        elif len(middle_related_qas) > 0:
            answers = [qa.get("answer", "") for qa in middle_related_qas]
            answer = "请问您是想问下面的问题吗：\n\n"
            for index, item in enumerate(answers, start=1):
                answer += f"    {index}. {item}\n"
            answer += "\n\n请输入上面的问题，或者提供更多的信息进行提问"
            result_data.data = {
                "code": 200,
                "message": "success",
                "answer": answer,
                "references": []
            }
        elif len(low_related_qas) > 0:
            result_data.data = {
                "code": 300,
                "message": "success",
                "answer": "",
                "key": "query_fagui",
                "recommend_questions": [qa.get("question", "") for qa in low_related_qas]
            }
        result_data.data_from = "DealQueryQA"
        context.pipeline_datas.append(result_data)
        return context

    def deal_linyan_result(self, answer):
        linyan_service = LinyanService()
        fagui_regex = r'《(.*?)》'
        fagui_title = re.findall(fagui_regex, answer, re.UNICODE | re.DOTALL)
        if len(fagui_title) > 0:
            result = linyan_service.query_fagui(fagui_title[0])
            return result
        return []

    def deal_qa_dataset(self, query, data):
        query_language = determine_language(query)
        rag_references = data
        high_related_qas = []
        middle_related_qas = []
        low_related_qas = []
        for rag_reference in rag_references:        
            content = rag_reference.get('content', '')
            regex = r'question:(.*?)answer:(.*)'
            q, a = re.findall(regex, content, re.UNICODE | re.DOTALL)[0]
            rag_reference_language = determine_language(q)

            if rag_reference_language != query_language:
                continue
            
            score = rag_reference.get('metadata', {}).get('score', 0)
            if score >= 0.9:
                high_related_qas.append({
                    "question": q,
                    "answer": a,
                    "score": score
                })
            elif score >= 0.6:
                middle_related_qas.append({
                    "question": q,
                    "answer": a,
                    "score": score
                })
            else:
                low_related_qas.append({
                    "question": q,
                    "answer": a,
                    "score": score
                })

        return {
            "high_related_qas": high_related_qas,
            "middle_related_qas": middle_related_qas,
            "low_related_qas": low_related_qas
        }