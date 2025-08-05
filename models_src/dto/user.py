from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

@dataclass
class UserResponseDTO:
    id: Optional[UUID] = None
    user_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None
    membership_level: Optional[str] = None
    token_limit: Optional[int] = None
    token_used: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    encryption_salt: Optional[str] = None