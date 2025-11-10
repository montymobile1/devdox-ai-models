import uuid
from datetime import datetime
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field

from models_src.models.document_extra.timestamp import TimestampAuditMixin

class APIKEY(TimestampAuditMixin, Document):
    """
    API Key document for storing user's API keys for external services
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)

    user_id: Indexed(str) = Field(
        ...,
        max_length=255,
        description="User identifier",
    )
    api_key: str = Field(
        ...,
        max_length=512,
        description="API Key for the context service",
    )
    masked_api_key: str = Field(
        ...,
        max_length=512,
        description="API Key masked",
    )

    is_active: bool = Field(default=True)
    
    last_used_at: Optional[datetime] = Field(
        default=None,
        description="Last time the API key was used",
    )

    class Settings:
        name = "api_key"
        description = "MongoDB Document for storing api key per user"

    def __str__(self) -> str:
        return f"APIKEY(id={self.id}, user_id={self.user_id}, masked_api_key={self.masked_api_key})"
    
    def __repr__(self):
        return self.__str__()