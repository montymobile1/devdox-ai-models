import uuid
from datetime import datetime
from typing import Optional

import pymongo
from beanie import Document
from models_src.models import QRegistryStat
from pydantic import Field

from models_src.models.document_extra.timestamp import TimestampAuditMixin

queue_processing_registry_one_claim_unique = "queue_processing_registry_message_id_idx"

class QueueProcessingRegistry(TimestampAuditMixin, Document):
    """
    Prevents double-claiming the same queue job. At most one doc per message_id is allowed
    while status any of {pending, in_progress} via a partial unique index.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)

    message_id: str = Field(..., description="Message id from the queue system")
    queue_name: str = Field(..., description="Queue name / topic")

    claimed_by: Optional[str] = Field(None, description="Worker id that claimed this item")
    step: str = Field(..., description="Pipeline step / phase label")

    status: QRegistryStat = Field(..., description="Processing state")

    previous_message_id: Optional[uuid.UUID] = Field(
        default=None, description="Previous message id in a linked chain (if any)"
    )

    claimed_at: Optional[datetime] = Field(default=None)

    class Settings:
        name = "queue_processing_registry"
        indexes = [
            
            pymongo.IndexModel([("message_id", pymongo.ASCENDING),
                                ("queue_name", pymongo.ASCENDING)]),

            # Partial UNIQUE index that enforces: at most one doc per message_id
            # while status is any of {pending, in_progress}
            pymongo.IndexModel(
                [("message_id", pymongo.ASCENDING)],
                name=queue_processing_registry_one_claim_unique,
                unique=True,
                partialFilterExpression={
                    "status": {"$in": [QRegistryStat.PENDING, QRegistryStat.IN_PROGRESS]}
                },
            ),
        ]

    def __str__(self) -> str:
        return f"QueueProcessingRegistry(message_id={self.message_id}, status={self.status}, queue={self.queue_name})"