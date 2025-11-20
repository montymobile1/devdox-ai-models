import datetime
import uuid

from beanie import Document
from pydantic import BaseModel, Field

from models_src.models.document_extra.timestamp import TimestampAuditMixin


class ApiLog(TimestampAuditMixin, Document):
	
	id: uuid.UUID = Field(default_factory=uuid.uuid4)
	operation_id: str = Field(
		...,
		max_length=128
	)
	
	path: str = Field(
		...,
		max_length=2048
	)
	
	method: str = Field(
		...,
		max_length=8
	)
	
	user_id: str = Field(
		...,
		max_length=255
	)
	
	
	request_received_at: datetime.datetime = Field(
		..., description="a passable meta data to know when a request has been recieved by the API"
	)
	
	process_time_ms: int = Field(
		...
	)
	
	request_body: list | dict | None = Field(
		default=None, description="Encrypted request body"
	)
	
	response_body: list | dict | None = Field(
		default=None, description="Encrypted response body"
	)
	
	class Settings:
		name = "api_log"
		description = "Table for storing api logs"
	
	def __str__(self) -> str:
		return f"ApiLog(id={self.id}, user_id={self.user_id}, method={self.method}, path={self.path})"
	
	def __repr__(self):
		return self.__str__()