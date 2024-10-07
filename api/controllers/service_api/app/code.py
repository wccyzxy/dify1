import logging
from flask_restful import Resource, fields, marshal_with, reqparse
from code.models.code import CodeQuery, CodeQueryConfig
from code.code import CodeExecutionEngine
from libs import helper
from controllers.service_api import api
from controllers.service_api.app.error import (
    CompletionRequestError,
    NotWorkflowAppError,
    ProviderModelCurrentlyNotSupportError,
    ProviderNotInitializeError,
    ProviderQuotaExceededError,
)
from core.errors.error import ModelCurrentlyNotSupportError, ProviderTokenNotInitError, QuotaExceededError
from core.model_runtime.errors.invoke import InvokeError
from werkzeug.exceptions import InternalServerError
from controllers.service_api.wraps import FetchUserArg, WhereisUserArg, validate_app_token

logger = logging.getLogger(__name__)

class CodeRunApi(Resource):
    def post(self):
        """
        Run CodeQuery
        """
        parser = reqparse.RequestParser()
        parser.add_argument("query", type=dict, location="json")
        parser.add_argument("config", type=dict, location="json")
        args = parser.parse_args()
        try:
            engine = CodeExecutionEngine()
            query = CodeQuery(**args["query"])
            config = CodeQueryConfig(args["config"])
            response = engine.execute(query=query, query_config=config)
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


api.add_resource(CodeRunApi, "/codequery/run")