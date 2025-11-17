import datetime
import uuid
from time import sleep

import pytest

from models_src.dto.code_chunks import CodeChunksResponseDTO
from models_src.repositories.code_chunks import (
    InMemoryCodeChunksBackend, CodeChunksStore
)
from test.conftest import _make_code_chunks_request


@pytest.mark.asyncio
class TestInMemoryCodeChunksBackend:
    inmemory_store = InMemoryCodeChunksBackend

    async def test_save_and_basic_fields(self):
        store = self.inmemory_store()

        req = _make_code_chunks_request(
            user_id="mem-user-save",
            repo_id="mem-repo-save",
            content="chunk content",
            file_name="file.py",
            file_path="/file.py",
            file_size=10,
            commit_number="c1",
        )

        saved = await store.save(req)

        assert isinstance(saved, CodeChunksResponseDTO)
        assert saved.id is not None
        assert isinstance(saved.id, uuid.UUID)
        assert saved.user_id == req.user_id
        assert saved.repo_id == req.repo_id
        assert saved.content == req.content
        assert isinstance(saved.created_at, datetime.datetime)

    async def test_bulk_save_appends_and_sets_created_at(self):
        store = self.inmemory_store()

        reqs = [
            _make_code_chunks_request(
                user_id="bulk-user",
                repo_id="bulk-repo",
                content=f"content-{i}",
                file_name=f"file-{i}.py",
                file_path=f"/file-{i}.py",
                file_size=100 + i,
                commit_number=f"c{i}",
            )
            for i in range(3)
        ]

        saved_list = await store.bulk_save(reqs)

        assert len(saved_list) == 3
        assert all(isinstance(x.id, uuid.UUID) for x in saved_list)
        assert all(isinstance(x.created_at, datetime.datetime) for x in saved_list)
        assert store.total_count == 3

    async def test_find_all_by_repo_id_with_limit_filters_and_limits(self):
        store = self.inmemory_store()

        repo_id = "repo-find"
        # 3 for target repo
        for i in range(3):
            await store.save(
                _make_code_chunks_request(
                    user_id="user",
                    repo_id=repo_id,
                    content=f"content-{i}",
                    file_name=f"f{i}.py",
                    file_path=f"/f{i}.py",
                    file_size=10,
                    commit_number=f"c{i}",
                )
            )

        # 1 for different repo
        await store.save(
            _make_code_chunks_request(
                user_id="user",
                repo_id="other-repo",
                content="other",
                file_name="other.py",
                file_path="/other.py",
                file_size=10,
                commit_number="cX",
            )
        )

        # Act: limit 2
        results = await store.find_all_by_repo_id_with_limit(repo_id=repo_id, limit=2)

        assert len(results) == 2
        assert all(r.repo_id == repo_id for r in results)

    async def test_get_repo_file_chunks_filters_and_sorts(self):
        store = self.inmemory_store()
        user_id = "user-readme"
        repo_id = "repo-readme"
        
        # Insert in order so created_at grows
        first = await store.save(
            _make_code_chunks_request(
                user_id=user_id,
                repo_id=repo_id,
                content="READ ME 1",
                file_name="README.md",
                file_path="/README.md",
                file_size=1,
                commit_number="c1",
            )
        )
        
        sleep(5)
        
        second = await store.save(
            _make_code_chunks_request(
                user_id=user_id,
                repo_id=repo_id,
                content="READ ME 2",
                file_name="readme_extra.md",
                file_path="/readme_extra.md",
                file_size=1,
                commit_number="c2",
            )
        )
        # Other file names / users
        await store.save(
            _make_code_chunks_request(
                user_id=user_id,
                repo_id=repo_id,
                content="other file",
                file_name="other.md",
                file_path="/other.md",
                file_size=1,
                commit_number="c3",
            )
        )
        await store.save(
            _make_code_chunks_request(
                user_id="other-user",
                repo_id=repo_id,
                content="other user readme",
                file_name="readme.md",
                file_path="/readme.md",
                file_size=1,
                commit_number="c4",
            )
        )

        results = await store.get_repo_file_chunks(
            user_id=user_id,
            repo_id=repo_id,
            file_name="readme",
        )

        assert len(results) == 2
        
        contents = [r["content"] for r in results]
        # Sorted by created_at desc -> second, then first
        assert contents == ["READ ME 2", "READ ME 1"]

    async def test_get_user_repo_chunks_multi_ranks_by_cosine_similarity(self):
        store = self.inmemory_store()
        user_id = "user-cos"
        repo_id = "repo-cos"

        # Embeddings in R^3 to make reasoning easy
        emb_best = [1.0, 0.0, 0.0]
        emb_worse = [0.0, 1.0, 0.0]

        saved_best = await store.save(
            _make_code_chunks_request(
                user_id=user_id,
                repo_id=repo_id,
                content="best match",
                file_name="best.py",
                file_path="/best.py",
                file_size=1,
                commit_number="c1",
                embedding=emb_best,
            )
        )
        saved_worse = await store.save(
            _make_code_chunks_request(
                user_id=user_id,
                repo_id=repo_id,
                content="worse match",
                file_name="worse.py",
                file_path="/worse.py",
                file_size=1,
                commit_number="c2",
                embedding=emb_worse,
            )
        )

        query_embeddings = [[1.0, 0.0, 0.0]]

        results = await store.get_user_repo_chunks_multi(
            user_id=user_id,
            repo_id=repo_id,
            query_embeddings=query_embeddings,
            emb_dim=3,
            limit=10,
        )

        assert len(results) == 2
        # First result should be the one aligned with the query
        assert results[0]["id"] == saved_best.id
        assert results[1]["id"] == saved_worse.id
        assert results[0]["fusion_score"] >= results[1]["fusion_score"]

