import datetime
import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class GitLabelResponseDTO:
    id: Optional[uuid.UUID] = None
    user_id: Optional[str] = None
    label: Optional[str] = None
    git_hosting: Optional[str] = None
    username: Optional[str] = None
    token_value: Optional[str] = None
    masked_token: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None