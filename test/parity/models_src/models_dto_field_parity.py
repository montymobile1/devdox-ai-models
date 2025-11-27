import dataclasses
from dataclasses import fields, is_dataclass
from typing import Iterable, List, Optional, Set, Type

from tortoise import Model

from models_src.dto.api_key import APIKeyResponseDTO
from models_src.dto.code_chunks import CodeChunksResponseDTO
from models_src.dto.git_label import GitLabelResponseDTO
from models_src.dto.queue_job_claim_registry import QueueProcessingRegistryResponseDTO
from models_src.dto.repo import RepoResponseDTO
from models_src.dto.user import UserResponseDTO
from models_src.models.tortoise_orm.api_key import APIKEY
from models_src.models.tortoise_orm.code_chunks import CodeChunks
from models_src.models.tortoise_orm.git_label import GitLabel
from models_src.models.tortoise_orm.queue_job_claim_registry import QueueProcessingRegistry
from models_src.models.tortoise_orm.repo import Repo
from models_src.models.tortoise_orm.user import User

def symmetric_field_diff(
    dataclass_type: Type[dataclasses.dataclass],
    tortoise_model: Type[Model],
    exclude: Optional[Iterable[str]] = None,
) -> List[str]:
    """
    Return a sorted list of field names that exist in exactly one of:
      1) the given dataclass (by dataclass field names), or
      2) the given Tortoise ORM model (_meta.fields_map keys).

    Args:
        dataclass_type: The dataclass *type* to inspect.
        tortoise_model: The Tortoise ORM model *class* to inspect.
        exclude: Optional iterable of field names to remove from the final diff.

    Example:
        diff = symmetric_field_diff(UserDTO, UserModel, exclude={"created_at", "updated_at"})
    """
    if not is_dataclass(dataclass_type):
        raise TypeError("dataclass_type must be a dataclass type (class decorated with @dataclass).")

    dto_fields: Set[str] = {f.name for f in fields(dataclass_type)}
    orm_fields: Set[str] = set(getattr(tortoise_model, "_meta").fields_map.keys())

    diff = dto_fields ^ orm_fields  # symmetric difference

    if exclude:
        diff -= set(exclude)

    return sorted(diff)

class TestAPIKEY:
    def test_with_apikey_response_dto(self):
        symmetric_diff = symmetric_field_diff(APIKeyResponseDTO, APIKEY)
        assert len(symmetric_diff) == 0

class TestCodeChunks:
    def test_with_code_chunks_response_dto(self):
        symmetric_diff = symmetric_field_diff(CodeChunksResponseDTO, CodeChunks)
        assert len(symmetric_diff) == 0

class TestGitLabel:
    def test_with_git_label_response_dto(self):
        symmetric_diff = symmetric_field_diff(GitLabelResponseDTO, GitLabel)
        assert len(symmetric_diff) == 0

class TestQueueProcessingRegistry:
    def test_with_queue_processing_registry_response_dto(self):
        symmetric_diff = symmetric_field_diff(QueueProcessingRegistryResponseDTO, QueueProcessingRegistry)
        assert len(symmetric_diff) == 0

class TestRepo:
    def test_with_repo_response_dto(self):
        symmetric_diff = symmetric_field_diff(RepoResponseDTO, Repo)
        assert len(symmetric_diff) == 0

class TestUser:
    def test_with_user_response_dto(self):
        symmetric_diff = symmetric_field_diff(UserResponseDTO, User)
        assert len(symmetric_diff) == 0