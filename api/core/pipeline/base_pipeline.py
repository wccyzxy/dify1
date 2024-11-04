

from abc import ABC, abstractmethod
from typing import Dict, Any
import datetime
from core.pipeline.entities.pipeline_entities import PipelineExecutionContext, PipelineExecutionLog

class BasePipeline(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.pipeline_name = ''
        self.config = config
        self.tenant_id = '9f2194a7-2f2f-49ae-8c2d-eb7febe9555c'

    def run(self, context: PipelineExecutionContext) -> PipelineExecutionContext:
        pipeline_execution_log = PipelineExecutionLog()
        pipeline_execution_log.pipeline_query = context.query
        pipeline_execution_log.pipeline_query_config = context.query_config
        pipeline_execution_log.current_pipeline_name = self.pipeline_name
        pipeline_execution_log.current_pipeline_enter_time = datetime.datetime.now()
        try:
            context = self.process(context)
        except Exception as e:            
            pipeline_execution_log.current_pipeline_status = 'error'
            pipeline_execution_log.current_pipeline_message = str(e)
            import traceback
            traceback.print_exc()
        pipeline_execution_log.current_pipeline_leave_time = datetime.datetime.now()
        context.logs.append(pipeline_execution_log)

        if context.query_config.configs.get('run_mode', None) == 'DEBUG':
            print(f'{self.pipeline_name}: {pipeline_execution_log.to_dict()} \n {context.pipeline_datas[-1].to_dict() if len(context.pipeline_datas) > 0 else None}')
        return context
    
    @abstractmethod
    def process(self, context: PipelineExecutionContext) -> PipelineExecutionContext:
        pass