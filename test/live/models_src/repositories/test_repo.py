import datetime
import uuid

import pytest
import pytest_asyncio
from pymongo.errors import DuplicateKeyError
from tortoise.exceptions import IntegrityError

from models_src.dto.repo import RepoResponseDTO
from models_src.models.common.repo_enums import StatusTypes
from models_src.repositories.repo import BeanieRepoBackend, InMemoryRepoBackend, IRepoStore, TortoiseRepoBackend
from models_src.exceptions.base_exceptions import DevDoxModelsException
from models_src.exceptions.utils import RepoErrors
from test.conftest import _make_repo_request

# All backends should raise one of these when the unique (user_id, repo_id)
# invariant is violated.
UNIQUE_EXCEPTIONS = (DuplicateKeyError, IntegrityError)

class TestRepoBackend:
    __test__ = False
    
    @pytest_asyncio.fixture
    async def repo(self) -> IRepoStore:
        raise NotImplementedError
    
    # =================================================================
    # save()
    # =================================================================

    async def test_save_should_persist_repo_and_return_dto(self, repo: IRepoStore):
        """Saving a repo should persist it and return a fully-populated DTO."""
        req = _make_repo_request()

        result = await repo.save(req)

        assert isinstance(result, RepoResponseDTO)
        assert isinstance(result.id, uuid.UUID)
        assert result.user_id == req.user_id
        assert result.repo_id == req.repo_id
        assert result.repo_name == req.repo_name
        assert result.html_url == req.html_url
        assert result.repo_alias_name == req.repo_alias_name

        # Timestamps should be set by the backend (DB or in-memory)
        assert isinstance(result.created_at, datetime.datetime)
        assert isinstance(result.updated_at, datetime.datetime)

    async def test_save_should_enforce_unique_user_id_and_repo_id(
        self, repo: IRepoStore
    ):
        """
        Saving two repos with the same (user_id, repo_id) should raise a uniqueness-related exception.
        """
        first = _make_repo_request(user_id="user-1", repo_id="repo-same")
        await repo.save(first)

        second = _make_repo_request(user_id="user-1", repo_id="repo-same")

        with pytest.raises(UNIQUE_EXCEPTIONS):
            await repo.save(second)

    # =================================================================
    # find_by_repo_id / find_by_repo_id_user_id / find_by_id
    # =================================================================

    async def test_find_by_repo_id_should_return_repo_for_existing_repo_id(
        self, repo: IRepoStore
    ):
        req = _make_repo_request(repo_id="repo-123")
        saved = await repo.save(req)

        found = await repo.find_by_repo_id("repo-123")

        assert found is not None
        assert isinstance(found, RepoResponseDTO)
        assert found.id == saved.id
        assert found.repo_id == "repo-123"

    async def test_find_by_repo_id_should_return_none_for_unknown_repo_id(
        self, repo: IRepoStore
    ):
        found = await repo.find_by_repo_id("non-existent-repo")
        assert found is None

    async def test_find_by_repo_id_user_id_should_return_repo_for_existing_pair(
        self, repo: IRepoStore
    ):
        req = _make_repo_request(user_id="user-x", repo_id="repo-x")
        saved = await repo.save(req)

        found = await repo.find_by_repo_id_user_id(
            repo_id="repo-x", user_id="user-x"
        )

        assert found is not None
        assert found.id == saved.id
        assert found.repo_id == "repo-x"
        assert found.user_id == "user-x"

    async def test_find_by_repo_id_user_id_should_return_none_for_unknown_pair(
        self, repo: IRepoStore
    ):
        req = _make_repo_request(user_id="user-y", repo_id="repo-y")
        await repo.save(req)

        # wrong user
        not_found = await repo.find_by_repo_id_user_id(
            repo_id="repo-y", user_id="other-user"
        )
        assert not_found is None

    async def test_find_by_id_should_return_repo_for_existing_id(
        self, repo: IRepoStore
    ):
        req = _make_repo_request()
        saved = await repo.save(req)

        found = await repo.find_by_id(str(saved.id))

        assert found is not None
        assert isinstance(found, RepoResponseDTO)
        assert found.id == saved.id

    async def test_find_by_id_should_return_none_for_unknown_id(
        self, repo: IRepoStore
    ):
        random_id = str(uuid.uuid4())
        found = await repo.find_by_id(random_id)
        assert found is None

    # =================================================================
    # find_by_user_id_and_html_url
    # =================================================================

    async def test_find_by_user_id_and_html_url_should_return_repo_when_exists(
        self, repo: IRepoStore
    ):
        req = _make_repo_request(
            user_id="user-html", html_url="https://example.com/repo-html"
        )
        saved = await repo.save(req)

        found = await repo.find_by_user_id_and_html_url(
            user_id="user-html",
            html_url="https://example.com/repo-html",
        )

        assert found is not None
        assert found.id == saved.id
        assert found.html_url == "https://example.com/repo-html"

    async def test_find_by_user_id_and_html_url_should_return_none_when_not_found(
        self, repo: IRepoStore
    ):
        req = _make_repo_request(
            user_id="user-html-2", html_url="https://example.com/repo-2"
        )
        await repo.save(req)

        found = await repo.find_by_user_id_and_html_url(
            user_id="user-html-2",
            html_url="https://example.com/other",
        )

        assert found is None

    # =================================================================
    # find_all_by_user_id + count_by_user_id
    # =================================================================

    async def test_find_all_by_user_id_should_return_paginated_sorted_by_created_at_desc(
        self, repo: IRepoStore
    ):
        user_id = "user-paging"

        # Create 3 repos for the same user; they should be ordered by created_at desc
        req1 = _make_repo_request(user_id=user_id, repo_id="r1")
        req2 = _make_repo_request(user_id=user_id, repo_id="r2")
        req3 = _make_repo_request(user_id=user_id, repo_id="r3")

        await repo.save(req1)
        await repo.save(req2)
        await repo.save(req3)

        page0 = await repo.find_all_by_user_id(user_id=user_id, offset=0, limit=2)
        assert len(page0) == 2
        # Newest first: r3, then r2
        repo_ids_page0 = [r.repo_id for r in page0]
        assert repo_ids_page0 == ["r3", "r2"]

        page1 = await repo.find_all_by_user_id(user_id=user_id, offset=1, limit=2)
        # Should contain the remaining one (r1) or be empty if only 3 total
        repo_ids_page1 = [r.repo_id for r in page1]
        assert repo_ids_page1 == ["r1"]

    async def test_count_by_user_id_should_return_number_of_repos_for_user(
        self, repo: IRepoStore
    ):
        user1 = "user-count-1"
        user2 = "user-count-2"

        # user1: 2 repos
        await repo.save(_make_repo_request(user_id=user1, repo_id="u1-r1"))
        await repo.save(_make_repo_request(user_id=user1, repo_id="u1-r2"))

        # user2: 1 repo
        await repo.save(_make_repo_request(user_id=user2, repo_id="u2-r1"))

        count1 = await repo.count_by_user_id(user_id=user1)
        count2 = await repo.count_by_user_id(user_id=user2)

        assert count1 == 2
        assert count2 == 1

    # =================================================================
    # update_analysis_metadata_by_id
    # =================================================================

    async def test_update_analysis_metadata_by_id_should_update_fields_and_return_one(
        self, repo: IRepoStore
    ):
        req = _make_repo_request()
        saved = await repo.save(req)

        now = datetime.datetime.now(datetime.timezone.utc)
        updated = await repo.update_analysis_metadata_by_id(
            id=str(saved.id),
            status=StatusTypes.COMPLETED,
            processing_end_time=now,
            total_files=10,
            total_chunks=20,
            total_embeddings=30,
        )

        assert updated == 1

        refreshed = await repo.find_by_id(str(saved.id))
        assert refreshed is not None
        assert refreshed.status == StatusTypes.COMPLETED
        assert refreshed.processing_end_time.replace(microsecond=0, tzinfo=None) == now.replace(microsecond=0, tzinfo=None)
        assert refreshed.total_files == 10
        assert refreshed.total_chunks == 20
        assert refreshed.total_embeddings == 30

    async def test_update_analysis_metadata_by_id_should_return_zero_for_unknown_id(
        self, repo: IRepoStore
    ):
        now = datetime.datetime.now(datetime.timezone.utc)
        random_id = str(uuid.uuid4())

        updated = await repo.update_analysis_metadata_by_id(
            id=random_id,
            status=StatusTypes.COMPLETED,
            processing_end_time=now,
            total_files=1,
            total_chunks=1,
            total_embeddings=1,
        )

        assert updated == 0

    # =================================================================
    # update_repo_system_reference_by_id
    # =================================================================

    async def test_update_repo_system_reference_by_id_should_update_and_return_one(
        self, repo: IRepoStore
    ):
        req = _make_repo_request()
        saved = await repo.save(req)

        updated = await repo.update_repo_system_reference_by_id(
            id=str(saved.id),
            repo_system_reference="auto-note",
        )
        assert updated == 1

        refreshed = await repo.find_by_id(str(saved.id))
        assert refreshed is not None
        assert refreshed.repo_system_reference == "auto-note"

    async def test_update_repo_system_reference_by_id_should_return_zero_for_unknown_id(
        self, repo: IRepoStore
    ):
        random_id = str(uuid.uuid4())

        updated = await repo.update_repo_system_reference_by_id(
            id=random_id,
            repo_system_reference="whatever",
        )
        assert updated == 0

    # =================================================================
    # find_by_user_and_path / find_by_user_and_alias_name
    # =================================================================

    async def test_find_by_user_and_path_should_return_repo_when_exists(
        self, repo: IRepoStore
    ):
        req = _make_repo_request(
            user_id="user-path",
            repo_id="repo-path",
            relative_path="/user-path/repo-path",
        )
        saved = await repo.save(req)

        found = await repo.find_by_user_and_path(
            user_id="user-path", relative_path="/user-path/repo-path"
        )

        assert found is not None
        assert found.id == saved.id
        assert found.relative_path == "/user-path/repo-path"

    async def test_find_by_user_and_path_should_return_none_when_not_found(
        self, repo: IRepoStore
    ):
        found = await repo.find_by_user_and_path(
            user_id="user-path-missing",
            relative_path="/does/not/exist",
        )
        assert found is None

    async def test_find_by_user_and_alias_name_should_return_repo_when_exists(
        self, repo: IRepoStore
    ):
        req = _make_repo_request(
            user_id="user-alias",
            repo_id="repo-alias",
            repo_alias_name="my-alias",
        )
        saved = await repo.save(req)

        found = await repo.find_by_user_and_alias_name(
            user_id="user-alias", repo_alias_name="my-alias"
        )

        assert found is not None
        assert found.id == saved.id
        assert found.repo_alias_name == "my-alias"

    async def test_find_by_user_and_alias_name_should_return_none_when_not_found(
        self, repo: IRepoStore
    ):
        found = await repo.find_by_user_and_alias_name(
            user_id="user-alias-missing",
            repo_alias_name="no-such-alias",
        )
        assert found is None

    # =================================================================
    # save_context
    # =================================================================

    async def test_save_context_should_set_status_to_pending_for_existing_repo(
        self, repo: IRepoStore
    ):
        """
        save_context should mark an existing repo as pending and return the updated DTO.
        """
        req = _make_repo_request(
            user_id="ctx-user",
            repo_id="ctx-repo",
            status=StatusTypes.COMPLETED,
        )
        saved = await repo.save(req)

        result = await repo.save_context(
            repo_id="ctx-repo",
            user_id="ctx-user",
            config={"some": "config"},
        )

        assert isinstance(result, RepoResponseDTO)
        assert result.id == saved.id
        assert result.status == StatusTypes.PENDING

    async def test_save_context_should_raise_dev_dox_exception_when_repo_missing(
        self, repo: IRepoStore
    ):
        """
        When no repo exists for (user_id, repo_id), save_context must raise DevDoxModelsException
        with RepoErrors.REPOSITORY_DOESNT_EXIST.
        """
        with pytest.raises(DevDoxModelsException) as exc_info:
            await repo.save_context(
                repo_id="missing-repo",
                user_id="missing-user",
                config={},
            )
        
        exc = exc_info.value
        err = RepoErrors.REPOSITORY_DOESNT_EXIST.value
        assert exc.error_type == err["error_type"]
        assert exc.user_message == err["log_message"]
        assert exc.log_message == err["log_message"]
    
@pytest.mark.asyncio
class TestTortoiseRepoBackend(TestRepoBackend):
    __test__ = True
    
    @pytest_asyncio.fixture
    async def repo(self, postgresql_client):
        return TortoiseRepoBackend()

@pytest.mark.asyncio
class TestBeanieRepoBackend(TestRepoBackend):
    __test__ = True
    
    @pytest_asyncio.fixture
    async def repo(self, db_client):
        return BeanieRepoBackend()

@pytest.mark.asyncio
class TestInMemoryRepoBackend(TestRepoBackend):
    __test__ = True
    
    @pytest_asyncio.fixture
    async def repo(self):
        return InMemoryRepoBackend()


