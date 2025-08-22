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
    FakeCodeChunksStore,
    StubCodeChunksStore, ZERO_NORM_TOLERANCE,
)

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
        embedding=kwargs.get("embedding") if kwargs.get("embedding") else generate_random_vector(),
        metadata=kwargs.get("metadata", {}),
        created_at=kwargs.get("created_at", now)
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

    async def test_get_repo_file_chunks(self):
        fake = FakeCodeChunksStore()

        chk_1 = make_code_chunk_response(file_name="xyz_12345", content="print('xyz_12345')", created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2))
        chk_2 = make_code_chunk_response(file_name="12345_xyz", content="print('12345_xyz')", created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        chk_3 = make_code_chunk_response(repo_id="different_repo_id", file_name="xyz", content="print('different_repo_id')")

        fake.set_fake_data([chk_1, chk_2, chk_3])

        result = await fake.get_repo_file_chunks(user_id=chk_1.user_id , repo_id=chk_1.repo_id,  file_name="xyz")
        assert [{"content": chk_2.content}, {"content": chk_1.content}] == result

    async def test_similarity_search_success(self):
        fake = FakeCodeChunksStore()

        embedding_vector = generate_random_vector()

        chk_1 = make_code_chunk_response(
            file_name="xyz_12345",
            content="print('xyz_12345')",
            embedding=generate_random_vector(),
            created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)
        )

        chk_2 = make_code_chunk_response(
            file_name="12345_xyz",
            content="print('12345_xyz')",
            embedding=generate_random_vector(),
            created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
        )

        chk_3 = make_code_chunk_response(repo_id="different_repo_id", file_name="xyz", content="print('different_repo_id')", embedding=generate_random_vector())

        fake.set_fake_data([chk_1, chk_2, chk_3])

        result = await fake.similarity_search(
            embedding=embedding_vector,
            user_id=chk_1.user_id,
            repo_id=chk_1.repo_id,
            limit= 5
        )

        assert round(fake.calculate_score(chk_2.embedding, embedding_vector), 1) == round(result[0]["score"], 1)
        assert round(fake.calculate_score(chk_1.embedding, embedding_vector), 1) == round(result[1]["score"], 1)

    @pytest.mark.parametrize(
        "input_kwarg",
        [
            {"embedding":generate_random_vector(), "user_id":"valid_user_id", "repo_id":"valid_repo_id", "limit": -1 },
            {"embedding":generate_random_vector(), "user_id":"valid_user_id", "repo_id":None, "limit": 5 },
            {"embedding":generate_random_vector(), "user_id": None, "repo_id":"valid_repo_id", "limit": 5 },
            {"embedding":None, "user_id": "valid_user_id", "repo_id":"valid_repo_id", "limit": 5 },
            {"embedding":generate_random_vector()[:10], "user_id": "valid_user_id", "repo_id":"valid_repo_id", "limit": 5 },
         ],
        ids=[
            "invalid limit", "Null repo_id", "Null user_id","embedding not of valid length", "Null embedding"
        ]
    )
    async def test_similarity_search_invalid_params(self, input_kwarg):
        fake = FakeCodeChunksStore()

        result = await fake.similarity_search(
            **input_kwarg
        )

        assert result == []


@pytest.mark.asyncio
class TestStubCodeChunksStore:
    async def test_output_mechanism(self) -> None:
        stub = StubCodeChunksStore()

        save = stub.save
        find_all_by_repo_id_with_limit = stub.find_all_by_repo_id_with_limit
        get_repo_file_chunks = stub.get_repo_file_chunks
        get_user_repo_chunks = stub.get_user_repo_chunks

        generated_response = make_code_chunk_response()

        expected_result = {
            save.__name__: generated_response,
            find_all_by_repo_id_with_limit.__name__: [generated_response,generated_response],
            get_repo_file_chunks.__name__: [{"content": generated_response.content}, {"content": generated_response.content}],
            get_user_repo_chunks.__name__: [asdict(generated_response), asdict(generated_response)],
        }

        stub.set_output(save, expected_result.get(save.__name__) )
        stub.set_output(find_all_by_repo_id_with_limit, expected_result.get(find_all_by_repo_id_with_limit.__name__) )
        stub.set_output(get_repo_file_chunks, expected_result.get(get_repo_file_chunks.__name__) )
        stub.set_output(get_user_repo_chunks, expected_result.get(get_user_repo_chunks.__name__) )

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
        
        await get_repo_file_chunks(user_id=generated_response.user_id, repo_id=generated_response.repo_id, file_name=generated_response.file_name)
        
        await get_user_repo_chunks(user_id=generated_response.user_id, repo_id=generated_response.repo_id, query_embedding=generate_random_vector(), limit= 5)

        assert expected_result == stub._outputs
