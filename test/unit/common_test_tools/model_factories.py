import uuid
import datetime as dt
from models_src.models import APIKEY, GitLabel, QueueProcessingRegistry, QRegistryStat, Repo, User, CodeChunks

def make_apikey(
    *,
    id: uuid.UUID | None = None,
    user_id: str = "u1",
    api_key: str = "K1",
    masked_api_key: str = "*K1*",
    is_active: bool = True,
    created_at: dt.datetime | None = None,
    updated_at: dt.datetime | None = None,
    last_used_at: dt.datetime | None = None,
) -> APIKEY:
    id = id or uuid.uuid4()
    now = dt.datetime.now(dt.timezone.utc)
    created_at = created_at or now
    updated_at = updated_at or now
    return APIKEY(
        id=id,
        user_id=user_id,
        api_key=api_key,
        masked_api_key=masked_api_key,
        is_active=is_active,
        created_at=created_at,
        updated_at=updated_at,
        last_used_at=last_used_at,
    )

def make_gitlabel(
    *,
    id: uuid.UUID | None = None,
    user_id: str = "u1",
    label: str = "default",
    git_hosting: str = "github",
    username: str = "alice",
    token_value: str = "tok_123",
    masked_token: str = "*123",
    created_at: dt.datetime | None = None,
    updated_at: dt.datetime | None = None,
) -> GitLabel:
    id = id or uuid.uuid4()
    now = dt.datetime.now(dt.timezone.utc)
    created_at = created_at or now
    updated_at = updated_at or now
    return GitLabel(
        id=id,
        user_id=user_id,
        label=label,
        git_hosting=git_hosting,
        username=username,
        token_value=token_value,
        masked_token=masked_token,
        created_at=created_at,
        updated_at=updated_at,
    )

def make_qreg(
    *,
    id: uuid.UUID | None = None,
    message_id: str = "msg-1",
    queue_name: str = "default",
    step: str = "ingest",
    status: QRegistryStat = QRegistryStat.PENDING,
    claimed_by: str | None = None,
    previous_message_id: uuid.UUID | None = None,
    claimed_at: dt.datetime | None = None,
    updated_at: dt.datetime | None = None,
) -> QueueProcessingRegistry:
    id = id or uuid.uuid4()
    now = dt.datetime.now(dt.timezone.utc)
    claimed_at = claimed_at or now
    updated_at = updated_at or now
    return QueueProcessingRegistry(
        id=id,
        message_id=message_id,
        queue_name=queue_name,
        claimed_by=claimed_by,
        step=step,
        status=status,
        previous_message_id=previous_message_id,
        claimed_at=claimed_at,
        updated_at=updated_at,
    )

def make_repo(
    *,
    id: uuid.UUID | None = None,
    user_id: str = "u1",
    repo_id: str = "r1",
    repo_name: str = "demo",
    description: str | None = None,
    html_url: str = "https://example.com/u1/demo",
    default_branch: str = "main",
    forks_count: int = 0,
    stargazers_count: int = 0,
    is_private: bool = False,
    visibility: str | None = None,
    token_id: str | None = None,
    created_at: dt.datetime | None = None,
    updated_at: dt.datetime | None = None,
    repo_created_at: dt.datetime | None = None,
    repo_updated_at: dt.datetime | None = None,
    language: list[str] | None = None,
    size: int | None = None,
    relative_path: str | None = None,
    total_files: int = 0,
    total_chunks: int = 0,
    total_embeddings: int = 0,
    processing_start_time: dt.datetime | None = None,
    processing_end_time: dt.datetime | None = None,
    error_message: str | None = None,
    last_commit: str = "",
    status: str = "pending",
    repo_alias_name: str = "alias-demo",
    repo_user_reference: str | None = None,
    repo_system_reference: str | None = None,
) -> Repo:
    id = id or uuid.uuid4()
    now = dt.datetime.now(dt.timezone.utc)
    created_at = created_at or now
    updated_at = updated_at or now
    language = language if language is not None else ["Python"]

    return Repo(
        id=id,
        user_id=user_id,
        repo_id=repo_id,
        repo_name=repo_name,
        description=description,
        html_url=html_url,
        default_branch=default_branch,
        forks_count=forks_count,
        stargazers_count=stargazers_count,
        is_private=is_private,
        visibility=visibility,
        token_id=token_id,
        created_at=created_at,
        updated_at=updated_at,
        repo_created_at=repo_created_at,
        repo_updated_at=repo_updated_at,
        language=language,
        size=size,
        relative_path=relative_path,
        total_files=total_files,
        total_chunks=total_chunks,
        total_embeddings=total_embeddings,
        processing_start_time=processing_start_time,
        processing_end_time=processing_end_time,
        error_message=error_message,
        last_commit=last_commit,
        status=status,
        repo_alias_name=repo_alias_name,
        repo_user_reference=repo_user_reference,
        repo_system_reference=repo_system_reference,
    )

def make_user(
    *,
    id: uuid.UUID | None = None,
    user_id: str = "u1",
    first_name: str = "Alice",
    last_name: str = "Doe",
    email: str = "alice@example.com",
    username: str = "",
    role: str = "member",
    active: bool = True,
    membership_level: str = "free",
    token_limit: int = 0,
    token_used: int = 0,
    created_at: dt.datetime | None = None,
    updated_at: dt.datetime | None = None,
    encryption_salt: str = "0",
) -> User:
    id = id or uuid.uuid4()
    now = dt.datetime.now(dt.timezone.utc)
    created_at = created_at or now
    updated_at = updated_at or now
    return User(
        id=id,
        user_id=user_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        username=username,
        role=role,
        active=active,
        membership_level=membership_level,
        token_limit=token_limit,
        token_used=token_used,
        created_at=created_at,
        updated_at=updated_at,
        encryption_salt=encryption_salt,
    )

def make_codechunk(
    *,
    id: uuid.UUID | None = None,
    user_id: str = "u1",
    repo_id: str = "r1",
    content: str = "print('hello')",
    file_name: str = "app.py",
    file_path: str = "src/app.py",
    file_size: int = 12,
    commit_number: str = "abc123",
    embedding=None,  # leave as None in unit tests (we don't touch DB/vector ops)
    metadata: dict | None = None,
    created_at: dt.datetime | None = None,
) -> CodeChunks:
    id = id or uuid.uuid4()
    now = dt.datetime.now(dt.timezone.utc)
    created_at = created_at or now
    metadata = metadata if metadata is not None else {}

    return CodeChunks(
        id=id,
        user_id=user_id,
        repo_id=repo_id,
        content=content,
        embedding=embedding,
        metadata=metadata,
        file_name=file_name,
        file_path=file_path,
        file_size=file_size,
        commit_number=commit_number,
        created_at=created_at,
    )