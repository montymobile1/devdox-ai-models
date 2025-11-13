import uuid
from datetime import datetime
from typing import Optional

import pymongo
from beanie import Document, Indexed
from pydantic import Field

from models_src.models.beanie_odm.document_extra.timestamp import TimestampAuditMixin
from models_src.models.common.repo_enums import StatusTypes


class Repo(TimestampAuditMixin, Document):
    """
    Repository document for storing repository information from various Git providers.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)

    # Ownership
    user_id: Indexed(str) = Field(..., max_length=255, description="User ID who owns this repository")

    # Basic info
    repo_id: str = Field(..., max_length=255, description="Repository ID from the Git provider")
    repo_name: str = Field(..., max_length=255, description="Repository name")
    repo_parent_id: Optional[list[str]] = Field(None, description="List of parent repository IDs")

    description: Optional[str] = Field(None, description="Repository description")
    html_url: str = Field(..., max_length=500, description="Repository URL")

    # Metadata
    default_branch: str = Field(default="main", max_length=100, description="Default branch name")
    forks_count: int = Field(default=0, description="Number of forks")
    stargazers_count: int = Field(default=0, description="Number of stars")

    # Visibility/Privacy
    is_private: bool = Field(default=False, description="Whether repository is private")
    visibility: Optional[str] = Field(None, max_length=50, description="Repository visibility (GitLab)")

    # Provider / token
    token_id: Optional[str] = Field(None, max_length=255, description="Associated token ID")

    # Provider timestamps
    repo_created_at: Optional[datetime] = Field(None, description="Repository creation date from provider")
    repo_updated_at: Optional[datetime] = Field(None, description="Repository last update from provider")

    # Additional metadata
    language: Optional[list] = Field(None, description="Primary programming languages")

    size: Optional[int] = Field(
        default=None,
        description=(
            "Size of the Git repository in bytes. Represents only the .git directory contents, "
            "including commit history, branches, and git objects. Does not include release assets, "
            "LFS files, CI artifacts, or other non-Git storage."
        ),
    )

    relative_path: Optional[str] = Field(
        None, max_length=1024, description="Path to the repository relative to its hosting platform domain"
    )

    total_files: int = Field(default=0, description="Total files processed")
    total_chunks: int = Field(default=0, description="Total code chunks created")
    total_embeddings: int = Field(default=0, description="Total embeddings created")

    processing_start_time: Optional[datetime] = None
    processing_end_time: Optional[datetime] = None

    error_message: Optional[str] = Field(None, description="Error message if processing failed")

    last_commit: str = Field(default="", max_length=255)
    status: str = Field(default=StatusTypes.PENDING, max_length=255)

    # Local/system references
    repo_alias_name: str = Field(
        ...,
        max_length=100,
        description="User-defined alias used locally as an alternative to the provider repo name.",
    )
    repo_user_reference: Optional[str] = Field(
        None,
        description="An optional free-form description or note for this repository. Use this to explain its purpose, provide internal context, or document team-specific information.",
    )
    repo_system_reference: Optional[str] = Field(
        None,
        description="An optional System generated (no user intervention required) description or note for this repository. Explaining its purpose, provide internal context, or document team-specific information.",
    )

    repo_author_name: Optional[str] = Field(None, max_length=255, description="The name of the user who owns this repository")
    repo_author_email: Optional[str] = Field(None, max_length=255, description="The email address of the user who owns this repository")

    class Settings:
        name = "repo"
        description = "Repository information from Git providers"
        indexes = [
            pymongo.IndexModel(
                [("user_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)]
            ),
            pymongo.IndexModel(
                [("user_id", pymongo.ASCENDING), ("repo_id", pymongo.ASCENDING)],
                unique=True,
            ),
        ]

    def __str__(self) -> str:
        return f"{self.repo_name}"
