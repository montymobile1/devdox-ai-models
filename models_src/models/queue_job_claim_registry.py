import uuid
from enum import Enum

from tortoise.models import Model
from tortoise import fields


class QRegistryStat(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RETRY = "retry"
    FAILED = "failed"
    COMPLETED = "completed"

# THis is the name of the most important part of the database, basically its a partial relation that
# is responsible for preventing two workers from acquiring the same job.
queue_processing_registry_one_claim_unique = "queue_processing_registry_message_id_idx" 

class QueueProcessingRegistry(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)

    message_id = fields.TextField(null=False)
    queue_name = fields.TextField(null=False)

    claimed_by = fields.TextField(null=True)

    step = fields.TextField(null=False)

    status = fields.CharEnumField(enum_type=QRegistryStat, max_length=30, null=False)

    previous_message_id = fields.UUIDField(default=None, null=True)

    claimed_at = fields.DatetimeField(null=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "queue_processing_registry"
        indexes = [("message_id", "queue_name")]
