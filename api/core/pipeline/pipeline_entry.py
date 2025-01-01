import importlib
from core.pipeline.pipelines.pre_deal_pipeline import PreDealPipeline
from core.pipeline.pipelines.after_deal_pipeline import AfterDealPipeline
from core.pipeline.entities.pipeline_entities import PipelineExecutionContext, PipelineQuery, PipelineQueryConfig, PipelineAnswer
from typing import Dict, Any

class PipelineExecutionEntry:
    def __init__(self, pipelines_dir='core.pipeline.pipelines'):
        self.pre_deal_pipeline = PreDealPipeline({})
        self.after_deal_pipeline = AfterDealPipeline({})
        self.pipelines_dir = pipelines_dir

    def execute(self, query: PipelineQuery, query_config: PipelineQueryConfig) -> PipelineAnswer:
        context = PipelineExecutionContext()
        context.query = query
        context.query_config = query_config
        context.pipeline_datas = []
        context.logs = []
        
        # 执行 PreDealPipeline
        context = self.pre_deal_pipeline.run(context)
        
        # 根据 CodeQueryConfig 执行中间流程
        print(f'query_config: {query_config.configs}')
        for pipeline_config in query_config.configs.get('pipelines', []):
            context = self.excute_pipeline(query_config, pipeline_config, context)
            if context.is_exit:
                break
        
        # 执行 AfterDealPipeline
        context = self.after_deal_pipeline.run(context)
        
        # 生成 CodeAnswer
        code_answer = self._generate_answer(context)
        return code_answer.to_dict()

    def excute_pipeline(self, query_config, pipeline_config, context: PipelineExecutionContext):
        pipeline_class = self._import_pipeline(pipeline_config)
        pipeline_config['tenant_id'] = query_config.tenant_id
        pipeline_instance = pipeline_class(pipeline_config)
        context = pipeline_instance.run(context)
        last_pipeline_data = context.pipeline_datas[-1].data
        if "code" in last_pipeline_data and last_pipeline_data["code"] == 300:
            key = last_pipeline_data.get("key", "")
            sub_pipeline_configs = pipeline_config.get("sub_pipeline_configs", {})
            if key != "" and key in sub_pipeline_configs:
                for config in sub_pipeline_configs.get(key, []):
                    context = self.excute_pipeline(query_config, config, context)
                    if context.is_exit:
                        break
        return context

    def _import_pipeline(self, pipeline_config: Dict[str, Any]):
        pipeline_name = pipeline_config['name']
        pipeline_path = pipeline_config['path']
        module_name = f"{self.pipelines_dir}.{pipeline_path}"
        try:
            module = importlib.import_module(module_name)
            return getattr(module, pipeline_name)
        except (ImportError, AttributeError) as e:
            raise ValueError(f"无法导入pipeline: {pipeline_name}. 错误: {str(e)}")

    def _generate_answer(self, context: PipelineExecutionContext) -> PipelineAnswer:
        answer = context.pipeline_datas[-1].fetch_context() if len(context.pipeline_datas) > 0 else ""
        references = []
        recommend_questions = []
        updated_references = []

        for pipeline_data in context.pipeline_datas:
            if pipeline_data.data_from == "RAG":
                references = pipeline_data.data
            elif pipeline_data.data_from == "DealQueryQA":
                references = pipeline_data.data.get("references", [])
                recommend_questions = pipeline_data.data.get("recommend_questions", [])
            elif pipeline_data.data_from == "QueryLawAndGuidance":
                references = pipeline_data.data.get("references", [])
        for reference in references:
            updated_references.append(
                {
                    "segment_id": reference.get("metadata", {}).get("segment_id", ""),
                    "position": reference.get("metadata", {}).get("position", ""),
                    "document_name": reference.get("metadata", {}).get("document_name", ""),
                    "score": reference.get("metadata", {}).get("score", ""),
                    "content": reference.get("content", ""),
                    "metadata": reference.get("metadata", {}),
                }
            )
        return PipelineAnswer(answer=answer, references=updated_references, recommend_questions=recommend_questions)
