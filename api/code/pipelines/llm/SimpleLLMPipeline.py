from code.models.code import BasePipeline, CodeExecutionContext, BasePipelineData
from typing import List, Dict, Any
from typing import TYPE_CHECKING, Any, Optional, cast
from pydantic import BaseModel, ConfigDict
from core.model_runtime.entities.llm_entities import LLMResult, LLMUsage
from core.model_manager import ModelInstance, ModelManager
from core.entities.provider_configuration import ProviderModelBundle
from core.model_runtime.entities.model_entities import AIModelEntity, ModelType
from core.model_runtime.model_providers.__base.large_language_model import LargeLanguageModel
from core.entities.model_entities import ModelStatus
from core.errors.error import ModelCurrentlyNotSupportError, ProviderTokenNotInitError, QuotaExceededError
from core.model_runtime.entities.message_entities import (
    AssistantPromptMessage,
    ImagePromptMessageContent,
    PromptMessage,
    PromptMessageContentType,
    PromptMessageRole,
    SystemPromptMessage,
    UserPromptMessage,
)
from collections.abc import Generator

class ModelConfigWithCredentialsEntity(BaseModel):
    """
    Model Config With Credentials Entity.
    """

    provider: str
    model: str
    model_schema: AIModelEntity
    mode: str
    provider_model_bundle: ProviderModelBundle
    credentials: dict[str, Any] = {}
    parameters: dict[str, Any] = {}
    stop: list[str] = []

    # pydantic configs
    model_config = ConfigDict(protected_namespaces=())

class ModelInvokeCompleted(BaseModel):
    """
    Model invoke completed
    """

    text: str
    usage: LLMUsage
    finish_reason: Optional[str] = None

class ModelConfig(BaseModel):
    """
    Model Config.
    """

    provider: str
    name: str
    mode: str
    completion_params: dict[str, Any] = {}

class SimpleLLMPipeline(BasePipeline):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.pipeline_name = "SimpleLLMPipeline"

    def process(self, context: CodeExecutionContext) -> CodeExecutionContext:
        query = context.query.query
        # 获取上下文（如果存在）
        context_content = context.pipeline_datas[-1].fetch_context() if len(context.pipeline_datas) > 0 else ""
        
        # fetch model config
        model_instance, model_config = self._fetch_model_config(self.config['model'])

        # 处理prompt模板
        prompt_messages = self._process_prompt_template(self.config['prompt_template'], query, context_content)
        print(f"prompt_messages: {prompt_messages}")
        llm_result = self._invoke_llm(model_instance, model_config, prompt_messages)

        print(llm_result)

        pipeline_data = BasePipelineData()
        pipeline_data.data = {
            'model': llm_result.model,
            'prompt_messages': [{'role': message.role, 'content': message.content, 'name': message.name} for message in llm_result.prompt_messages],
            'message': llm_result.message.content,
            'usage': '',
            'system_fingerprint': llm_result.system_fingerprint
        }
        pipeline_data.data_from = "LLM"
        context.pipeline_datas.append(pipeline_data)
        return context

    def _fetch_model_config(
        self, node_data_model: ModelConfig
    ) -> tuple[ModelInstance, ModelConfigWithCredentialsEntity]:
        """
        Fetch model config
        :param node_data_model: node data model
        :return:
        """
        model_name = node_data_model['name']
        provider_name = node_data_model['provider']

        model_manager = ModelManager()
        model_instance = model_manager.get_model_instance(
            tenant_id=self.tenant_id, model_type=ModelType.LLM, provider=provider_name, model=model_name
        )

        provider_model_bundle = model_instance.provider_model_bundle
        model_type_instance = model_instance.model_type_instance
        model_type_instance = cast(LargeLanguageModel, model_type_instance)

        model_credentials = model_instance.credentials

        # check model
        provider_model = provider_model_bundle.configuration.get_provider_model(
            model=model_name, model_type=ModelType.LLM
        )

        if provider_model is None:
            raise ValueError(f"Model {model_name} not exist.")

        if provider_model.status == ModelStatus.NO_CONFIGURE:
            raise ProviderTokenNotInitError(f"Model {model_name} credentials is not initialized.")
        elif provider_model.status == ModelStatus.NO_PERMISSION:
            raise ModelCurrentlyNotSupportError(f"Dify Hosted OpenAI {model_name} currently not support.")
        elif provider_model.status == ModelStatus.QUOTA_EXCEEDED:
            raise QuotaExceededError(f"Model provider {provider_name} quota exceeded.")

        # model config
        completion_params = node_data_model['completion_params']
        stop = []
        if "stop" in completion_params:
            stop = completion_params["stop"]
            del completion_params["stop"]

        # get model mode
        model_mode = node_data_model['mode']
        if not model_mode:
            raise ValueError("LLM mode is required.")

        model_schema = model_type_instance.get_model_schema(model_name, model_credentials)

        if not model_schema:
            raise ValueError(f"Model {model_name} not exist.")

        return model_instance, ModelConfigWithCredentialsEntity(
            provider=provider_name,
            model=model_name,
            model_schema=model_schema,
            mode=model_mode,
            provider_model_bundle=provider_model_bundle,
            credentials=model_credentials,
            parameters=completion_params,
            stop=stop,
        )

    def _invoke_llm(
        self,
        model_instance: ModelInstance,
        model_config: ModelConfigWithCredentialsEntity,
        prompt_messages: list[PromptMessage],
    ) -> LLMResult:
        invoke_result = model_instance.invoke_llm(
            prompt_messages=prompt_messages,
            model_parameters=model_config.parameters,
            stop=model_config.stop,
            stream=False,
            user=self.tenant_id,
        )

        if isinstance(invoke_result, Generator):
            # 如果结果是生成器，我们需要消耗它以获得最终结果
            final_result = None
            for chunk in invoke_result:
                final_result = chunk
            return final_result
        else:
            return invoke_result
        
    def _process_prompt_template(self, prompt_template, query, context_content) -> list[PromptMessage]:
        processed_messages = []
        for message in prompt_template:
            role = message.get('role', 'user')
            text = message['text']
            
            # 替换特殊变量
            text = text.replace("{{#query#}}", query)
            text = text.replace("{{#context#}}", context_content)
            
            # 处理其他变量
            # for variable in re.findall(r'{{#(.*?)#}}', text):
            #     parts = variable.split('.')
            #     if len(parts) == 2:
            #         pipeline_data = next((data for data in execution_context.pipeline_datas if data.__class__.__name__.lower() == parts[0]), None)
            #         if pipeline_data:
            #             value = getattr(pipeline_data, parts[1], '')
            #             text = text.replace(f"{{#{variable}#}}", str(value))
            print(f"role: {role}")
            if role == PromptMessageRole.USER.value:
                processed_messages.append(UserPromptMessage(content=text))
            elif role == PromptMessageRole.ASSISTANT.value:
                processed_messages.append(AssistantPromptMessage(content=text))
            elif role == PromptMessageRole.SYSTEM.value:
                processed_messages.append(SystemPromptMessage(content=text))
        
        return processed_messages