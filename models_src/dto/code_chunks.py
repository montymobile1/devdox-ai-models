import dataclasses
import datetime
import uuid
from typing import Any, Optional

@dataclasses.dataclass
class CodeChunksResponseDTO:
    """
    API Key model for storing user's API keys for external services
    """

    id: Optional[uuid.UUID]
    user_id: Optional[str]
    repo_id: Optional[str]
    content: Optional[str]
    file_name: Optional[str]
    file_path: Optional[str]
    file_size: Optional[int]
    commit_number: Optional[str]
    embedding: Optional[Any]
    metadata: Optional[dict]
    created_at: Optional[datetime.datetime]



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