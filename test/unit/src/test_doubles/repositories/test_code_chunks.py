import datetime
import logging
import math
import random
import uuid
from dataclasses import asdict
from typing import List

import pytest

from models_src.dto.code_chunks import CodeChunksRequestDTO, CodeChunksResponseDTO
from models_src.test_doubles.repositories.code_chunks import (
    EMBED_DIM,
    FakeCodeChunksStore,
    StubCodeChunksStore,
    ZERO_NORM_TOLERANCE,
)


def k_hot_vectors(indices: list[int], dim: int = EMBED_DIM, normalize: bool = True) -> list[float]:
    if not indices:
        raise ValueError("indices must not be empty")
    v = [0.0] * dim
    for i in indices:
        if not (0 <= i < dim):
            raise ValueError(f"index {i} out of range 0..{dim-1}")
        v[i] = 1.0
    if normalize:
        inv = 1.0 / math.sqrt(len(indices))  # unit length
        v = [x * inv for x in v]
    return v


def generate_random_vector() -> List[float]:
    while True:
        vec = [round(random.random(), 6) for _ in range(768)]  # [0.0, 1.0)
        norm = math.sqrt(sum(x * x for x in vec))
        if norm >= ZERO_NORM_TOLERANCE:
            return vec


def make_code_chunk_response(**kwargs) -> CodeChunksResponseDTO:
    now = datetime.datetime.now(datetime.timezone.utc)
    return CodeChunksResponseDTO(
        id=uuid.uuid4(),
        user_id=kwargs.get("user_id", "user1"),
        repo_id=kwargs.get("repo_id", "repo1"),
        content=kwargs.get("content", "print('hello')"),
        file_name=kwargs.get("file_name", "main.py"),
        file_path=kwargs.get("file_path", "/main.py"),
        file_size=kwargs.get("file_size", 123),
        commit_number=kwargs.get("commit_number", "abc123"),
        embedding=kwargs.get("embedding") if kwargs.get("embedding") else k_hot_vectors([0]),
        metadata=kwargs.get("metadata", {}),
        created_at=kwargs.get("created_at", now)
    )
