import datetime
import uuid

import pytest
from beanie.exceptions import DocumentNotFound

from models_src.dto.repo import RepoResponseDTO
from models_src.models.common.repo_enums import StatusTypes
from models_src.repositories.repo import BeanieRepoBackend
from models_src.exceptions.base_exceptions import DevDoxModelsException
from models_src.exceptions.utils import RepoErrors
from test.conftest import _make_repo_request


@pytest.mark.asyncio
class TestBeanieRepoBackend:
    beanie_store = BeanieRepoBackend

    async def test_save_and_get_by_id(self, db_client):
        store = self.beanie_store()

        req = _make_repo_request(
            user_id="beanie-user-1",
            repo_id="beanie-repo-1",
            repo_name="beanie-repo",
            html_url="https://github.com/u/beanie-repo",
            repo_alias_name="alias-1",
        )

        saved = await store.save(req)

        assert isinstance(saved, RepoResponseDTO)
        assert isinstance(saved.id, uuid.UUID)
        assert saved.user_id == req.user_id
        assert saved.repo_id == req.repo_id
        assert saved.repo_name == req.repo_name
        assert saved.html_url == req.html_url
        assert saved.repo_alias_name == req.repo_alias_name
        assert isinstance(saved.created_at, datetime.datetime)

        fetched = await store.get_by_id(str(saved.id))
        assert fetched is not None
        assert fetched.id == saved.id
    
    async def test_get_by_id_not_found_returns_exception(self, db_client):
        store = self.beanie_store()
        
        with pytest.raises(DocumentNotFound):
            await store.get_by_id("b0908783-6b99-45ca-8d2b-acb369945374")
    
    async def test_find_by_repo_id_and_user_id_and_html_url(self, db_client):
        store = self.beanie_store()
        user_id = "beanie-user-2"

        saved = await store.save(
            _make_repo_request(
                user_id=user_id,
                repo_id="gid-123",
                repo_name="test-repo",
                html_url="https://gitlab.com/u/test-repo",
                repo_alias_name="alias-2",
            )
        )

        by_repo_id = await store.find_by_repo_id("gid-123")
        assert by_repo_id is not None
        assert by_repo_id.id == saved.id

        by_repo_and_user = await store.find_by_repo_id_user_id("gid-123", user_id)
        assert by_repo_and_user is not None
        assert by_repo_and_user.id == saved.id

        by_user_and_html = await store.find_by_user_id_and_html_url(
            user_id=user_id,
            html_url="https://gitlab.com/u/test-repo",
        )
        assert by_user_and_html is not None
        assert by_user_and_html.id == saved.id

    async def test_find_by_id_returns_none_when_not_found(self, db_client):
        store = self.beanie_store()

        result = await store.find_by_id(str(uuid.uuid4()))
        assert result is None

    async def test_find_all_by_user_id_and_count_pagination(self, db_client):
        store = self.beanie_store()
        user_id = "beanie-user-3"

        saved1 = await store.save(
            _make_repo_request(
                user_id=user_id,
                repo_id="repo-1",
                repo_name="repo-1",
                html_url="https://g.com/r1",
                repo_alias_name="alias-r1",
            )
        )
        saved2 = await store.save(
            _make_repo_request(
                user_id=user_id,
                repo_id="repo-2",
                repo_name="repo-2",
                html_url="https://g.com/r2",
                repo_alias_name="alias-r2",
            )
        )
        saved3 = await store.save(
            _make_repo_request(
                user_id=user_id,
                repo_id="repo-3",
                repo_name="repo-3",
                html_url="https://g.com/r3",
                repo_alias_name="alias-r3",
            )
        )
        # other user
        await store.save(
            _make_repo_request(
                user_id="other-user",
                repo_id="other",
                repo_name="other",
                html_url="https://g.com/other",
                repo_alias_name="alias-other",
            )
        )

        total = await store.count_by_user_id(user_id=user_id)
        assert total == 3

        page0 = await store.find_all_by_user_id(user_id=user_id, offset=0, limit=2)
        page1 = await store.find_all_by_user_id(user_id=user_id, offset=1, limit=2)

        assert len(page0) == 2
        assert len(page1) == 1

        ids = {r.id for r in page0 + page1}
        assert ids == {saved1.id, saved2.id, saved3.id}

    async def test_update_analysis_metadata_by_id_updates_fields(self, db_client):
        store = self.beanie_store()
        user_id = "beanie-user-4"

        saved = await store.save(
            _make_repo_request(
                user_id=user_id,
                repo_id="repo-meta",
                repo_name="repo-meta",
                html_url="https://g.com/meta",
                repo_alias_name="alias-meta",
                status=StatusTypes.IN_PROGRESS,
            )
        )

        end_time = datetime.datetime.now(datetime.timezone.utc)
        updated = await store.update_analysis_metadata_by_id(
            id=str(saved.id),
            status=StatusTypes.COMPLETED,
            processing_end_time=end_time,
            total_files=10,
            total_chunks=20,
            total_embeddings=30,
        )
        assert updated == 1

        refreshed = await store.find_by_id(str(saved.id))
        assert refreshed is not None
        assert refreshed.status == StatusTypes.COMPLETED
        assert refreshed.processing_end_time.date() == end_time.date()
        assert refreshed.total_files == 10
        assert refreshed.total_chunks == 20
        assert refreshed.total_embeddings == 30

    async def test_update_repo_system_reference_by_id(self, db_client):
        store = self.beanie_store()
        user_id = "beanie-user-5"

        saved = await store.save(
            _make_repo_request(
                user_id=user_id,
                repo_id="repo-ref",
                repo_name="repo-ref",
                html_url="https://g.com/ref",
                repo_alias_name="alias-ref",
            )
        )

        updated = await store.update_repo_system_reference_by_id(
            id=str(saved.id),
            repo_system_reference="sys-ref-123",
        )
        assert updated == 1

        refreshed = await store.find_by_id(str(saved.id))
        assert refreshed is not None
        assert refreshed.repo_system_reference == "sys-ref-123"

    async def test_find_by_user_and_path_and_alias(self, db_client):
        store = self.beanie_store()
        user_id = "beanie-user-6"

        saved = await store.save(
            _make_repo_request(
                user_id=user_id,
                repo_id="repo-path",
                repo_name="repo-path",
                html_url="https://g.com/path",
                repo_alias_name="alias-path",
                visibility="public",
            )
        )
        # manually update relative_path + alias via model to simulate extra fields
        await store.model.find(store.model.id == saved.id).update(
            {"$set": {"relative_path": "/u/repo-path", "repo_alias_name": "my-alias"}}
        )

        by_path = await store.find_by_user_and_path(user_id=user_id, relative_path="/u/repo-path")
        assert by_path is not None
        assert by_path.id == saved.id

        by_alias = await store.find_by_user_and_alias_name(user_id=user_id, repo_alias_name="my-alias")
        assert by_alias is not None
        assert by_alias.id == saved.id

    async def test_save_context_updates_status_to_pending(self, db_client):
        store = self.beanie_store()
        user_id = "beanie-user-7"
        repo_id = "repo-context"

        saved = await store.save(
            _make_repo_request(
                user_id=user_id,
                repo_id=repo_id,
                repo_name="repo-context",
                html_url="https://g.com/context",
                repo_alias_name="alias-context",
                status=StatusTypes.COMPLETED,
            )
        )

        updated = await store.save_context(
            repo_id=repo_id,
            user_id=user_id,
            config={"dummy": True},
        )

        assert isinstance(updated, RepoResponseDTO)
        assert updated.id == saved.id
        assert updated.status == StatusTypes.PENDING

    async def test_save_context_missing_repo_raises_internal_error(self, db_client):
        store = self.beanie_store()

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.save_context(
                repo_id="non-existing",
                user_id="user-x",
                config={},
            )

        exc = exc_info.value
        err = RepoErrors.REPOSITORY_DOESNT_EXIST.value
        assert exc.error_type == err["error_type"]
        assert exc.user_message == err["log_message"]
        assert exc.log_message == err["log_message"]
