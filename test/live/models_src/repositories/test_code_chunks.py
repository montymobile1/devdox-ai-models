import datetime
import uuid

import pytest
import pytest_asyncio
import math

from models_src import EMBED_DIM, InMemoryGitLabelBackend

from models_src.dto.code_chunks import CodeChunksRequestDTO, CodeChunksResponseDTO
from models_src.exceptions.exception_constants import EMBEDDINGS_INVALID_SIZE
from models_src.repositories.code_chunks import BeanieCodeChunksBackend, ICodeChunksStore, InMemoryCodeChunksBackend, \
    TortoiseCodeChunksBackend
from test.conftest import _make_code_chunks_request

def _make_embedding(value: float = 1.0, dim: int = EMBED_DIM) -> list[float]:
    """Helper to generate a dense embedding of the correct dimension."""
    return [value] * dim

def one_hot(index: int, dim: int = EMBED_DIM) -> list[float]:
    """Unit vector e_i in R^dim."""
    v = [0.0] * dim
    v[index] = 1.0
    return v

def normalized_sum(indices: list[int], dim: int = EMBED_DIM) -> list[float]:
    """
    Unit vector proportional to sum of basis vectors: (e_i + e_j + ...)/sqrt(k).
    """
    v = [0.0] * dim
    for idx in indices:
        v[idx] += 1.0
    norm = math.sqrt(len(indices))
    return [x / norm for x in v]

