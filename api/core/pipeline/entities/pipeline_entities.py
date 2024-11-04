import datetime
import logging
from typing import Dict, Any, List
from abc import ABC, abstractmethod
import json
import uuid

class PipelineQuery:
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

class PipelineQueryConfig:
    def __init__(self, configs: List[Dict[str, Any]]):
        self.configs = configs
        self.current_index = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'current_index': self.current_index,
            'configs': self.configs
        }

class PipelineAnswer:
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
    
class PipelineExecutionLog:
    id: str = str(uuid.uuid4())
    pipeline_query: PipelineQuery = None
    pipeline_answer: PipelineAnswer = None
    pipeline_query_config: PipelineQueryConfig = None
    current_pipeline_name: str = ''
    current_pipeline_enter_time: str = ''
    current_pipeline_leave_time: str = ''
    current_pipeline_status: str = ''
    current_pipeline_message: str = ''

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'pipeline_query': self.pipeline_query.to_dict() if self.pipeline_query else None,
            'pipeline_answer': self.pipeline_answer.to_dict() if self.pipeline_answer else None,
            'pipeline_query_config': self.pipeline_query_config.to_dict() if self.pipeline_query_config else None,
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

class PipelineExecutionContext:
    query: PipelineQuery = None
    query_config: PipelineQueryConfig = None
    pipeline_datas: List[BasePipelineData] = []
    logs: List[PipelineExecutionLog] = []

