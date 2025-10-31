import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from beanie import PydanticObjectId
from beanie import Document, before_event, Insert, Replace
from pydantic import Field


class CodeChunks(Document):
    """
    Model for storing code chunks per repo of user
    """

    id: uuid.UUID| PydanticObjectId = Field(default_factory=uuid.uuid4)
    user_id: str = Field(..., max_length=255, description="User identifier")
    repo_id: str = Field(..., max_length=255, description="Repo identifier")
    content: str = Field(..., description="Code content")

    # Store embeddings as a list of floats
    embedding: Optional[List] = Field(
        default=None, description="Vector embedding for semantic search"
    )

    metadata: Dict[str, Any] = Field(default_factory=dict)
    file_name: str = Field(..., max_length=255, description="File name")
    file_path: str = Field(..., max_length=255, description="File path")
    file_size: int = Field(..., description="File size in bytes")

    commit_number: Optional[str] = Field(
        default=None, max_length=255, description="Commit number of the repo"
    )

    created_at: datetime = Field(default_factory=datetime.utcnow, description="Record creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Record last update timestamp")

    class Settings:
        name = "code_chunks"  # MongoDB collection name
        description = "Table for storing code chunks per repo of user"

    @before_event(Insert)
    @before_event(Replace)
    async def update_timestamp(self):
        """Automatically update timestamps before insert/replace."""
        self.updated_at = datetime.utcnow()
        if not self.created_at:
            self.created_at = datetime.utcnow()

    def __str__(self):
        return f"CodeChunks(id={self.id}, user_id={self.user_id}, repo_id={self.repo_id})"

    def __repr__(self):
        return self.__str__()
