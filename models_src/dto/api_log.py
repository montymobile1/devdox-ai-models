import datetime
import uuid
from dataclasses import dataclass


@dataclass
class ApiLogResponseDTO:
	id: uuid.UUID | None = None
	
	operation_id: str | None = None
	path: str | None = None
	method: str | None = None
	user_id: str | None = None
	
	request_received_at: datetime.datetime | None = None
	
	process_time_ms: int | None = None
	
	request_body: dict | None = None
	response_body: dict | None = None


@dataclass
class ApiLogRequestDTO:
	operation_id: str
	path: str
	method: str
	user_id: str
	
	request_received_at: datetime.datetime
	
	process_time_ms: int
	
	request_body: dict
	response_body: dict