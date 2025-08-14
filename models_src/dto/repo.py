import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from uuid import UUID


class GitHosting(str, Enum):
    GITLAB = "gitlab"
    GITHUB = "github"


@dataclass
class RepoResponseDTO:
    id: Optional[UUID] = None
    user_id: Optional[str] = None
    repo_id: Optional[str] = None
    repo_name: Optional[str] = None
    description: Optional[str] = None
    html_url: Optional[str] = None
    default_branch: Optional[str] = None
    forks_count: Optional[int] = None
    stargazers_count: Optional[int] = None
    is_private: Optional[bool] = None
    visibility: Optional[str] = None
    token_id: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None
    repo_created_at: Optional[datetime.datetime] = None
    repo_updated_at: Optional[datetime.datetime] = None
    language: Optional[List[str]] = field(default_factory=list)
    size: Optional[int] = None
    relative_path: Optional[str] = None
    total_files: Optional[int] = None
    total_chunks: Optional[int] = None
    processing_start_time: Optional[datetime.datetime] = None
    processing_end_time: Optional[datetime.datetime] = None
    error_message: Optional[str] = None
    last_commit: Optional[str] = None
    status: Optional[str] = None
    repo_alias_name: Optional[str] = None
    repo_user_reference: Optional[str] = None
    repo_system_reference: Optional[str] = None


@dataclass
class RepoRequestDTO:

    user_id: str
    repo_id: str
    repo_name: str
    html_url: str
    repo_alias_name: str

    description: Optional[str] = None
    default_branch: str = "main"
    forks_count: int = 0
    stargazers_count: int = 0
    is_private: bool = False
    visibility: Optional[str] = None
    token_id: Optional[str] = None
    repo_created_at: Optional[datetime.datetime] = None
    repo_updated_at: Optional[datetime.datetime] = None
    language: Optional[List[str]] = None
    size: Optional[int] = None
    relative_path: Optional[str] = None
    total_files: int = 0
    total_chunks: int = 0
    processing_start_time: Optional[datetime.datetime] = None
    processing_end_time: Optional[datetime.datetime] = None
    error_message: Optional[str] = None
    last_commit: str = ""
    status: str = "pending"
    repo_user_reference: Optional[str] = None
    repo_system_reference: Optional[str] = None
