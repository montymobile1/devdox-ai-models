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

    async def test_get_user_repo_chunks_multi_inconsistent_embedding_dims_returns_empty(
        self,
    ):
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