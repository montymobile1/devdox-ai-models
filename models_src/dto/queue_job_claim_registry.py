import dataclasses
import datetime
import uuid
from typing import Optional

from models_src.models.common.queue_job_claim_registry_enums import QRegistryStat


@dataclasses.dataclass
class QueueProcessingRegistryResponseDTO:
    id: Optional[uuid.UUID] = None
    message_id: Optional[str] = None
    queue_name: Optional[str] = None
    step: Optional[str] = None
    status: Optional[QRegistryStat] = None
    claimed_by: Optional[str] = None
    previous_message_id: Optional[uuid.UUID] = None
    claimed_at: Optional[datetime.datetime] = None
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None


@dataclasses.dataclass
class QueueProcessingRegistryRequestDTO:
    message_id: str
    queue_name: str
    step: str
    status: QRegistryStat
    claimed_by: Optional[str] = None
    previous_message_id: Optional[uuid.UUID] = None
    claimed_at: Optional[datetime.datetime] = None