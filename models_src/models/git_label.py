import uuid
from datetime import datetime
from typing import Union
from beanie import PydanticObjectId
from beanie import Document, before_event, Insert, Replace
from pydantic import Field


class GitLabel(Document):
    """
    Git Label model for storing user's git hosting service credentials and labels
    """


    id: Union[uuid.UUID, PydanticObjectId] = Field(default_factory=uuid.uuid4)
    user_id: str = Field(..., max_length=255, description="User identifier")
    label: str = Field(..., description="Label/name for this git configuration")
    git_hosting: str = Field(..., max_length=50, description="Git hosting service (e.g., 'github', 'gitlab')")
    username: str = Field(..., description="Username for the git hosting service")
    token_value: str = Field(..., description="Access token for the git hosting service")
    masked_token: str = Field(..., description="Masked Access token for the git hosting service")

    created_at: datetime = Field(default_factory=datetime.utcnow, description="Record creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Record last update timestamp")


    class Settings:
        name = "git_label"  # MongoDB collection name
        description = "Table for storing git hosting service configurations per user"

    def __str__(self):
        return f"GitLabel(id={self.id}, user_id={self.user_id}, label={self.label}, git_hosting={self.git_hosting})"

    def __repr__(self):
        return self.__str__()

