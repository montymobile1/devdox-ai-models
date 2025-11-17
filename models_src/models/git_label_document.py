import uuid

import pymongo
from beanie import Document, Indexed
from pydantic import BaseModel, ConfigDict, Field

from models_src.models.document_extra.timestamp import TimestampAuditMixin


class GitLabel(TimestampAuditMixin, Document):
    """
    Git Label model for storing user's git hosting service credentials and labels
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)

    user_id: Indexed(str) = Field(..., max_length=255, description="User identifier")
    label: str = Field(..., description="Label/name for this git configuration")
    git_hosting: str = Field(
        ...,
        max_length=50,
        description="Git hosting service (e.g., 'github', 'gitlab')",
    )
    username: str = Field(..., description="Username for the git hosting service")

    token_value: str = Field(..., description="Access token for the git hosting service")

    masked_token: str = Field(
        ...,
        description="Masked access token for display/logging",
    )

    class Settings:
        name = "git_label"
        
        description = (
            "MongoDB Document for storing git hosting service configurations per user"
        )
        
        indexes = [
            
            pymongo.IndexModel(
                [("user_id", pymongo.ASCENDING),
                 ("git_hosting", pymongo.ASCENDING),
                 ("masked_token", pymongo.ASCENDING)],
                unique=True,
            )
        ]

    def __str__(self) -> str:
        return f"GitLabel(id={self.id}, user_id={self.user_id}, label={self.label}, git_hosting={self.git_hosting})"

    def __repr__(self) -> str:
        return self.__str__()

    
class GitLabelProjection(BaseModel):
    id: uuid.UUID = Field(alias="_id")
    git_hosting: str

    # optional, but nice to have:
    model_config = ConfigDict(
        populate_by_name=True,  # can also construct with id=...
        extra="ignore",         # ignore any extra fields Mongo might send
    )
