import logging
import os
from collections.abc import Mapping
from typing import Any, cast

from api.core.app.apps.base_app_runner import AppRunner
from api.core.pipeline.entities.event import PipelineEngineEvent, PipelineRunFailedEvent, PipelineRunSucceededEvent
from api.core.pipeline.entities.pipeline_entities import PipelineQuery, PipelineQueryConfig

from core.app.apps.pipeline_chat.app_config_manager import PipelineChatAppConfig
from core.app.apps.base_app_queue_manager import AppQueueManager, PublishFrom
from core.app.entities.app_invoke_entities import (
    PipelineChatAppGenerateEntity,
    InvokeFrom,
)
from core.app.entities.queue_entities import (
    AppQueueEvent,
    QueueAnnotationReplyEvent,
    QueuePipelineFailedEvent,
    QueuePipelineSucceededEvent,
    QueueStopEvent,
    QueueTextChunkEvent,
)
from core.moderation.base import ModerationError
from core.pipeline.pipeline_entry import PipelineExecutionEntry
from extensions.ext_database import db
from models.model import App, Conversation, EndUser, Message
from models.workflow import ConversationVariable, WorkflowType

logger = logging.getLogger(__name__)


class PipelineChatAppRunner(AppRunner):
    """
    PipelineChat Application Runner
    """

    def __init__(
        self,
        application_generate_entity: PipelineChatAppGenerateEntity,
        queue_manager: AppQueueManager,
        conversation: Conversation,
        message: Message,
    ) -> None:
        """
        :param application_generate_entity: application generate entity
        :param queue_manager: application queue manager
        :param conversation: conversation
        :param message: message
        """
        self.queue_manager = queue_manager
        self.application_generate_entity = application_generate_entity
        self.conversation = conversation
        self.message = message

    def run(self) -> None:
        """
        Run application
        :return:
        """
        app_config = self.application_generate_entity.app_config
        app_config = cast(PipelineChatAppConfig, app_config)

        app_record = db.session.query(App).filter(App.id == app_config.app_id).first()
        if not app_record:
            raise ValueError("App not found")

        user_id = None
        if self.application_generate_entity.invoke_from in {InvokeFrom.WEB_APP, InvokeFrom.SERVICE_API}:
            end_user = db.session.query(EndUser).filter(EndUser.id == self.application_generate_entity.user_id).first()
            if end_user:
                user_id = end_user.session_id
        else:
            user_id = self.application_generate_entity.user_id

        inputs = self.application_generate_entity.inputs
        query = self.application_generate_entity.query
        files = self.application_generate_entity.files

        # moderation
        if self.handle_input_moderation(
            app_record=app_record,
            app_generate_entity=self.application_generate_entity,
            inputs=inputs,
            query=query,
            message_id=self.message.id,
        ):
            return

        # annotation reply
        if self.handle_annotation_reply(
            app_record=app_record,
            message=self.message,
            query=query,
            app_generate_entity=self.application_generate_entity,
        ):
            return

        db.session.commit()

        db.session.close()

        pipeline_query = PipelineQuery(
            query=query,
            user_id=user_id,
            conversation_id=self.conversation.id,
            parent_message_id=self.message.id,
        )
        pipeline_query_config = PipelineQueryConfig(
            configs=self.application_generate_entity.extras['pipeline_query_config'],
        )
        # RUN PIPELINE
        pipeline_entry = PipelineExecutionEntry()

        generator = pipeline_entry.execute(
            pipeline_query=pipeline_query,
            pipeline_query_config=pipeline_query_config,
        )
        for event in generator:
            self._handle_event(pipeline_entry, event)

    def handle_input_moderation(
        self,
        app_record: App,
        app_generate_entity: PipelineChatAppGenerateEntity,
        inputs: Mapping[str, Any],
        query: str,
        message_id: str,
    ) -> bool:
        """
        Handle input moderation
        :param app_record: app record
        :param app_generate_entity: application generate entity
        :param inputs: inputs
        :param query: query
        :param message_id: message id
        :return:
        """
        try:
            # process sensitive_word_avoidance
            _, inputs, query = self.moderation_for_inputs(
                app_id=app_record.id,
                tenant_id=app_generate_entity.app_config.tenant_id,
                app_generate_entity=app_generate_entity,
                inputs=inputs,
                query=query,
                message_id=message_id,
            )
        except ModerationError as e:
            self._complete_with_stream_output(text=str(e), stopped_by=QueueStopEvent.StopBy.INPUT_MODERATION)
            return True

        return False

    def handle_annotation_reply(
        self, app_record: App, message: Message, query: str, app_generate_entity: PipelineChatAppGenerateEntity
    ) -> bool:
        """
        Handle annotation reply
        :param app_record: app record
        :param message: message
        :param query: query
        :param app_generate_entity: application generate entity
        """
        # annotation reply
        annotation_reply = self.query_app_annotations_to_reply(
            app_record=app_record,
            message=message,
            query=query,
            user_id=app_generate_entity.user_id,
            invoke_from=app_generate_entity.invoke_from,
        )

        if annotation_reply:
            self._publish_event(QueueAnnotationReplyEvent(message_annotation_id=annotation_reply.id))

            self._complete_with_stream_output(
                text=annotation_reply.content, stopped_by=QueueStopEvent.StopBy.ANNOTATION_REPLY
            )
            return True

        return False

    def _complete_with_stream_output(self, text: str, stopped_by: QueueStopEvent.StopBy) -> None:
        """
        Direct output
        :param text: text
        :return:
        """
        self._publish_event(QueueTextChunkEvent(text=text))

        self._publish_event(QueueStopEvent(stopped_by=stopped_by))

    def _handle_event(self, pipeline_entry: PipelineExecutionEntry, event: PipelineEngineEvent) -> None:
        """
        Handle event
        :param pipeline_entry: pipeline entry
        :param event: event
        """
        if isinstance(event, PipelineRunSucceededEvent):
            self._publish_event(QueuePipelineSucceededEvent(outputs=event.outputs))
        elif isinstance(event, PipelineRunFailedEvent):
            self._publish_event(QueuePipelineFailedEvent(error=event.error))

    def _publish_event(self, event: AppQueueEvent) -> None:
        self.queue_manager.publish(event, PublishFrom.APPLICATION_MANAGER)