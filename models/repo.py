from tortoise.models import Model
from tortoise import fields
import uuid


class Repo(Model):
    """
    Repository model for storing repository information from various Git providers
    """

    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    user_id = fields.CharField(
     max_length=255, description="User ID who owns this repository"
    )

    # Repository basic information
    repo_id = fields.CharField(
        max_length=255, description="Repository ID from the Git provider"
    )
    repo_name = fields.CharField(max_length=255, description="Repository name")
    description = fields.TextField(null=True, description="Repository description")
    html_url = fields.CharField(max_length=500, description="Repository URL")

    # Repository metadata
    default_branch = fields.CharField(
        max_length=100, default="main", description="Default branch name"
    )
    forks_count = fields.IntField(default=0, description="Number of forks")
    stargazers_count = fields.IntField(default=0, description="Number of stars")

    # Visibility/Privacy settings
    is_private = fields.BooleanField(
        default=False, description="Whether repository is private"
    )
    visibility = fields.CharField(
        max_length=50, null=True, description="Repository visibility (GitLab)"
    )

    # Git provider information
    token_id = fields.CharField(
        max_length=255, null=True, description="Associated token ID"
    )

    # Timestamps
    created_at = fields.DatetimeField(
        auto_now_add=True, description="Record creation timestamp"
    )
    updated_at = fields.DatetimeField(
        auto_now=True, description="Record update timestamp"
    )

    # Repository timestamps from provider
    repo_created_at = fields.DatetimeField(
        null=True, description="Repository creation date from provider"
    )
    repo_updated_at = fields.DatetimeField(
        null=True, description="Repository last update from provider"
    )

    # Additional metadata
    language = fields.JSONField(null=True, description="Primary programming languages")
    
    size = fields.IntField(
        null=True,
        description="Size of the Git repository in bytes. Represents only the .git directory contents, including commit history, branches, and git objects. Does not include release assets, LFS files, CI artifacts, or other non-Git storage"
    )
    
    relative_path = fields.CharField(
        max_length=1024, null=True, description="The path to the repository relative to its hosting platform domain"
    )
    total_files = fields.IntField(default=0, description="Total files processed")
    total_chunks = fields.IntField(default=0, description="Total code chunks created")
    processing_start_time = fields.DatetimeField(null=True)
    processing_end_time = fields.DatetimeField(null=True)
    error_message = fields.TextField(null=True, description="Error message if processing failed")
    last_commit = fields.CharField(max_length=255, default="")
    status = fields.CharField(max_length=255, default="pending")
    
    repo_alias_name = fields.CharField(
        max_length=100,
        description="A user-defined alias for this repository, used locally within this system as an alternative to the official GitHub or GitLab repository name."
    )

    repo_user_reference = fields.TextField(
        null=True,
        description="An optional free-form description or note for this repository. Use this to explain its purpose, provide internal context, or document team-specific information."
    )
    
    repo_system_reference = fields.TextField(
        null=True,
        description="An optional System generated (no user intervention required) description or note for this repository. Explaining its purpose, provide internal context, or document team-specific information."
    )
    
    class Meta:
        table = "repo"
        table_description = "Repository information from Git providers"
        indexes = [
            ("user_id", "created_at"),
        ]
        
        unique_together = (
            ("user_id", "repo_id"),
        )

    def __str__(self):
        return f"{self.repo_name} "
