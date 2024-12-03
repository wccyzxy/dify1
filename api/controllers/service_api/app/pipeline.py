import logging
from flask_restful import Resource, fields, marshal_with, reqparse

from controllers.service_api.wraps import validate_app_token
from core.pipeline.entities.pipeline_entities import PipelineQuery, PipelineQueryConfig
from core.pipeline.pipeline_entry import PipelineExecutionEntry
from libs import helper
from controllers.service_api import api
from controllers.service_api.app.error import (
    CompletionRequestError,
    ProviderModelCurrentlyNotSupportError,
    ProviderNotInitializeError,
    ProviderQuotaExceededError,
)
from core.errors.error import ModelCurrentlyNotSupportError, ProviderTokenNotInitError, QuotaExceededError
from core.model_runtime.errors.invoke import InvokeError
from werkzeug.exceptions import InternalServerError

from models import App

logger = logging.getLogger(__name__)


class PipelineQueryApi(Resource):
    @validate_app_token
    def post(self, app_model: App):
        """
        Run CodeQuery
        """
        parser = reqparse.RequestParser()
        parser.add_argument("query", type=dict, location="json")
        parser.add_argument("config", type=dict, location="json")
        args = parser.parse_args()
        try:
            pipeline_entry = PipelineExecutionEntry()
            query = PipelineQuery(**args["query"])
            config = PipelineQueryConfig(args["config"], app_model.tenant_id)
            response = pipeline_entry.execute(query=query, query_config=config)
            return response, 200
        except ProviderTokenNotInitError as ex:
            raise ProviderNotInitializeError(ex.description)
        except QuotaExceededError:
            raise ProviderQuotaExceededError()
        except ModelCurrentlyNotSupportError:
            raise ProviderModelCurrentlyNotSupportError()
        except InvokeError as e:
            raise CompletionRequestError(e.description)
        except ValueError as e:
            raise e
        except Exception as e:
            logging.exception("internal server error.")
            raise InternalServerError()


api.add_resource(PipelineQueryApi, "/pipeline/query")
