import datetime
import sys
import uuid
from pathlib import Path

from models_src.models import QRegistryStat

from models_src.dto.queue_job_claim_registry import QueueProcessingRegistryRequestDTO

from models_src import APIKeyRequestDTO, ApiLogRequestDTO, CodeChunksRequestDTO, GitHosting, GitLabelRequestDTO, RepoRequestDTO, \
    StatusTypes, UserRequestDTO

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def _make_api_log_request(
    user_id: str = "user-1",
    operation_id: str = "api_operation_id",
    path: str = "/some/api",
    method: str = "POST",
    request_received_at: datetime.datetime = datetime.datetime.now(datetime.timezone.utc),
    process_time_ms: int = 1,
    request_body: dict | list | None = None,
    response_body: dict | list | None = None,
) -> ApiLogRequestDTO:
    """
    Helper to build ApiLogRequestDTO consistently.
    """
    return ApiLogRequestDTO(
        user_id=user_id,
        operation_id=operation_id,
        path=path,
        method=method,
        request_received_at=request_received_at,
        process_time_ms=process_time_ms,
        request_body=request_body,
        response_body=response_body
    )

def _make_api_key_request(
    user_id: str = "user-1",
    api_key: str = "api-key-1",
    masked_api_key: str = "****-1",
    is_active: bool = True,
) -> APIKeyRequestDTO:
    """
    Helper to build APIKeyRequestDTO consistently.
    """
    return APIKeyRequestDTO(
        user_id=user_id,
        api_key=api_key,
        masked_api_key=masked_api_key,
        is_active=is_active,
    )


def _make_code_chunks_request(
    user_id: str = "user-1",
    repo_id: str = "repo-1",
    content: str = "print('hello')",
    file_name: str = "readme.md",
    file_path: str = "/readme.md",
    file_size: int = 123,
    commit_number: str = "abc123",
    embedding: list[float] | None = None,
    metadata: dict | None = None,
) -> CodeChunksRequestDTO:
    return CodeChunksRequestDTO(
        user_id=user_id,
        repo_id=repo_id,
        content=content,
        file_name=file_name,
        file_path=file_path,
        file_size=file_size,
        commit_number=commit_number,
        embedding=embedding,
        metadata=metadata or {},
    )


def _make_git_label_request(
    user_id: str = "user-1",
    label: str = "default-label",
    git_hosting: GitHosting = GitHosting.GITHUB,
    username: str = "user-name",
    token_value: str = "secret-token",
    masked_token: str = "****token",
) -> GitLabelRequestDTO:
    return GitLabelRequestDTO(
        user_id=user_id,
        label=label,
        git_hosting=git_hosting,
        username=username,
        token_value=token_value,
        masked_token=masked_token,
    )

def _make_queue_registry_request(
    message_id: str = "msg-1",
    queue_name: str = "queue-1",
    step: str = "step-1",
    status: QRegistryStat = QRegistryStat.PENDING,
    claimed_by: str | None = None,
    previous_message_id: uuid.UUID | None = None,
    claimed_at: datetime.datetime | None = None,
) -> QueueProcessingRegistryRequestDTO:
    return QueueProcessingRegistryRequestDTO(
        message_id=message_id,
        queue_name=queue_name,
        step=step,
        status=status,
        claimed_by=claimed_by,
        previous_message_id=previous_message_id,
        claimed_at=claimed_at,
    )


def _make_repo_request(
    user_id: str = "user-1",
    repo_id: str = "repo-1",
    repo_name: str = "my-repo",
    html_url: str = "https://github.com/user-1/my-repo",
    relative_path: str = "user-1/my-repo",
    repo_alias_name: str = "my-repo-alias",
    description: str | None = "desc",
    default_branch: str = "main",
    forks_count: int = 0,
    stargazers_count: int = 0,
    is_private: bool = False,
    visibility: str | None = None,
    token_id: str | None = None,
    status: str = StatusTypes.PENDING,
) -> RepoRequestDTO:
    return RepoRequestDTO(
        user_id=user_id,
        repo_id=repo_id,
        repo_name=repo_name,
        html_url=html_url,
        relative_path=relative_path,
        repo_alias_name=repo_alias_name,
        description=description,
        default_branch=default_branch,
        forks_count=forks_count,
        stargazers_count=stargazers_count,
        is_private=is_private,
        visibility=visibility,
        token_id=token_id,
        status=status,
    )


def _make_user_request(
    user_id: str = "user-1",
    first_name: str = "John",
    last_name: str = "Doe",
    email: str = "john.doe@example.com",
    role: str = "user",
    username: str = "johndoe",
    active: bool = True,
    membership_level: str = "free",
    token_limit: int = 0,
    token_used: int = 0,
    encryption_salt: str = "salt-1",
) -> UserRequestDTO:
    return UserRequestDTO(
        user_id=user_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        role=role,
        username=username,
        active=active,
        membership_level=membership_level,
        token_limit=token_limit,
        token_used=token_used,
        encryption_salt=encryption_salt,
    )
