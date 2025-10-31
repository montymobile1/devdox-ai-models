import uuid

from tortoise import fields, Model


class ApiLog(Model):
	id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
	
	operation_id = fields.CharField(max_length=128)
	path = fields.CharField(max_length=2048)
	method = fields.CharField(max_length=8)
	user_id = fields.CharField(max_length=255)
	
	request_received_at = fields.DatetimeField()
	
	process_time_ms = fields.IntField()
	
	request = fields.JSONField()
	response = fields.JSONField()

