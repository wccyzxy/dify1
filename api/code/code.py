import importlib
from code.models.code import CodeQuery, CodeQueryConfig, CodeAnswer, CodeExecutionContext, BasePipeline
from typing import Dict, Any

class CodeExecutionEngine:
    def __init__(self, pipelines_dir='code.pipelines'):
        self.pre_deal_pipeline = PreDealPipeline({})
        self.after_deal_pipeline = AfterDealPipeline({})
        self.pipelines_dir = pipelines_dir

    def execute(self, query: CodeQuery, query_config: CodeQueryConfig) -> CodeAnswer:
        context = CodeExecutionContext()
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

    def _generate_answer(self, context: CodeExecutionContext) -> CodeAnswer:
        answer = context.pipeline_datas[-1].fetch_context() if len(context.pipeline_datas) > 0 else ""
        references = []
        for pipeline_data in context.pipeline_datas:
            if pipeline_data.data_from == "RAG":
                references.append({"RAG": pipeline_data.data})
        return CodeAnswer(answer=answer, references=references)

# 预处理和后处理管道
class PreDealPipeline(BasePipeline):
    def __init__(self, config: Dict[str, Any]):
        self.pipeline_name = 'PreDealPipeline'
        self.config = config

    def process(self, context: CodeExecutionContext) -> CodeExecutionContext:
        # 实现预处理逻辑
        return context

class AfterDealPipeline(BasePipeline):
    def __init__(self, config: Dict[str, Any]):
        self.pipeline_name = 'AfterDealPipeline'
        self.config = config
        
    def process(self, context: CodeExecutionContext) -> CodeExecutionContext:
        # 实现后处理逻辑
        return context