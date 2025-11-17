import datetime
import uuid

import pytest

from models_src.dto.code_chunks import CodeChunksResponseDTO
from models_src.exceptions.exception_constants import EMBEDDINGS_INVALID_SIZE
from models_src.repositories.code_chunks import BeanieCodeChunksBackend
from test.conftest import _make_code_chunks_request


@pytest.mark.asyncio
class TestBeanieCodeChunksBackend:
    beanie_store = BeanieCodeChunksBackend

    async def test_save_persists_and_maps_to_dto(self, db_client):
        # Arrange
        req = _make_code_chunks_request(
            user_id="beanie-user-save",
            repo_id="repo-save",
            content="chunk content",
            file_name="readme.md",
            file_path="/readme.md",
            file_size=42,
            commit_number="commit-1",
        )

        # Act
        saved = await self.beanie_store().save(req)

        # Assert
        assert isinstance(saved, CodeChunksResponseDTO)
        assert saved.id is not None
        assert isinstance(saved.id, uuid.UUID)

        assert saved.user_id == req.user_id
        assert saved.repo_id == req.repo_id
        assert saved.content == req.content
        assert saved.file_name == req.file_name
        assert saved.file_path == req.file_path
        assert saved.file_size == req.file_size
        assert saved.commit_number == req.commit_number

        assert isinstance(saved.created_at, datetime.datetime)

        # And we can see it via repo query
        results = await self.beanie_store().find_all_by_repo_id_with_limit(
            repo_id="repo-save", limit=10
        )
        assert len(results) == 1
        assert results[0].id == saved.id

    async def test_bulk_save_inserts_many(self, db_client):
        # Arrange
        repo_id = "repo-bulk"
        reqs = [
            _make_code_chunks_request(
                user_id="bulk-user",
                repo_id=repo_id,
                content=f"content-{i}",
                file_name=f"file-{i}.py",
                file_path=f"/src/file-{i}.py",
                file_size=100 + i,
                commit_number=f"commit-{i}",
            )
            for i in range(3)
        ]

        # Act
        saved_list = await self.beanie_store().bulk_save(reqs)

        # Assert
        assert len(saved_list) == 3
        assert all(isinstance(x, CodeChunksResponseDTO) for x in saved_list)
        assert all(isinstance(x.id, uuid.UUID) for x in saved_list)

        # Confirm via repo query
        results = await self.beanie_store().find_all_by_repo_id_with_limit(
            repo_id=repo_id, limit=10
        )
        assert len(results) == 3
        saved_ids = {s.id for s in saved_list}
        result_ids = {r.id for r in results}
        assert saved_ids == result_ids

    async def test_find_all_by_repo_id_with_limit_orders_newest_first(self, db_client):
        repo_id = "repo-order"

        saved1 = await self.beanie_store().save(
            _make_code_chunks_request(
                user_id="user-order",
                repo_id=repo_id,
                content="older",
                file_name="file1.py",
                file_path="/file1.py",
                file_size=10,
                commit_number="c1",
            )
        )
        saved2 = await self.beanie_store().save(
            _make_code_chunks_request(
                user_id="user-order",
                repo_id=repo_id,
                content="newer",
                file_name="file2.py",
                file_path="/file2.py",
                file_size=20,
                commit_number="c2",
            )
        )

        # Act: limit 1, newest only
        results = await self.beanie_store().find_all_by_repo_id_with_limit(
            repo_id=repo_id, limit=1
        )

        # Assert
        assert len(results) == 1
        assert results[0].id == saved2.id  # newest first

        # Act: limit 2, both
        results_all = await self.beanie_store().find_all_by_repo_id_with_limit(
            repo_id=repo_id, limit=2
        )
        assert len(results_all) == 2
        ids = [r.id for r in results_all]
        assert ids == [saved2.id, saved1.id]

    async def test_embedding_length_validation_on_save_raises_value_error(self, db_client):
        # Arrange: invalid embedding length (2 instead of 768)
        bad_embedding = [0.1, 0.2]

        req = _make_code_chunks_request(
            user_id="user-embed-bad",
            repo_id="repo-embed-bad",
            content="some code",
            file_name="file.py",
            file_path="/file.py",
            file_size=10,
            commit_number="c-embed-bad",
            embedding=bad_embedding,
        )

        # Act / Assert
        with pytest.raises(ValueError) as exc_info:
            await self.beanie_store().save(req)

        msg = str(exc_info.value)
        # The validator formats EMBEDDINGS_INVALID_SIZE with actual lengths
        assert "embedding must have length" in msg
        assert "got 2" in msg
        # Optional: check base template string is present
        assert "embedding must have length" in EMBEDDINGS_INVALID_SIZE

    async def test_get_repo_file_chunks_filters_by_user_repo_and_filename(self, db_client):
        store = self.beanie_store()
        user_id = "user-readme"
        repo_id = "repo-readme"

        # Matching user & repo, readme variations
        await store.save(
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
        await store.save(
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
        # Different file name -> should not match
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
        # Different user -> should not match
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

        # Act
        results = await store.get_repo_file_chunks(
            user_id=user_id,
            repo_id=repo_id,
            file_name="readme",
        )

        # Assert: only 2 readme-ish for that user+repo
        assert len(results) == 2
        contents = {r["content"] for r in results}
        assert contents == {"READ ME 1", "READ ME 2"}
        # Only "content" key is present in projections
        assert all(list(r.keys()) == ["content"] for r in results)

    async def test_get_user_repo_chunks_multi_returns_ranked_results(self, db_client):
        store = self.beanie_store()
        user_id = "user-multi"
        repo_id = "repo-multi"

        EMBED_DIM = 768
        emb1 = [1.0] * EMBED_DIM

        # Two chunks with same embedding
        saved1 = await store.save(
            _make_code_chunks_request(
                user_id=user_id,
                repo_id=repo_id,
                content="chunk-1",
                file_name="file1.py",
                file_path="/file1.py",
                file_size=10,
                commit_number="c1",
                embedding=emb1,
            )
        )
        saved2 = await store.save(
            _make_code_chunks_request(
                user_id=user_id,
                repo_id=repo_id,
                content="chunk-2",
                file_name="file2.py",
                file_path="/file2.py",
                file_size=20,
                commit_number="c2",
                embedding=emb1,
            )
        )

        query_embeddings = [emb1]  # single query
        results = await store.get_user_repo_chunks_multi(
            user_id=user_id,
            repo_id=repo_id,
            query_embeddings=query_embeddings,
            emb_dim=EMBED_DIM,
            limit=10,
        )

        assert len(results) == 2
        ids = {r["id"] for r in results}
        assert ids == {saved1.id, saved2.id}

        # Each result has the expected keys
        for r in results:
            assert "fusion_score" in r
            assert "max_sim" in r
            assert "content" in r
            assert "file_name" in r
            assert "file_path" in r
            assert "created_at" in r
