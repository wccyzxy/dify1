from core.pipeline.base_pipeline import BasePipeline
from core.pipeline.entities.pipeline_entities import PipelineExecutionContext, BasePipelineData
from typing import List, Dict, Any
from extensions.ext_database import db
from models.dataset import Dataset, Document, DocumentSegment
from sqlalchemy import func
from core.rag.retrieval.dataset_retrieval import DatasetRetrieval
from core.rag.retrieval.retrieval_methods import RetrievalMethod
from core.app.app_config.entities import DatasetRetrieveConfigEntity


class DealLeadingQuestionPipeline(BasePipeline):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.pipeline_name = "DealLeadingQuestionPipeline"

    def process(self, context: PipelineExecutionContext) -> PipelineExecutionContext:
        leading_question_data = context.pipeline_datas[-1].data.get("message", "")
        print(f"leading_question_data: {leading_question_data}")
        leading_question_json_data = self.get_json_data(leading_question_data)
        print(f"leading_question_json_data: {leading_question_json_data}")
        relevant_data = BasePipelineData()        
        context.pipeline_datas.append(relevant_data)
        if not leading_question_json_data:
            relevant_data.data = {
                "code": 500,
                "message": "获取问题引导数据错误"
            }
            context.is_exit = True
        else:
            deal_type = leading_question_json_data.get("type", "")
            deal_data = leading_question_json_data.get("data", "")
            if deal_type == "":
                relevant_data.data = {
                    "code": 500,
                    "message": "获取问题引导数据错误"
                }
                context.is_exit = True
            elif deal_type == "answer":
                data = deal_data
                if isinstance(deal_data, list):
                    data = "请问您要问的是：\n\n"
                    for index, item in enumerate(deal_data, start=1):
                        data += f"    {index}. {item}\n"
                    data += "\n请输入上面的问题或者提供更多的信息。"
                relevant_data.data = {
                    "code": 200,
                    "message": "success",
                    "data": data
                }
                context.is_exit = True
            elif deal_type == "query":
                relevant_data.data = {
                    "code": 300,
                    "message": "success",
                    "data": deal_data,
                    "key": "query"
                }
            elif deal_type == "query_fagui":
                relevant_data.data = {
                    "code": 300,
                    "message": "success",
                    "data": deal_data,
                    "key": "query_fagui"
                }


        relevant_data.data_from = "DealLeadingQuestion"
        return context

    def get_json_data(self, message):
        try:
            import re
            import json

            # 查找字符串中的 JSON 格式内容（在花括号之间的内容）
            json_pattern = r'\{[^{}]*\}'
            json_matchs = re.findall(json_pattern, message)
            for json_match in json_matchs:
                try:
                    json_str = json_match.replace("\n", "")
                    json_data = json.loads(json_str)

                    # 验证是否包含必需的键
                    if all(key in json_data for key in ['type', 'data']):
                        return json_data
                except Exception as e:
                    continue
            return None
        except Exception as e:
            # JSON 解析失败时返回默认结构
            return None