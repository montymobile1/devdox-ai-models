import datetime
import uuid

import pytest

from models_src.dto.code_chunks import CodeChunksRequestDTO, CodeChunksResponseDTO
from models_src.test_doubles.repositories.code_chunks import FakeCodeChunksStore


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
        embedding=kwargs.get("embedding"),
        metadata=kwargs.get("metadata", {}),
        created_at=kwargs.get("created_at", now),
    )


@pytest.mark.asyncio
async def test_set_fake_data_populates_store():
    fake = FakeCodeChunksStore()
    data = [make_code_chunk_response(repo_id="r1"), make_code_chunk_response(repo_id="r2")]
    fake.set_fake_data(data)

    assert fake.total_count == 2
    assert len(fake.data_store) == 2
    assert all(isinstance(item, CodeChunksResponseDTO) for item in fake.data_store)


@pytest.mark.asyncio
async def test_save_inserts_data_correctly():
    fake = FakeCodeChunksStore()
    dto = CodeChunksRequestDTO(
        user_id="u1",
        repo_id="r1",
        content="print('hi')",
        file_name="main.py",
        file_path="/main.py",
        file_size=100,
        commit_number="commit1",
    )
    result = await fake.save(dto)

    assert result.id is not None
    assert result.created_at is not None
    assert result.repo_id == "r1"
    assert fake.total_count == 1
    assert result in fake.data_store


@pytest.mark.asyncio
async def test_find_all_by_repo_id_with_limit():
    fake = FakeCodeChunksStore()
    r1 = make_code_chunk_response(repo_id="r1")
    r2 = make_code_chunk_response(repo_id="r1")
    r3 = make_code_chunk_response(repo_id="r2")
    fake.set_fake_data([r1, r2, r3])

    result = await fake.find_all_by_repo_id_with_limit(repo_id="r1", limit=2)

    assert len(result) == 2
    assert all(r.repo_id == "r1" for r in result)


@pytest.mark.asyncio
async def test_find_all_by_repo_id_with_limit_applies_limit():
    fake = FakeCodeChunksStore()
    chunks = [make_code_chunk_response(repo_id="repo") for _ in range(5)]
    fake.set_fake_data(chunks)

    result = await fake.find_all_by_repo_id_with_limit(repo_id="repo", limit=3)

    assert len(result) == 3


@pytest.mark.asyncio
async def test_find_all_by_repo_id_with_limit_handles_empty():
    fake = FakeCodeChunksStore()
    result = await fake.find_all_by_repo_id_with_limit(repo_id="not-there", limit=5)
    assert result == []
