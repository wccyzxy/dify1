import os
from typing import Generator

import pytest
from core.model_runtime.entities.llm_entities import LLMResult, LLMResultChunk, LLMResultChunkDelta
from core.model_runtime.entities.message_entities import (AssistantPromptMessage, ImagePromptMessageContent,
                                                          PromptMessageTool, SystemPromptMessage,
                                                          TextPromptMessageContent, UserPromptMessage)
from core.model_runtime.entities.model_entities import AIModelEntity, ModelType
from core.model_runtime.errors.validate import CredentialsValidateFailedError
from core.model_runtime.model_providers.__base.large_language_model import LargeLanguageModel
from core.model_runtime.model_providers.kimi.llm.llm import KimiLargeLanguageModel

"""FOR MOCK FIXTURES, DO NOT REMOVE"""
from tests.integration_tests.model_runtime.__mock.openai import setup_openai_mock


def test_predefined_models():
    model = KimiLargeLanguageModel()
    model_schemas = model.predefined_models()

    assert len(model_schemas) >= 1
    assert isinstance(model_schemas[0], AIModelEntity)

@pytest.mark.parametrize('setup_openai_mock', [['chat']], indirect=True)
def test_validate_credentials_for_chat_model(setup_openai_mock):
    model = KimiLargeLanguageModel()

    with pytest.raises(CredentialsValidateFailedError):
        model.validate_credentials(
            model='moonshot-v1-8k',
            credentials={
                'moonshot_api_key': 'invalid_key'
            }
        )

    model.validate_credentials(
        model='moonshot-v1-8k',
        credentials={
            'moonshot_api_key': os.environ.get('MOONSHOT_API_KEY')
        }
    )

@pytest.mark.parametrize('setup_openai_mock', [['completion']], indirect=True)
def test_validate_credentials_for_completion_model(setup_openai_mock):
    model = KimiLargeLanguageModel()

    with pytest.raises(CredentialsValidateFailedError):
        model.validate_credentials(
            model='moonshot-v1-32k',
            credentials={
                'moonshot_api_key': 'invalid_key'
            }
        )

    model.validate_credentials(
        model='moonshot-v1-32k',
        credentials={
            'moonshot_api_key': os.environ.get('MOONSHOT_API_KEY')
        }
    )

@pytest.mark.parametrize('setup_openai_mock', [['completion']], indirect=True)
def test_invoke_completion_model(setup_openai_mock):
    model = KimiLargeLanguageModel()

    result = model.invoke(
        model='moonshot-v1-128k',
        credentials={
            'moonshot_api_key': os.environ.get('MOONSHOT_API_KEY'),
            'openai_api_base': 'https://api.moonshot.cn/v1'
        },
        prompt_messages=[
            UserPromptMessage(
                content='Hello World!'
            )
        ],
        model_parameters={
            'temperature': 0.0,
            'max_tokens': 1
        },
        stream=False,
        user="abc-123"
    )

    assert isinstance(result, LLMResult)
    assert len(result.message.content) > 0
    assert model._num_tokens_from_string('moonshot-v1-128k', result.message.content) == 1


def test__get_num_tokens_by_gpt2():
    model = KimiLargeLanguageModel()
    num_tokens = model._get_num_tokens_by_gpt2('Hello World!')

    assert num_tokens == 3