@pytest.mark.asyncio
class TestCodeChunksStoreValidation:
    code_chunks_store = CodeChunksStore

    async def test_bulk_save_empty_list_returns_empty_and_skips_backend(self):
        store = self.code_chunks_store(storage_backend=None)

        result = await store.bulk_save(create_model=[])
        assert result == []

    @pytest.mark.parametrize(
        "repo_id, limit",
        [
            (None, 10),
            ("", 10),
            (" ", 10),
            ("\t", 10),
            ("valid-repo", 0),
            ("valid-repo", -1),
        ],
    )
    async def test_find_all_by_repo_id_with_limit_invalid_args_return_empty(
        self,
        repo_id,
        limit,
    ):
        store = self.code_chunks_store(storage_backend=None)

        result = await store.find_all_by_repo_id_with_limit(
            repo_id=repo_id,
            limit=limit,
        )
        assert result == []

    async def test_get_repo_file_chunks_backend_failure_returns_empty_list(self):
        """
        With storage_backend=None, any attribute access raises AttributeError,
        which should be caught and translated into [].
        """
        store = self.code_chunks_store(storage_backend=None)

        result = await store.get_repo_file_chunks(
            user_id="user",
            repo_id="repo",
            file_name="readme",
        )
        assert result == []

    @pytest.mark.parametrize(
        "user_id, repo_id, query_embeddings, limit",
        [
            # Empty query embeddings
            ("user", "repo", [], 10),
            # Blank user_id
            (None, "repo", [[0.1, 0.2]], 10),
            ("", "repo", [[0.1, 0.2]], 10),
            (" ", "repo", [[0.1, 0.2]], 10),
            ("\t", "repo", [[0.1, 0.2]], 10),
            # Blank repo_id
            ("user", None, [[0.1, 0.2]], 10),
            ("user", "", [[0.1, 0.2]], 10),
            ("user", " ", [[0.1, 0.2]], 10),
            ("user", "\t", [[0.1, 0.2]], 10),
            # Non-positive limit
            ("user", "repo", [[0.1, 0.2]], 0),
            ("user", "repo", [[0.1, 0.2]], -1),
        ],
    )
    async def test_get_user_repo_chunks_multi_invalid_args_return_empty(
        self,
        user_id,
        repo_id,
        query_embeddings,
        limit,
    ):
        store = self.code_chunks_store(storage_backend=None)

        result = await store.get_user_repo_chunks_multi(
            user_id=user_id,
            repo_id=repo_id,
            query_embeddings=query_embeddings,
            emb_dim=2,
            limit=limit,
        )
        assert result == []

    async def test_get_user_repo_chunks_multi_inconsistent_embedding_dims_returns_empty(self):
        store = self.code_chunks_store(storage_backend=None)

        user_id = "user-valid"
        repo_id = "repo-valid"
        # One has dim 2, the other dim 1 -> inconsistent
        query_embeddings = [
            [0.1, 0.2],
            [0.3],
        ]

        result = await store.get_user_repo_chunks_multi(
            user_id=user_id,
            repo_id=repo_id,
            query_embeddings=query_embeddings,
            emb_dim=2,
            limit=10,
        )
        assert result == []