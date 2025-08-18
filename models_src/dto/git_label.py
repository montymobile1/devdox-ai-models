import datetime
import uuid
from dataclasses import dataclass
from typing import Optional

from models_src.dto.repo import GitHosting


@dataclass
class GitLabelResponseDTO:
    id: Optional[uuid.UUID] = None
    user_id: Optional[str] = None
    label: Optional[str] = None
    git_hosting: Optional[str] = None
    username: Optional[str] = None
    token_value: Optional[str] = None
    masked_token: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None


@dataclass
class GitLabelRequestDTO:
    user_id: str
    label: str
    git_hosting: GitHosting
    username: str
    token_value: str
    masked_token: str
