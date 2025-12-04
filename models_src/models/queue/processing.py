from enum import IntEnum, StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

processing_queue_name: str = "processing"

class ProcessingJobType(StrEnum):
    ANALYZE = "analyze"
    REANALYZE = "reanalyze"
    PROCESSING = "processing"

class ProcessingPriority(IntEnum):
    LEVEL_1 = 1

class ProcessingQPayloadMeta(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    
    branch: str = Field(..., description="The repository branch name on the hosting platform")
    repo_id: str = Field(..., description="The repository id on the hosting platform")
    token_id: str = Field(..., description="The `id` of the git_label")
    config: dict | None = Field(default_factory=dict, description="If you want to pass any extra configurations to the queue engine")
    user_id: str = Field(..., description="the id of the user on the authentication platform")
    priority: ProcessingPriority = Field(..., description="The priority of the job on the queue")
    git_token: str = Field(..., description="The `id` of the git_label")
    token_value: str = Field(..., description="The `token_value` of the git_label")
    git_provider: str = Field(..., description="The `git_provider` of the git_label")
    context_id: str = Field(default_factory=lambda: uuid4().hex, description="A randomly generated code to be able to identify the job")

class ProcessingQPayload(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    
    job_type: ProcessingJobType = Field(..., description="The type of the job")
    payload: ProcessingQPayloadMeta = Field(..., description="The payload of the job")