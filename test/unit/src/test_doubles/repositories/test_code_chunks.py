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

        chk_1 = make_code_chunk_response(
            file_name="xyz_12345",
            content="print('xyz_12345')",
            created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2),
        )
        chk_2 = make_code_chunk_response(
            file_name="12345_xyz",
            content="print('12345_xyz')",
            created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1),
        )
        chk_3 = make_code_chunk_response(
            repo_id="different_repo_id", file_name="xyz", content="print('different_repo_id')"
        )

        fake.set_fake_data([chk_1, chk_2, chk_3])

        result = await fake.get_repo_file_chunks(
            user_id=chk_1.user_id, repo_id=chk_1.repo_id, file_name="xyz"
        )
        assert [{"content": chk_2.content}, {"content": chk_1.content}] == result

    async def test_get_user_repo_chunks_multi_success(self):
        """
        Two queries; one doc overlaps with both -> highest fusion_score.
        Fusion = sum of per-query cosine sims, MaxSim = max of per-query sims.
        Ordered by fusion_score DESC, then max_sim DESC, then created_at DESC.
        """
        fake = FakeCodeChunksStore()
        now = datetime.datetime.now(datetime.timezone.utc)

        # queries (unit norm k-hot by helper)
        q1 = k_hot_vectors([0])       # ||q1|| = 1
        q2 = k_hot_vectors([4])       # ||q2|| = 1
        queries = [q1, q2]

        # doc B overlaps with both q1 and q2 -> fusion highest
        doc_B = make_code_chunk_response(
            file_name="doc_B.py",
            content="print('B')",
            embedding=k_hot_vectors([0, 4, 7]),   # norm sqrt(3)
            created_at=now - datetime.timedelta(days=1),
        )
        # doc A orthogonal to both
        doc_A = make_code_chunk_response(
            file_name="doc_A.py",
            content="print('A')",
            embedding=k_hot_vectors([1, 2, 3]),
            created_at=now - datetime.timedelta(days=2),
        )
        # different repo -> filtered out
        doc_X = make_code_chunk_response(
            repo_id="other",
            file_name="doc_X.py",
            content="print('X')",
            embedding=k_hot_vectors([0, 4]),
            created_at=now,
        )

        fake.set_fake_data([doc_A, doc_B, doc_X])

        out = await fake.get_user_repo_chunks_multi(
            user_id=doc_A.user_id,
            repo_id=doc_A.repo_id,
            query_embeddings=queries,
            emb_dim=len(q1),
            limit=5,
        )

        # B comes first
        assert [r["file_name"] for r in out[:2]] == ["doc_B.py", "doc_A.py"]

        # Expected sims:
        # sim(q1, B) = 1/sqrt(3), sim(q2, B) = 1/sqrt(3)  => fusion_B = 2/sqrt(3)
        expected_fusion_B = 2 / math.sqrt(3)
        assert math.isclose(out[0]["fusion_score"], expected_fusion_B, abs_tol=ZERO_NORM_TOLERANCE)

        # A had no overlap => fusion ~ 0.0
        assert math.isclose(out[1]["fusion_score"], 0.0, abs_tol=ZERO_NORM_TOLERANCE)

    @pytest.mark.parametrize(
        "kwargs,case",
        [
            ({"query_embeddings": [k_hot_vectors([0, 5])], "emb_dim": 768, "user_id": "u", "repo_id": "r", "limit": -1}, "invalid limit"),
            ({"query_embeddings": [k_hot_vectors([0, 5])], "emb_dim": 768, "user_id": "u", "repo_id": None, "limit": 5}, "null repo"),
            ({"query_embeddings": [k_hot_vectors([0, 5])], "emb_dim": 768, "user_id": None, "repo_id": "r", "limit": 5}, "null user"),
            ({"query_embeddings": None, "emb_dim": 768, "user_id": "u", "repo_id": "r", "limit": 5}, "null embeddings"),
            # inconsistent dims (one 768, one 10) should be rejected
            ({"query_embeddings": [k_hot_vectors([0], dim=768), k_hot_vectors([1], dim=10)], "emb_dim": 768, "user_id": "u", "repo_id": "r", "limit": 5}, "inconsistent dims"),
            # emb_dim mismatch but consistent vectors still allowed? Our fake enforces vectors length == emb_dim, so this fails:
            ({"query_embeddings": [k_hot_vectors([0], dim=10)], "emb_dim": 768, "user_id": "u", "repo_id": "r", "limit": 5}, "emb_dim mismatch"),
        ],
        ids=["invalid limit", "Null repo_id", "Null user_id", "Null embeddings", "Inconsistent dims", "Emb_dim mismatch"],
    )
    async def test_get_user_repo_chunks_multi_invalid_params(self, kwargs, case):
        fake = FakeCodeChunksStore()
        out = await fake.get_user_repo_chunks_multi(**kwargs)
        assert out == []

    async def test_bulk_save_inserts_data(self):
        fake = FakeCodeChunksStore()

        dto_list = []
        for i in range(2):
            dto_list.append(
                CodeChunksRequestDTO(
                    user_id="u1",
                    repo_id=f"r{i}",
                    content=f"print('hi from r{i}')",
                    file_name=f"main{i}.py",
                    file_path=f"/main{i}.py",
                    file_size=i * 10,
                    commit_number="commit1",
                )
            )

        result_list = await fake.bulk_save(create_model=dto_list)

        assert fake.total_count == len(dto_list)
        assert len(result_list) == len(dto_list)
        for index, res in enumerate(result_list):
            assert res in fake.data_store
            assert res.id is not None
            assert res.created_at is not None
            assert res.repo_id == dto_list[index].repo_id


