from __future__ import annotations

import datetime
import uuid
from typing import Optional, List

import pymongo
from beanie import Document, Indexed
from pydantic import BaseModel, ConfigDict, Field, field_validator

from models_src.exceptions.exception_constants import EMBEDDINGS_INVALID_SIZE
from models_src.models.document_extra.timestamp import TimestampAuditMixin

EMBED_DIM = 768  # set to your model's dimension

class CodeChunks(TimestampAuditMixin, Document):
    """
    Code chunks per repo; embeddings are stored as a plain list[float].
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: Indexed(str) = Field(..., max_length=255, description="User identifier")
    repo_id: str = Field(..., max_length=255, description="Repo identifier")

    content: str = Field(..., description="Chunk content")

    embedding: Optional[List[float]] = Field(
        default=None,
        description=f"Embedding vector (length={EMBED_DIM})"
    )

    metadata: dict = Field(default_factory=dict, description="Free-form metadata")
    file_name: str = Field(..., max_length=255, description="File name")
    file_path: str = Field(..., max_length=255, description="File path")
    file_size: int = Field(..., description="File size in bytes")

    commit_number: str = Field(..., max_length=255, description="Commit hash/number")

    class Settings:
        name = "code_chunks"
        
        indexes = [
            pymongo.IndexModel([("user_id", 1), ("repo_id", 1)]),
            pymongo.IndexModel([("repo_id", 1), ("file_path", 1)]),
            pymongo.IndexModel([("repo_id", 1), ("commit_number", 1)]),
        ]

    @field_validator("embedding")
    @classmethod
    def _check_embedding_len(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        if v is None:
            return v
        if len(v) != EMBED_DIM:
            raise ValueError(EMBEDDINGS_INVALID_SIZE.format(EMBED_DIM=EMBED_DIM, ARRAY_LENGTH=len(v)))
        return v

    def __str__(self) -> str:
        return f"CodeChunks(id={self.id}, user_id={self.user_id}, repo_id={self.repo_id})"

    def __repr__(self) -> str:
        return self.__str__()

class CodeChunksProjection(BaseModel):
    content: str

class CodeChunksSearchProjection(BaseModel):
    """Only pull what's needed to compute scores and build the response."""
    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID = Field(alias="_id")
    file_name: str
    file_path: str
    content: str
    created_at: datetime.datetime
    embedding: List[float] | None = None