class TestCodeChunksBackend:
    __test__ = False
    
    @pytest_asyncio.fixture
    async def repo(self) -> ICodeChunksStore:
        """
		Concrete subclasses must override this to return
		the appropriate repo instance (Mongo or Postgres).
		"""
        raise NotImplementedError
    
    # --------------------------------------------------
    # save
    # --------------------------------------------------
    async def test_save_persists_chunk_and_returns_correct_dto(self, repo: ICodeChunksStore):
        # Arrange
        emb = _make_embedding(0.5)
        req = _make_code_chunks_request(
            user_id="user-save",
            repo_id="repo-save-1",
            content="print('hello')",
            file_name="main.py",
            file_path="src/main.py",
            file_size=123,
            commit_number="commit-save-1",
            embedding=emb,
            metadata={"lang": "python"},
        )

        # Act
        saved = await repo.save(req)

        # Assert DTO basics
        assert isinstance(saved, CodeChunksResponseDTO)

        assert saved.id is not None
        assert isinstance(saved.id, uuid.UUID)

        assert isinstance(saved.user_id, str)
        assert saved.user_id == req.user_id

        assert isinstance(saved.repo_id, str)
        assert saved.repo_id == req.repo_id

        assert isinstance(saved.content, str)
        assert saved.content == req.content

        assert isinstance(saved.file_name, str)
        assert saved.file_name == req.file_name

        assert isinstance(saved.file_path, str)
        assert saved.file_path == req.file_path

        assert isinstance(saved.file_size, int)
        assert saved.file_size == req.file_size

        assert isinstance(saved.commit_number, str)
        assert saved.commit_number == req.commit_number

        # Embedding & metadata
        assert saved.embedding is not None
        assert isinstance(saved.embedding, list)
        assert len(saved.embedding) == EMBED_DIM

        assert isinstance(saved.metadata, dict)
        assert saved.metadata == req.metadata

        # Timestamps
        assert saved.created_at is not None
        assert isinstance(saved.created_at, datetime.datetime)

        assert saved.updated_at is not None
        assert isinstance(saved.updated_at, datetime.datetime)

        # Roundtrip via find_all_by_repo_id_with_limit
        fetched = await repo.find_all_by_repo_id_with_limit(
            repo_id=req.repo_id,
            limit=10,
        )

        assert isinstance(fetched, list)
        assert len(fetched) >= 1

        found = next((c for c in fetched if c.id == saved.id), None)
        assert found is not None
        assert isinstance(found, CodeChunksResponseDTO)

        assert found.user_id == saved.user_id
        assert found.repo_id == saved.repo_id
        assert found.file_name == saved.file_name
        assert found.file_path == saved.file_path
        assert found.file_size == saved.file_size
        assert found.commit_number == saved.commit_number
        assert found.content == saved.content

        assert isinstance(found.created_at, datetime.datetime)
        assert isinstance(found.updated_at, datetime.datetime)
    
    async def test_bulk_save_populates_timestamps(self, repo):
        # Arrange
        dtos = [
            _make_code_chunks_request(user_id="u1", repo_id="r1", file_name="f1.py"),
            _make_code_chunks_request(user_id="u1", repo_id="r1", file_name="f2.py"),
        ]
        
        # Act
        saved = await repo.bulk_save(dtos)
        
        # Assert
        assert len(saved) == 2
        for chunk in saved:
            assert isinstance(chunk.created_at, datetime.datetime)
            assert isinstance(chunk.updated_at, datetime.datetime)
            # sanity: created_at <= updated_at
            assert chunk.created_at <= chunk.updated_at
    
    # --------------------------------------------------
    # bulk_save
    # --------------------------------------------------
    async def test_bulk_save_persists_multiple_chunks_and_returns_dtos(
        self,
        repo: ICodeChunksStore,
    ):
        # Arrange
        emb1 = _make_embedding(0.1)
        emb2 = _make_embedding(0.2)

        req1 = _make_code_chunks_request(
            user_id="user-bulk",
            repo_id="repo-bulk",
            content="code 1",
            file_name="file1.py",
            file_path="src/file1.py",
            file_size=10,
            commit_number="commit-bulk-1",
            embedding=emb1,
            metadata={"idx": 1},
        )
        req2 = _make_code_chunks_request(
            user_id="user-bulk",
            repo_id="repo-bulk",
            content="code 2",
            file_name="file2.py",
            file_path="src/file2.py",
            file_size=20,
            commit_number="commit-bulk-2",
            embedding=emb2,
            metadata={"idx": 2},
        )

        # Act
        saved_list = await repo.bulk_save([req1, req2])

        # Assert
        assert isinstance(saved_list, list)
        assert len(saved_list) == 2

        for saved in saved_list:
            assert isinstance(saved, CodeChunksResponseDTO)
            assert isinstance(saved.id, uuid.UUID)
            assert isinstance(saved.user_id, str)
            assert isinstance(saved.repo_id, str)
            assert isinstance(saved.content, str)
            assert isinstance(saved.file_name, str)
            assert isinstance(saved.file_path, str)
            assert isinstance(saved.file_size, int)
            assert isinstance(saved.commit_number, str)
            assert isinstance(saved.created_at, datetime.datetime)
            assert isinstance(saved.updated_at, datetime.datetime)

            if saved.commit_number == "commit-bulk-1":
                assert saved.content == "code 1"
                assert saved.metadata == {"idx": 1}
            elif saved.commit_number == "commit-bulk-2":
                assert saved.content == "code 2"
                assert saved.metadata == {"idx": 2}

        # Confirm via find_all_by_repo_id_with_limit
        fetched = await repo.find_all_by_repo_id_with_limit("repo-bulk", limit=10)
        fetched_ids = {c.id for c in fetched}
        assert {s.id for s in saved_list}.issubset(fetched_ids)

    # --------------------------------------------------
    # find_all_by_repo_id_with_limit
    # --------------------------------------------------
    async def test_find_all_by_repo_id_with_limit_filters_by_repo_and_respects_limit(
        self,
        repo: ICodeChunksStore,
    ):
        # Arrange: 3 chunks for repo A, 1 chunk for repo B
        for i in range(3):
            await repo.save(
                _make_code_chunks_request(
                    user_id="user-repo",
                    repo_id="repo-A",
                    content=f"code A{i}",
                    file_name=f"a{i}.py",
                    file_path=f"src/a{i}.py",
                    file_size=100 + i,
                    commit_number=f"commit-A-{i}",
                    embedding=_make_embedding(0.3 + 0.01 * i),
                    metadata={"repo": "A", "idx": i},
                )
            )
        await repo.save(
            _make_code_chunks_request(
                user_id="user-repo",
                repo_id="repo-B",
                content="code B0",
                file_name="b0.py",
                file_path="src/b0.py",
                file_size=999,
                commit_number="commit-B-0",
                embedding=_make_embedding(0.9),
                metadata={"repo": "B", "idx": 0},
            )
        )

        # Act
        result = await repo.find_all_by_repo_id_with_limit(
            repo_id="repo-A",
            limit=2,
        )

        # Assert
        assert isinstance(result, list)
        # At most 2 because of limit
        assert 0 < len(result) <= 2

        for chunk in result:
            assert isinstance(chunk, CodeChunksResponseDTO)
            assert chunk.repo_id == "repo-A"
            assert isinstance(chunk.id, uuid.UUID)
            assert isinstance(chunk.user_id, str)
            assert isinstance(chunk.content, str)
            assert isinstance(chunk.file_name, str)
            assert isinstance(chunk.file_path, str)
            assert isinstance(chunk.file_size, int)
            assert isinstance(chunk.commit_number, str)
            assert isinstance(chunk.created_at, datetime.datetime)
            assert isinstance(chunk.updated_at, datetime.datetime)

        # Optional: you can check that no chunk from repo-B sneaks in
        repo_ids = {c.repo_id for c in result}
        assert repo_ids == {"repo-A"}

    # --------------------------------------------------
    # get_repo_file_chunks
    # --------------------------------------------------
    async def test_get_repo_file_chunks_filters_by_user_repo_and_filename(
        self,
        repo: ICodeChunksStore,
    ):
        # Arrange:
        # - 2 matching chunks: user1/repo1, file_name contains "readme"
        # - 1 same user/repo but different filename
        # - 1 other user/repo with "readme" (should be excluded)
        await repo.save(
            _make_code_chunks_request(
                user_id="user-file",
                repo_id="repo-file",
                content="readme 1 content",
                file_name="README.md",
                file_path="docs/README.md",
                file_size=10,
                commit_number="commit-f1",
                embedding=_make_embedding(0.1),
                metadata={},
            )
        )
        await repo.save(
            _make_code_chunks_request(
                user_id="user-file",
                repo_id="repo-file",
                content="readme 2 content",
                file_name="readme_extra.md",
                file_path="docs/readme_extra.md",
                file_size=20,
                commit_number="commit-f2",
                embedding=_make_embedding(0.2),
                metadata={},
            )
        )
        await repo.save(
            _make_code_chunks_request(
                user_id="user-file",
                repo_id="repo-file",
                content="other file content",
                file_name="main.py",
                file_path="src/main.py",
                file_size=30,
                commit_number="commit-f3",
                embedding=_make_embedding(0.3),
                metadata={},
            )
        )
        await repo.save(
            _make_code_chunks_request(
                user_id="other-user",
                repo_id="other-repo",
                content="foreign readme content",
                file_name="README.md",
                file_path="docs/README.md",
                file_size=40,
                commit_number="commit-f4",
                embedding=_make_embedding(0.4),
                metadata={},
            )
        )

        # Act
        result = await repo.get_repo_file_chunks(
            user_id="user-file",
            repo_id="repo-file",
            file_name="readme",
        )

        # Assert
        assert isinstance(result, list)
        assert len(result) == 2  # 2 matching, only content returned

        for item in result:
            assert isinstance(item, dict)
            # Both backends return only "content" key
            assert set(item.keys()) == {"content"}
            assert isinstance(item["content"], str)

        contents = {item["content"] for item in result}
        assert "readme 1 content" in contents
        assert "readme 2 content" in contents
        assert "other file content" not in contents
        assert "foreign readme content" not in contents

    # --------------------------------------------------
    # get_user_repo_chunks_multi
    # --------------------------------------------------
    async def test_get_user_repo_chunks_multi_returns_only_matching_user_and_repo(
        self,
        repo: ICodeChunksStore,
    ):
        # Arrange: 2 chunks for (userX, repoX), 1 for same user different repo,
        # 1 for different user.
        emb_good = _make_embedding(1.0)
        emb_other = _make_embedding(-0.5)

        # relevant
        saved1 = await repo.save(
            _make_code_chunks_request(
                user_id="user-multi",
                repo_id="repo-multi",
                content="multi code 1",
                file_name="m1.py",
                file_path="src/m1.py",
                file_size=10,
                commit_number="commit-m1",
                embedding=emb_good,
                metadata={},
            )
        )
        saved2 = await repo.save(
            _make_code_chunks_request(
                user_id="user-multi",
                repo_id="repo-multi",
                content="multi code 2",
                file_name="m2.py",
                file_path="src/m2.py",
                file_size=20,
                commit_number="commit-m2",
                embedding=emb_other,
                metadata={},
            )
        )

        # same user, different repo
        await repo.save(
            _make_code_chunks_request(
                user_id="user-multi",
                repo_id="repo-other",
                content="other repo code",
                file_name="o.py",
                file_path="src/o.py",
                file_size=30,
                commit_number="commit-o",
                embedding=_make_embedding(0.3),
                metadata={},
            )
        )

        # different user
        await repo.save(
            _make_code_chunks_request(
                user_id="other-user-multi",
                repo_id="repo-multi",
                content="other user code",
                file_name="ou.py",
                file_path="src/ou.py",
                file_size=40,
                commit_number="commit-ou",
                embedding=_make_embedding(0.4),
                metadata={},
            )
        )

        query_embeddings = [emb_good]

        # Act
        results = await repo.get_user_repo_chunks_multi(
            user_id="user-multi",
            repo_id="repo-multi",
            query_embeddings=query_embeddings,
            emb_dim=EMBED_DIM,
            limit=10,
        )

        # Assert
        assert isinstance(results, list)
        assert 0 < len(results) <= 2  # only 2 relevant chunks exist

        # All ids must belong to the two relevant saved chunks
        allowed_ids = {saved1.id, saved2.id}
        result_ids = set()

        for row in results:
            assert isinstance(row, dict)
            assert "id" in row
            assert "file_name" in row
            assert "file_path" in row
            assert "content" in row
            assert "created_at" in row
            assert "fusion_score" in row
            assert "max_sim" in row

            # Normalize id to UUID for comparison
            rid = row["id"]
            if isinstance(rid, uuid.UUID):
                rid_uuid = rid
            else:
                rid_uuid = uuid.UUID(str(rid))

            result_ids.add(rid_uuid)

            assert isinstance(row["file_name"], str)
            assert isinstance(row["file_path"], str)
            assert isinstance(row["content"], str)
            assert isinstance(row["created_at"], datetime.datetime)
            assert isinstance(row["fusion_score"], float)
            assert isinstance(row["max_sim"], float)

        # Ensure we didn't get any chunk from other user/repo
        assert result_ids.issubset(allowed_ids)
    
    async def test_get_user_repo_chunks_multi_single_query_orders_by_similarity(
        self,
        repo: ICodeChunksStore,
    ):
        """
        For a single query embedding q = e0:
          - chunk_best = e0          -> sim = 1
          - chunk_mid  = (e0+e1)/√2  -> sim = ~0.707
          - chunk_worst= e1          -> sim = 0

        We expect:
          best first, worst last, regardless of insertion order.
        """
        user_id = "user-math-single"
        repo_id = "repo-math-single"

        emb_best = one_hot(0)
        emb_mid = normalized_sum([0, 1])
        emb_worst = one_hot(1)

        # Insert in a shuffled order to ensure ranking isn't by insertion
        saved_mid = await repo.save(
            _make_code_chunks_request(
                user_id=user_id,
                repo_id=repo_id,
                content="mid similarity",
                file_name="mid.py",
                file_path="src/mid.py",
                file_size=10,
                commit_number="commit-mid",
                embedding=emb_mid,
                metadata={},
            )
        )
        saved_worst = await repo.save(
            _make_code_chunks_request(
                user_id=user_id,
                repo_id=repo_id,
                content="worst similarity",
                file_name="worst.py",
                file_path="src/worst.py",
                file_size=10,
                commit_number="commit-worst",
                embedding=emb_worst,
                metadata={},
            )
        )
        saved_best = await repo.save(
            _make_code_chunks_request(
                user_id=user_id,
                repo_id=repo_id,
                content="best similarity",
                file_name="best.py",
                file_path="src/best.py",
                file_size=10,
                commit_number="commit-best",
                embedding=emb_best,
                metadata={},
            )
        )

        query_embeddings = [one_hot(0)]

        # Act
        results = await repo.get_user_repo_chunks_multi(
            user_id=user_id,
            repo_id=repo_id,
            query_embeddings=query_embeddings,
            emb_dim=EMBED_DIM,
            limit=10,
        )

        # Assert
        assert len(results) == 3

        ids_in_order = [uuid.UUID(str(r["id"])) for r in results]

        # best first, worst last
        assert ids_in_order[0] == saved_best.id
        assert ids_in_order[-1] == saved_worst.id

        # mid is somewhere in the middle
        assert set(ids_in_order) == {saved_best.id, saved_mid.id, saved_worst.id}
    
    async def test_get_user_repo_chunks_multi_multi_query_favors_chunks_close_to_all_queries(
        self,
        repo: ICodeChunksStore,
    ):
        """
        Queries: q1 = e0, q2 = e1
        Chunks:
          center  = (e0+e1)/√2  -> sims ~ [0.707, 0.707], fusion ~ 1.414
          only_e0 = e0          -> sims [1, 0], fusion = 1
          only_e1 = e1          -> sims [0, 1], fusion = 1

        We expect 'center' to be ranked FIRST.
        """
        user_id = "user-math-multi"
        repo_id = "repo-math-multi"

        emb_center = normalized_sum([0, 1])
        emb_e0 = one_hot(0)
        emb_e1 = one_hot(1)

        saved_center = await repo.save(
            _make_code_chunks_request(
                user_id=user_id,
                repo_id=repo_id,
                content="center chunk",
                file_name="center.py",
                file_path="src/center.py",
                file_size=10,
                commit_number="commit-center",
                embedding=emb_center,
                metadata={},
            )
        )
        saved_e0 = await repo.save(
            _make_code_chunks_request(
                user_id=user_id,
                repo_id=repo_id,
                content="only e0",
                file_name="e0.py",
                file_path="src/e0.py",
                file_size=10,
                commit_number="commit-e0",
                embedding=emb_e0,
                metadata={},
            )
        )
        saved_e1 = await repo.save(
            _make_code_chunks_request(
                user_id=user_id,
                repo_id=repo_id,
                content="only e1",
                file_name="e1.py",
                file_path="src/e1.py",
                file_size=10,
                commit_number="commit-e1",
                embedding=emb_e1,
                metadata={},
            )
        )

        query_embeddings = [one_hot(0), one_hot(1)]

        # Act
        results = await repo.get_user_repo_chunks_multi(
            user_id=user_id,
            repo_id=repo_id,
            query_embeddings=query_embeddings,
            emb_dim=EMBED_DIM,
            limit=10,
        )

        # Assert
        assert len(results) == 3

        ids_in_order = [uuid.UUID(str(r["id"])) for r in results]

        # center must come first (highest fusion_score)
        assert ids_in_order[0] == saved_center.id

        # All three must be present
        assert set(ids_in_order) == {saved_center.id, saved_e0.id, saved_e1.id}

        # And fusion_score / max_sim are floats
        for row in results:
            assert isinstance(row["fusion_score"], float)
            assert isinstance(row["max_sim"], float)

@pytest.mark.asyncio
class TestTortoiseCodeChunksBackend(TestCodeChunksBackend):
    __test__ = True
    
    @pytest_asyncio.fixture
    async def repo(self, postgresql_client):
        return TortoiseCodeChunksBackend()

@pytest.mark.asyncio
class TestBeanieCodeChunksBackend(TestCodeChunksBackend):
    __test__ = True
    
    @pytest_asyncio.fixture
    async def repo(self, db_client):
        return BeanieCodeChunksBackend()

@pytest.mark.asyncio
class TestInMemoryCodeChunksBackend(TestCodeChunksBackend):
    __test__ = True
    
    @pytest_asyncio.fixture
    async def repo(self):
        return InMemoryCodeChunksBackend()