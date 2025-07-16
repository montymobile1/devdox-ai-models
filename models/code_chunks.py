import uuid
from tortoise.models import Model
from typing import List, Optional
from tortoise import fields


class CodeChunks(Model):
    """
    API Key model for storing user's API keys for external services
    """

    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    user_id = fields.CharField(
        max_length=255, null=False, description="User identifier"
    )
    repo_id = fields.CharField(
        required=True, max_length=255, null=False, description="Repo identifier"
    )
    content = fields.TextField(required=True, null=False)

    embedding = fields.JSONField(null=True, description="Vector embedding as JSON array")
    metadata = fields.JSONField(default=dict)
    file_name = fields.CharField(
        required=True, max_length=255, null=False, description="File name"
    )
    file_path = fields.CharField(
        required=True, max_length=255, null=False, description="File path"
    )
    file_size = fields.IntField(
        required=True,
    )

    commit_number = fields.CharField(
        description="Commit number of the repo",
        max_length=255,
    )

    created_at = fields.DatetimeField(
        auto_now_add=True, description="Record creation timestamp"
    )

    class Meta:
        table = "code_chunks"
        table_description = "Table for storing code chunks per repo of user"

    def __str__(self):
        return (
            f"CodeChunks(id={self.id}, user_id={self.user_id}, "
            f"repo_id={self.repo_id})"
        )

    @property
    def embedding_json(self) -> Optional[List[float]]:
        """Get embedding as a list of floats."""
        if self.embedding is None:
            return None
        return self.embedding

    @embedding_json.setter
    def embedding_json(self, value: Optional[List[float]]):
        """Set embedding from a list of floats."""
        self.embedding = value

    def __repr__(self):
        return self.__str__()
