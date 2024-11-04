from typing import Any, Optional
from pydantic import BaseModel, Field

class PipelineEngineEvent(BaseModel):
    pass

###########################################
# Pipeline Events
###########################################

class BasePipelineEvent(PipelineEngineEvent):
    pass

class PipelineRunSucceededEvent(BasePipelineEvent):
    outputs: Optional[dict[str, Any]] = None
    """outputs"""

class PipelineRunFailedEvent(BasePipelineEvent):
    error: str = Field(..., description="failed reason")