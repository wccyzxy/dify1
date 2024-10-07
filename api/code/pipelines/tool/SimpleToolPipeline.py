from core.workflow.nodes.tool.entities import ToolNodeData
from code.models.code import BasePipeline, CodeExecutionContext, BasePipelineData
from typing import Dict, Any, cast
from core.tools.entities.tool_entities import ToolInvokeMessage
from core.tools.tool_engine import ToolEngine
from core.tools.tool_manager import ToolManager
from core.callback_handler.workflow_tool_callback_handler import DifyWorkflowCallbackHandler
from core.workflow.entities.node_entities import NodeRunMetadataKey, NodeRunResult
from models import WorkflowNodeExecutionStatus

class SimpleToolPipeline(BasePipeline):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.pipeline_name = "SimpleToolPipeline"

    def process(self, context: CodeExecutionContext) -> CodeExecutionContext:
        node_data = ToolNodeData(
            provider_id=self.config['data']['provider_id'],
            provider_type=self.config['data']['provider_type'],
            provider_name=self.config['data']['provider_name'],
            tool_name=self.config['data']['tool_name'],
            tool_label=self.config['data']['tool_label'],
            tool_configurations=self.config['data']['tool_configurations'],
            title=self.config['data'].get('title', ''),  # 如果 'title' 不存在,使用空字符串作为默认值
            tool_parameters={}
        )

        for key, value in self.config['data']['tool_parameters'].items():
            tool_input = ToolNodeData.ToolInput(
                value=value['value'],
                type=value['type']
            )
            node_data.tool_parameters[key] = tool_input

        print(node_data)
        # 获取 tool 运行时
        try:
            tool_runtime = ToolManager.get_workflow_tool_runtime(
                tenant_id=self.tenant_id,
                app_id='',
                node_id='',
                workflow_tool=node_data,
                invoke_from=None
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            error_message = f"Failed to get tool runtime: {str(e)}"
            self._handle_error(context, error_message)
            return context

        # 获取参数
        tool_parameters = {}
        for key, value in node_data.tool_parameters.items():
            tool_parameters[key] = value.value
        print(f"tool_parameters: {tool_parameters}")
        # 调用 tool
        try:
            messages = ToolEngine.workflow_invoke(
                tool=tool_runtime,
                tool_parameters=tool_parameters,
                user_id=self.config.get('user_id'),
                workflow_tool_callback=DifyWorkflowCallbackHandler(),
                workflow_call_depth=self.config.get('workflow_call_depth', 0),
                thread_pool_id=self.config.get('thread_pool_id')
            )
        except Exception as e:
            error_message = f"Failed to invoke tool: {str(e)}"
            self._handle_error(context, error_message)
            return context

        # 转换 tool 消息
        plain_text, files, json_data = self._convert_tool_messages(messages)

        # 创建 BasePipelineData 并添加到 context
        pipeline_data = BasePipelineData()
        pipeline_data.data = {
            "text": plain_text,
            "files": files,
            "json": json_data
        }
        pipeline_data.data_from = "TOOL"
        context.pipeline_datas.append(pipeline_data)

        return context

    def _handle_error(self, context: CodeExecutionContext, error_message: str):
        pipeline_data = BasePipelineData()
        pipeline_data.data = {"error": error_message}
        pipeline_data.data_from = "TOOL"
        context.pipeline_datas.append(pipeline_data)

    def _convert_tool_messages(self, messages: list[ToolInvokeMessage]) -> tuple[str, list[Dict[str, Any]], list[Dict[str, Any]]]:
        plain_text = self._extract_tool_response_text(messages)
        files = self._extract_tool_response_binary(messages)
        json_data = self._extract_tool_response_json(messages)
        return plain_text, files, json_data

    def _extract_tool_response_text(self, tool_response: list[ToolInvokeMessage]) -> str:
        return "\n".join(
            [
                f"{message.message}"
                if message.type == ToolInvokeMessage.MessageType.TEXT
                else f"Link: {message.message}"
                if message.type == ToolInvokeMessage.MessageType.LINK
                else ""
                for message in tool_response
            ]
        )

    def _extract_tool_response_binary(self, tool_response: list[ToolInvokeMessage]) -> list[Dict[str, Any]]:
        # 这里简化了文件处理,只返回文件的基本信息
        files = []
        for response in tool_response:
            if response.type in {ToolInvokeMessage.MessageType.IMAGE_LINK, ToolInvokeMessage.MessageType.IMAGE, ToolInvokeMessage.MessageType.BLOB}:
                files.append({
                    "url": response.message,
                    "filename": response.save_as,
                    "mime_type": response.meta.get("mime_type", "application/octet-stream")
                })
        return files

    def _extract_tool_response_json(self, tool_response: list[ToolInvokeMessage]) -> list[Dict[str, Any]]:
        return [message.message for message in tool_response if message.type == ToolInvokeMessage.MessageType.JSON]