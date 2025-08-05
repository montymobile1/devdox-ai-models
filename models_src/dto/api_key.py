import datetime
import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class APIKeyResponseDTO:
    id: Optional[uuid.UUID] = None
    user_id: Optional[str] = None
    api_key: Optional[str] = None
    masked_api_key: Optional[str] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None
    last_used_at: Optional[datetime.datetime] = None


@dataclass
class APIKeyRequestDTO:
    user_id: str
    api_key: str
    masked_api_key: str
    is_active: Optional[str] = None
