import datetime
import uuid

from tortoise import fields, Model


class ApiLog(Model):
	id: uuid.UUID = fields.UUIDField(primary_key=True, default=uuid.uuid4)
	
	operation_id: str = fields.CharField(max_length=128)
	path: str = fields.CharField(max_length=2048)
	method: str = fields.CharField(max_length=8)
	user_id: str = fields.CharField(max_length=255)
	
	request_received_at: datetime.datetime = fields.DatetimeField()
	
	process_time_ms: int = fields.IntField()
	
	request_body: list | dict | None = fields.JSONField(default=None)
	response_body: list | dict | None = fields.JSONField(default=None)

