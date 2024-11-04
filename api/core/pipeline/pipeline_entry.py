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
        for pipeline_config in query_config.configs.get('pipelines', []):
            pipeline_class = self._import_pipeline(pipeline_config)
            pipeline_instance = pipeline_class(pipeline_config)
            context = pipeline_instance.run(context)
        
        # 执行 AfterDealPipeline
        context = self.after_deal_pipeline.run(context)
        
        # 生成 CodeAnswer
        code_answer = self._generate_answer(context)
        return code_answer.to_dict()

    def _import_pipeline(self, pipeline_config: Dict[str, Any]):
        pipeline_name = pipeline_config['name']
        pipeline_category = pipeline_config['category']
        module_name = f"{self.pipelines_dir}.{pipeline_category}.{pipeline_name}" if pipeline_category else f"{self.pipelines_dir}.{pipeline_name}"
        try:
            module = importlib.import_module(module_name)
            return getattr(module, pipeline_name)
        except (ImportError, AttributeError) as e:
            raise ValueError(f"无法导入pipeline: {pipeline_name}. 错误: {str(e)}")

    def _generate_answer(self, context: PipelineExecutionContext) -> PipelineAnswer:
        answer = context.pipeline_datas[-1].fetch_context() if len(context.pipeline_datas) > 0 else ""
        references = []
        for pipeline_data in context.pipeline_datas:
            if pipeline_data.data_from == "RAG":
                references.append({"RAG": pipeline_data.data})
        return PipelineAnswer(answer=answer, references=references)
