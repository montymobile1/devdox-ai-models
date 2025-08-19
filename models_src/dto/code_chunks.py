import dataclasses
import datetime
import uuid
from typing import Any, Optional


@dataclasses.dataclass
class CodeChunksResponseDTO:
    """
    API Key model for storing user's API keys for external services
    """

    id: Optional[uuid.UUID] = None
    user_id: Optional[str] = None
    repo_id: Optional[str] = None
    content: Optional[str] = None
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    commit_number: Optional[str] = None
    embedding: Optional[Any] = None
    metadata: Optional[dict] = None
    created_at: Optional[datetime.datetime] = None


@dataclasses.dataclass
class CodeChunksRequestDTO:
    """
    API Key model for storing user's API keys for external services
    """

    user_id: str

    repo_id: str
    content: str

    file_name: str

    file_path: str

    file_size: int

    commit_number: str

    embedding: Optional[Any] = None
    metadata: dict = dataclasses.field(default_factory=dict)