@pytest.mark.asyncio
class TestStubCodeChunksStore:
    async def test_output_mechanism(self) -> None:
        stub = StubCodeChunksStore()

        save = stub.save
        bulk_save = stub.bulk_save
        find_all_by_repo_id_with_limit = stub.find_all_by_repo_id_with_limit
        get_repo_file_chunks = stub.get_repo_file_chunks
        get_user_repo_chunks_multi = stub.get_user_repo_chunks_multi

        generated = make_code_chunk_response()

        # shape the multi-response the way production returns (dict rows + fusion/max)
        multi_resp = [
            {**asdict(generated), "fusion_score": 0.9, "max_sim": 0.9},
            {**asdict(generated), "fusion_score": 0.5, "max_sim": 0.5},
        ]

        expected = {
            save.__name__: generated,
            bulk_save.__name__: [generated],
            find_all_by_repo_id_with_limit.__name__: [generated, generated],
            get_repo_file_chunks.__name__: [{"content": generated.content}, {"content": generated.content}],
            get_user_repo_chunks_multi.__name__: multi_resp,
        }

        stub.set_output(save, expected[save.__name__])
        stub.set_output(bulk_save, expected[bulk_save.__name__])
        stub.set_output(find_all_by_repo_id_with_limit, expected[find_all_by_repo_id_with_limit.__name__])
        stub.set_output(get_repo_file_chunks, expected[get_repo_file_chunks.__name__])
        stub.set_output(get_user_repo_chunks_multi, expected[get_user_repo_chunks_multi.__name__])

        await save(
            create_model=CodeChunksRequestDTO(
                user_id="u1",
                repo_id="r1",
                content="print('hi')",
                file_name="main.py",
                file_path="/main.py",
                file_size=100,
                commit_number="commit1",
            )
        )

        await bulk_save(
            create_model=[
                CodeChunksRequestDTO(
                    user_id="u1",
                    repo_id="r1",
                    content="print('hi')",
                    file_name="main.py",
                    file_path="/main.py",
                    file_size=100,
                    commit_number="commit1",
                )
            ]
        )

        await find_all_by_repo_id_with_limit(repo_id=generated.repo_id, limit=100)
        await get_repo_file_chunks(user_id=generated.user_id, repo_id=generated.repo_id, file_name=generated.file_name)

        await get_user_repo_chunks_multi(
            user_id=generated.user_id,
            repo_id=generated.repo_id,
            query_embeddings=[k_hot_vectors([2, 3])],
            emb_dim=768,
            limit=5,
        )

        assert expected == stub._outputs
