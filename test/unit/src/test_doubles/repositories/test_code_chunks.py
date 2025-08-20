import datetime
import uuid
import pytest

from models_src.dto.code_chunks import CodeChunksRequestDTO, CodeChunksResponseDTO
from models_src.test_doubles.repositories.code_chunks import (
    FakeCodeChunksStore,
    StubCodeChunksStore,
)


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
class TestFakeCodeChunksStore:
    async def test_set_fake_data_populates_store(self):
        fake = FakeCodeChunksStore()
        data = [make_code_chunk_response(repo_id="r1"), make_code_chunk_response(repo_id="r2")]
        fake.set_fake_data(data)
    
        assert fake.total_count == 2
        assert len(fake.data_store) == 2
        assert all(isinstance(item, CodeChunksResponseDTO) for item in fake.data_store)
    
    async def test_save_inserts_data_correctly(self):
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
    
    async def test_find_all_by_repo_id_with_limit(self):
        fake = FakeCodeChunksStore()
        r1 = make_code_chunk_response(repo_id="r1")
        r2 = make_code_chunk_response(repo_id="r1")
        r3 = make_code_chunk_response(repo_id="r2")
        fake.set_fake_data([r1, r2, r3])
    
        result = await fake.find_all_by_repo_id_with_limit(repo_id="r1", limit=2)
    
        assert len(result) == 2
        assert all(r.repo_id == "r1" for r in result)
    
    async def test_find_all_by_repo_id_with_limit_applies_limit(self):
        fake = FakeCodeChunksStore()
        chunks = [make_code_chunk_response(repo_id="repo") for _ in range(5)]
        fake.set_fake_data(chunks)
    
        result = await fake.find_all_by_repo_id_with_limit(repo_id="repo", limit=3)
    
        assert len(result) == 3
    
    async def test_find_all_by_repo_id_with_limit_handles_empty(self):
        fake = FakeCodeChunksStore()
        result = await fake.find_all_by_repo_id_with_limit(repo_id="not-there", limit=5)
        assert result == []

@pytest.mark.asyncio
class TestStubCodeChunksStore:
    async def test_output_mechanism(self) -> None:
        stub = StubCodeChunksStore()

        save = stub.save
        find_all_by_repo_id_with_limit = stub.find_all_by_repo_id_with_limit

        generated_response = make_code_chunk_response()

        expected_result = {
            save.__name__: generated_response,
            find_all_by_repo_id_with_limit.__name__: [generated_response,generated_response],
        }

        stub.set_output(save, expected_result.get(save.__name__) )
        stub.set_output(find_all_by_repo_id_with_limit, expected_result.get(find_all_by_repo_id_with_limit.__name__) )

        await save(create_model=CodeChunksRequestDTO(
            user_id="u1",
            repo_id="r1",
            content="print('hi')",
            file_name="main.py",
            file_path="/main.py",
            file_size=100,
            commit_number="commit1",
        ))
        
        await find_all_by_repo_id_with_limit(repo_id=generated_response.repo_id, limit= 100)

        assert expected_result == stub._outputs
