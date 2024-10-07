import datetime
import logging
from typing import Dict, Any, List
from abc import ABC, abstractmethod
import json
import uuid

class CodeQuery:
    def __init__(self, query: str, file_ids: List[str] = None, user_id: str = '', conversation_id: str = '', extensions: Dict[str, Any] = None):
        self.id: str = str(uuid.uuid4())
        self.query: str = query
        self.file_ids: List[str] = file_ids or []
        self.user_id: str = user_id
        self.conversation_id: str = conversation_id
        self.extensions: Dict[str, Any] = extensions or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'query': self.query,
            'file_ids': self.file_ids,
            'user_id': self.user_id,
            'conversation_id': self.conversation_id,
            'extensions': self.extensions
        }

class CodeQueryConfig:
    def __init__(self, configs: List[Dict[str, Any]]):
        self.configs = configs
        self.current_index = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'current_index': self.current_index,
            'configs': self.configs
        }

class CodeAnswer:
    def __init__(self, answer: str, references: List[Dict[str, any]]):
        self.id: str = str(uuid.uuid4())
        self.answer: str = answer
        self.references: List[Dict[str, any]] = references

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'answer': self.answer,
            'references': self.references
        }
    
class CodeExecutionLog:
    id: str = str(uuid.uuid4())
    code_query: CodeQuery = None
    code_answer: CodeAnswer = None
    code_query_config: CodeQueryConfig = None
    current_pipeline_name: str = ''
    current_pipeline_enter_time: str = ''
    current_pipeline_leave_time: str = ''
    current_pipeline_status: str = ''
    current_pipeline_message: str = ''

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'code_query': self.code_query.to_dict() if self.code_query else None,
            'code_answer': self.code_answer.to_dict() if self.code_answer else None,
            'code_query_config': self.code_query_config.to_dict() if self.code_query_config else None,
            'current_pipeline_name': self.current_pipeline_name,
            'current_pipeline_enter_time': self.current_pipeline_enter_time,
            'current_pipeline_leave_time': self.current_pipeline_leave_time,
            'current_pipeline_status': self.current_pipeline_status,
            'current_pipeline_message': self.current_pipeline_message
        }

class BasePipelineData(ABC):
    data: Any = None
    data_from: str = ''

    def to_dict(self) -> Dict[str, Any]:
        return {
            'data': self.data,
            'data_from': self.data_from
        }
    
    def fetch_context(self) -> str:
        if self.data_from == 'RAG':
            if isinstance(self.data, list) and len(self.data) > 0:
                contents = [item.get('content', '') for item in self.data if isinstance(item, dict)]
                return '\n\n'.join(contents)
        if self.data_from == 'LLM':
            if isinstance(self.data, dict) and self.data.get('message', None):
                return self.data['message']
        if self.data_from == 'TOOL':
            if isinstance(self.data, dict) and self.data.get('text', None):
                return self.data['text']
            if isinstance(self.data, dict) and self.data.get('json', None):
                return json.dumps(self.data['json'])
        return ''

class CodeExecutionContext:
    query: CodeQuery = None
    query_config: CodeQueryConfig = None
    pipeline_datas: List[BasePipelineData] = []
    logs: List[CodeExecutionLog] = []

class BasePipeline(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.pipeline_name = ''
        self.config = config
        self.tenant_id = '9f2194a7-2f2f-49ae-8c2d-eb7febe9555c'

    def run(self, context: CodeExecutionContext) -> CodeExecutionContext:
        code_execution_log = CodeExecutionLog()
        code_execution_log.code_query = context.query
        code_execution_log.code_query_config = context.query_config
        code_execution_log.current_pipeline_name = self.pipeline_name
        code_execution_log.current_pipeline_enter_time = datetime.datetime.now()
        try:
            context = self.process(context)
        except Exception as e:            
            code_execution_log.current_pipeline_status = 'error'
            code_execution_log.current_pipeline_message = str(e)
            import traceback
            traceback.print_exc()
        code_execution_log.current_pipeline_leave_time = datetime.datetime.now()
        context.logs.append(code_execution_log)

        if context.query_config.configs.get('run_mode', None) == 'DEBUG':
            print(f'{self.pipeline_name}: {code_execution_log.to_dict()} \n {context.pipeline_datas[-1].to_dict() if len(context.pipeline_datas) > 0 else None}')
        return context
    
    @abstractmethod
    def process(self, context: CodeExecutionContext) -> CodeExecutionContext:
        pass


