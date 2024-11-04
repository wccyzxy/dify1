from core.pipeline.base_pipeline import BasePipeline
from typing import Dict, Any
from core.pipeline.entities.pipeline_entities import PipelineExecutionContext

class AfterDealPipeline(BasePipeline):
    def __init__(self, config: Dict[str, Any]):
        self.pipeline_name = 'AfterDealPipeline'
        self.config = config
        
    def process(self, context: PipelineExecutionContext) -> PipelineExecutionContext:
        # 实现后处理逻辑
        return context