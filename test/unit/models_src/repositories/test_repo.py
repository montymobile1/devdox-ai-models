import datetime
import uuid

import pytest
import pytest_asyncio
from beanie.exceptions import DocumentNotFound
from pymongo.errors import DuplicateKeyError

from models_src.exceptions.base_exceptions import DevDoxModelsException
from models_src.exceptions.utils import RepoErrors
from models_src.repositories.repo import (
    InMemoryRepoBackend, RepoStore,
)
from test.conftest import _make_repo_request
from test.live.models_src.repositories.test_repo import TestRepoBackend


@pytest.mark.asyncio
class TestRepoStoreValidation:
    repo_store = RepoStore

    # =================================================================
    # save
    # =================================================================
    async def test_save_duplicate_key_error_wrapped_as_internal_error(self):
        class FakeBackend:
            async def save(self, repo_model):
                raise DuplicateKeyError("duplicate repo")

        store = self.repo_store(storage_backend=FakeBackend())
        req = _make_repo_request()

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.save(repo_model=req)

        exc = exc_info.value
        err = RepoErrors.REPOSITORY_ALREADY_EXIST.value
        assert exc.error_type == err["error_type"]
        assert exc.user_message == err["log_message"]
        assert exc.log_message == err["log_message"]
        assert exc.log_level == "error"

    # =================================================================
    # save_context
    # =================================================================
    @pytest.mark.parametrize(
        "repo_id, user_id",
        [
            (None, "user"),
            ("", "user"),
            (" ", "user"),
            ("\t", "user"),
            ("rid", None),
            ("rid", ""),
            ("rid", " "),
            ("rid", "\t"),
        ],
    )
    async def test_save_context_invalid_args_raises_repo_not_exist(
        self,
        repo_id,
        user_id,
    ):
        store = self.repo_store(storage_backend=None)

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.save_context(repo_id=repo_id, user_id=user_id, config={})

        exc = exc_info.value
        err = RepoErrors.REPOSITORY_DOESNT_EXIST.value
        assert exc.error_type == err["error_type"]
        assert exc.user_message == err["log_message"]

    # =================================================================
    # get_by_id
    # =================================================================
    @pytest.mark.parametrize(
        "repo_id",
        [None, "", " ", "\t", "not-a-uuid"],
    )
    async def test_get_by_id_invalid_repo_id_raises_repo_not_exist(self, repo_id):
        store = self.repo_store(storage_backend=None)

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.get_by_id(repo_id=repo_id)

        exc = exc_info.value
        err = RepoErrors.REPOSITORY_DOESNT_EXIST.value
        assert exc.error_type == err["error_type"]
        assert exc.user_message == err["log_message"]

    async def test_get_by_id_backend_not_found_raises_repo_not_exist(self):
        class FakeBackend:
            async def get_by_id(self, repo_id: str):
                raise DocumentNotFound("not found")

        store = self.repo_store(storage_backend=FakeBackend())
        valid_id = str(uuid.uuid4())

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.get_by_id(repo_id=valid_id)

        exc = exc_info.value
        err = RepoErrors.REPOSITORY_DOESNT_EXIST.value
        assert exc.error_type == err["error_type"]
        assert exc.user_message == err["log_message"]

    # =================================================================
    # find_by_repo_id_user_id
    # =================================================================
    async def test_find_by_repo_id_user_id_not_found_raises_repo_not_exist(self):
        class FakeBackend:
            async def find_by_repo_id_user_id(self, repo_id: str, user_id: str):
                return None

        store = self.repo_store(storage_backend=FakeBackend())

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.find_by_repo_id_user_id(repo_id="rid", user_id="uid")

        exc = exc_info.value
        err = RepoErrors.REPOSITORY_DOESNT_EXIST.value
        assert exc.error_type == err["error_type"]
        assert exc.user_message == err["log_message"]

    # =================================================================
    # find_by_id
    # =================================================================
    @pytest.mark.parametrize(
        "id_value",
        [None, "", " ", "\t", "not-a-uuid"],
    )
    async def test_find_by_id_invalid_id_returns_none(self, id_value):
        store = self.repo_store(storage_backend=None)

        result = await store.find_by_id(id=id_value)
        assert result is None

    # =================================================================
    # find_all_by_user_id / count_by_user_id
    # =================================================================
    @pytest.mark.parametrize("user_id", [None, "", " ", "\t"])
    async def test_find_all_by_user_id_invalid_user_id_raises_missing_user(
        self,
        user_id,
    ):
        store = self.repo_store(storage_backend=None)

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.find_all_by_user_id(user_id=user_id, offset=0, limit=10)

        exc = exc_info.value
        err = RepoErrors.MISSING_USER_ID.value
        assert exc.error_type == err["error_type"]
        assert exc.user_message == err["log_message"]

    @pytest.mark.parametrize("user_id", [None, "", " ", "\t"])
    async def test_count_by_user_id_invalid_user_id_raises_missing_user(
        self,
        user_id,
    ):
        store = self.repo_store(storage_backend=None)

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.count_by_user_id(user_id=user_id)

        exc = exc_info.value
        err = RepoErrors.MISSING_USER_ID.value
        assert exc.error_type == err["error_type"]
        assert exc.user_message == err["log_message"]

    # =================================================================
    # update_analysis_metadata_by_id
    # =================================================================
    @pytest.mark.parametrize(
        "id_value, status, expected",
        [
            (None, "completed", -1),
            ("", "completed", -1),
            (" ", "completed", -1),
            ("\t", "completed", -1),
            ("not-a-uuid", "completed", -1),
            (str(uuid.uuid4()), None, -1),
            (str(uuid.uuid4()), "", -1),
            (str(uuid.uuid4()), " ", -1),
            (str(uuid.uuid4()), "\t", -1),
        ],
    )
    async def test_update_analysis_metadata_by_id_invalid_args_return_minus_one(
        self,
        id_value,
        status,
        expected,
    ):
        store = self.repo_store(storage_backend=None)

        result = await store.update_analysis_metadata_by_id(
            id=id_value,
            status=status,
            processing_end_time=datetime.datetime.now(datetime.timezone.utc),
            total_files=1,
            total_chunks=1,
            total_embeddings=1,
        )
        assert result == expected

    # =================================================================
    # update_repo_system_reference_by_id
    # =================================================================
    @pytest.mark.parametrize(
        "id_value, repo_system_reference, expected",
        [
            (None, "ref", -1),
            ("", "ref", -1),
            (" ", "ref", -1),
            ("\t", "ref", -1),
            ("not-a-uuid", "ref", -1),
            (str(uuid.uuid4()), None, -1),
            (str(uuid.uuid4()), "", -1),
            (str(uuid.uuid4()), " ", -1),
            (str(uuid.uuid4()), "\t", -1),
        ],
    )
    async def test_update_repo_system_reference_by_id_invalid_args_return_minus_one(
        self,
        id_value,
        repo_system_reference,
        expected,
    ):
        store = self.repo_store(storage_backend=None)

        result = await store.update_repo_system_reference_by_id(
            id=id_value,
            repo_system_reference=repo_system_reference,
        )
        assert result == expected

    # =================================================================
    # NEW: update_repo_parent_id validation
    # =================================================================
    @pytest.mark.parametrize(
        "repo_id, parent_repo_id",
        [
            (None, str(uuid.uuid4())),
            ("", str(uuid.uuid4())),
            (" ", str(uuid.uuid4())),
            ("\t", str(uuid.uuid4())),
            (str(uuid.uuid4()), None),
            (str(uuid.uuid4()), ""),
            (str(uuid.uuid4()), " "),
            (str(uuid.uuid4()), "\t"),
            ("not-a-uuid", str(uuid.uuid4())),
            (str(uuid.uuid4()), "not-a-uuid"),
        ],
    )
    async def test_update_repo_parent_id_invalid_args_return_minus_one(
        self,
        repo_id,
        parent_repo_id,
    ):
        store = self.repo_store(storage_backend=None)

        result = await store.update_repo_parent_id(
            repo_id=repo_id,
            parent_repo_id=parent_repo_id,
        )
        assert result == -1

    async def test_update_repo_parent_id_same_ids_return_minus_one(self):
        repo_id = str(uuid.uuid4())
        store = self.repo_store(storage_backend=None)

        result = await store.update_repo_parent_id(
            repo_id=repo_id,
            parent_repo_id=repo_id,
        )
        assert result == -1

    async def test_update_repo_parent_id_valid_delegates_to_backend(self):
        captured = {}

        class FakeBackend:
            async def update_repo_parent_id(self, repo_id: str, parent_repo_id: str) -> int:
                captured["repo_id"] = repo_id
                captured["parent_repo_id"] = parent_repo_id
                return 1

        store = self.repo_store(storage_backend=FakeBackend())
        repo_id = str(uuid.uuid4())
        parent_repo_id = str(uuid.uuid4())

        result = await store.update_repo_parent_id(
            repo_id=repo_id,
            parent_repo_id=parent_repo_id,
        )

        assert result == 1
        assert captured["repo_id"] == repo_id
        assert captured["parent_repo_id"] == parent_repo_id

    # =================================================================
    # NEW: find_all_by_user_id_and_html_urls validation
    # =================================================================
    @pytest.mark.parametrize(
        "html_urls",
        [
            set(),
            {None},
            {"", "https://example.com/a"},
            {" ", "https://example.com/a"},
            {"\t", "https://example.com/a"},
        ],
    )
    async def test_find_all_by_user_id_and_html_urls_invalid_html_urls_raise_internal_error(
        self,
        html_urls,
    ):
        store = self.repo_store(storage_backend=None)

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.find_all_by_user_id_and_html_urls(
                user_id="user-1",
                html_urls=html_urls,
            )

        exc = exc_info.value
        err = RepoErrors.INVALID_HTML_URL.value
        assert exc.error_type == err["error_type"]
        assert exc.user_message == err["log_message"]
        assert exc.log_message == err["log_message"]

    @pytest.mark.parametrize("user_id", [None, "", " ", "\t"])
    async def test_find_all_by_user_id_and_html_urls_invalid_user_id_raises_missing_user(
        self,
        user_id,
    ):
        store = self.repo_store(storage_backend=None)

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.find_all_by_user_id_and_html_urls(
                user_id=user_id,
                html_urls={"https://example.com/repo"},
            )

        exc = exc_info.value
        err = RepoErrors.MISSING_USER_ID.value
        assert exc.error_type == err["error_type"]
        assert exc.user_message == err["log_message"]

    async def test_find_all_by_user_id_and_html_urls_valid_delegates_to_backend(self):
        captured = {}

        class FakeBackend:
            async def find_all_by_user_id_and_html_urls(
                self,
                user_id: str,
                html_urls: set[str],
            ):
                captured["user_id"] = user_id
                captured["html_urls"] = html_urls
                return ["ok"]

        store = self.repo_store(storage_backend=FakeBackend())
        urls = {"https://example.com/a", "https://example.com/b"}

        result = await store.find_all_by_user_id_and_html_urls(
            user_id="user-123",
            html_urls=urls,
        )

        assert result == ["ok"]
        assert captured["user_id"] == "user-123"
        assert captured["html_urls"] == urls

@pytest.mark.asyncio
class TestInMemoryRepoBackend(TestRepoBackend):
    __test__ = True
    
    @pytest_asyncio.fixture
    async def repo(self):
        return InMemoryRepoBackend()