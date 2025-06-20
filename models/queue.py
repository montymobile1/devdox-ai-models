import uuid
from enum import Enum
from tortoise import fields, Model


# Enums
class MessageStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Tortoise ORM Models
class MessageQueue(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    message_id = fields.CharField(max_length=255, unique=True)
    message_type = fields.CharField(max_length=100)
    payload = fields.JSONField()
    priority = fields.IntField(default=1)
    status = fields.CharEnumField(MessageStatus, default=MessageStatus.PENDING)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    processed_at = fields.DatetimeField(null=True)
    scheduled_for = fields.DatetimeField(default=datetime.utcnow)
    retry_count = fields.IntField(default=0)
    max_retries = fields.IntField(default=3)
    error_message = fields.TextField(null=True)

    class Meta:
        table = "message_queue"
        indexes = [
            ("status",),
            ("scheduled_for",),
            ("priority",),
            ("message_type",),
            ("created_at",),
        ]

    def __str__(self):
        return f"MessageQueue({self.message_id}: {self.message_type})"
