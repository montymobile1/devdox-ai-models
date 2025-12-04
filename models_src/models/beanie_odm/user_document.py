import uuid

import pymongo
from beanie import Document, Indexed
from pydantic import BaseModel, ConfigDict, Field

from models_src.models.beanie_odm.document_extra.timestamp import TimestampAuditMixin


class User(TimestampAuditMixin, Document):
    """
    User document for storing user information from Clerk.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)

    user_id: Indexed(str) = Field(
        ...,
        max_length=255,
        description="User ID (from Clerk)",
    )

    first_name: str = Field(..., max_length=255, description="First name of user")
    last_name: str = Field(..., max_length=255, description="Last name of user")
    email: str = Field(..., max_length=255, description="Email of user")
    username: str = Field(default="", max_length=255, description="Username of user")
    role: str = Field(..., max_length=255, description="Role name of user")
    active: bool = Field(default=True)

    membership_level: str = Field(
        default="free", max_length=100, description="Default membership level"
    )
    token_limit: int = Field(default=0, description="Monthly token quota")
    token_used: int = Field(default=0, description="Tokens used this month")

    encryption_salt: str = Field(default="0", max_length=255, description="Encryption salt")

    class Settings:
        name = "user"
        
        description = "User information from Clerk"
        
        indexes = [
            
            pymongo.IndexModel(
                [("user_id", pymongo.ASCENDING)],
                name="user_user_id_unique",
                unique=True,
            ),
            
            pymongo.IndexModel(
                [("created_at", pymongo.DESCENDING)],
                name="user_created_at_desc",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.email})"

    def __repr__(self) -> str:
        return self.__str__()

class UserSimpleProjection(BaseModel):
    id: uuid.UUID = Field(alias="_id")
    encryption_salt: str

    # optional, but nice to have:
    model_config = ConfigDict(
        populate_by_name=True,  # can also construct with id=...
        extra="ignore",         # ignore any extra fields Mongo might send
    )