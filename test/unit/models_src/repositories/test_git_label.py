import uuid

import pytest
import pytest_asyncio
from pymongo.errors import DuplicateKeyError
from tortoise.exceptions import IntegrityError

from models_src.exceptions.base_exceptions import DevDoxModelsException
from models_src.exceptions.exception_constants import (
    LABEL_ALREADY_EXISTS_MESSAGE,
    LABEL_ALREADY_EXISTS_TITLE,
    MISSING_LABEL_ID_TITLE,
    MISSING_LABEL_LOG_MESSAGE,
    MISSING_USER_ID_LOG_MESSAGE,
    MISSING_USER_ID_TITLE,
)
from models_src.repositories.git_label import (
    GitLabelStore,
    InMemoryGitLabelBackend,
)
from test.conftest import _make_git_label_request
from test.live.models_src.repositories.test_git_label import TestGitLabelBackend


@pytest.mark.asyncio
class TestGitLabelStoreValidation:
    git_label_store = GitLabelStore

    async def test_save_duplicate_key_error_wrapped_as_internal_error(self):
        """
        Store.save should convert DuplicateKeyError into DevDoxModelsException
        using GitLabelErrors.GIT_LABEL_ALREADY_EXISTS.
        """

        class FakeBackend:
            async def save(self, label_model):
                raise DuplicateKeyError("duplicate")

        store = self.git_label_store(storage_backend=FakeBackend())
        req = _make_git_label_request()

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.save(label_model=req)

        exc = exc_info.value
        assert exc.error_type == LABEL_ALREADY_EXISTS_TITLE
        assert exc.user_message == LABEL_ALREADY_EXISTS_MESSAGE
        assert exc.log_message == LABEL_ALREADY_EXISTS_MESSAGE
        assert exc.log_level == "error"

    async def test_save_integrity_error_wrapped_as_internal_error(self):
        """
        Store.save should convert IntegrityError into DevDoxModelsException
        using GitLabelErrors.GIT_LABEL_ALREADY_EXISTS.
        """

        class FakeBackend:
            async def save(self, label_model):
                raise IntegrityError("duplicate")

        store = self.git_label_store(storage_backend=FakeBackend())
        req = _make_git_label_request()

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.save(label_model=req)

        exc = exc_info.value
        assert exc.error_type == LABEL_ALREADY_EXISTS_TITLE
        assert exc.user_message == LABEL_ALREADY_EXISTS_MESSAGE
        assert exc.log_message == LABEL_ALREADY_EXISTS_MESSAGE
        assert exc.log_level == "error"

    async def test_find_git_hostings_by_ids_empty_returns_empty(self):
        store = self.git_label_store(storage_backend=None)

        result = await store.find_git_hostings_by_ids(token_ids=[])
        assert result == []

    @pytest.mark.parametrize(
        "token_id, user_id",
        [
            (None, "user"),
            ("", "user"),
            (" ", "user"),
            ("\t", "user"),
            ("not-a-uuid", "user"),
            ("some-id", None),
            ("some-id", ""),
            ("some-id", " "),
            ("some-id", "\t"),
        ],
    )
    async def test_find_by_token_id_and_user_invalid_returns_none(
        self,
        token_id,
        user_id,
    ):
        store = self.git_label_store(storage_backend=None)

        result = await store.find_by_token_id_and_user(
            token_id=token_id,
            user_id=user_id,
        )
        assert result is None

    @pytest.mark.parametrize(
        "id_value, user_id, git_hosting",
        [
            (None, "user", "github"),
            ("", "user", "github"),
            (" ", "user", "github"),
            ("\t", "user", "github"),
            ("not-a-uuid", "user", "github"),
            ("valid-id", None, "github"),
            ("valid-id", "", "github"),
            ("valid-id", " ", "github"),
            ("valid-id", "\t", "github"),
            ("valid-id", "user", None),
            ("valid-id", "user", ""),
            ("valid-id", "user", " "),
            ("valid-id", "user", "\t"),
        ],
    )
    async def test_find_by_id_and_user_id_and_git_hosting_invalid_returns_none(
        self,
        id_value,
        user_id,
        git_hosting,
    ):
        store = self.git_label_store(storage_backend=None)

        result = await store.find_by_id_and_user_id_and_git_hosting(
            id=id_value,
            user_id=user_id,
            git_hosting=git_hosting,
        )
        assert result is None

    @pytest.mark.parametrize("user_id", [None, "", " ", "\t"])
    async def test_find_all_by_user_id_invalid_user_id_raises_internal_error(
        self,
        user_id,
    ):
        store = self.git_label_store(storage_backend=None)

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.find_all_by_user_id(
                offset=0,
                limit=10,
                user_id=user_id,
            )

        exc = exc_info.value
        assert exc.error_type == MISSING_USER_ID_TITLE
        assert exc.user_message == MISSING_USER_ID_LOG_MESSAGE
        assert exc.log_message == MISSING_USER_ID_LOG_MESSAGE
        assert exc.log_level == "critical"

    @pytest.mark.parametrize("user_id", [None, "", " ", "\t"])
    async def test_count_by_user_id_invalid_user_id_raises_internal_error(
        self,
        user_id,
    ):
        store = self.git_label_store(storage_backend=None)

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.count_by_user_id(user_id=user_id)

        exc = exc_info.value
        assert exc.error_type == MISSING_USER_ID_TITLE
        assert exc.user_message == MISSING_USER_ID_LOG_MESSAGE
        assert exc.log_message == MISSING_USER_ID_LOG_MESSAGE
        assert exc.log_level == "critical"

    @pytest.mark.parametrize("user_id", [None, ""])
    async def test_find_all_by_user_id_and_label_missing_user_id_raises_internal_error(
        self,
        user_id,
    ):
        store = self.git_label_store(storage_backend=None)

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.find_all_by_user_id_and_label(
                offset=0,
                limit=10,
                user_id=user_id,
                label="prod",
            )

        exc = exc_info.value
        assert exc.error_type == MISSING_USER_ID_TITLE
        assert exc.user_message == MISSING_USER_ID_LOG_MESSAGE
        assert exc.log_message == MISSING_USER_ID_LOG_MESSAGE
        assert exc.log_level == "critical"

    @pytest.mark.parametrize("label", [None, "", " ", "\t"])
    async def test_find_all_by_user_id_and_label_missing_label_raises_internal_error(
        self,
        label,
    ):
        store = self.git_label_store(storage_backend=None)

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.find_all_by_user_id_and_label(
                offset=0,
                limit=10,
                user_id="valid-user",
                label=label,
            )

        exc = exc_info.value
        assert exc.error_type == MISSING_LABEL_ID_TITLE
        assert exc.user_message == MISSING_LABEL_LOG_MESSAGE
        assert exc.log_message == MISSING_LABEL_LOG_MESSAGE
        assert exc.log_level == "critical"

    @pytest.mark.parametrize("user_id", [None, ""])
    async def test_count_by_user_id_and_label_missing_user_id_raises_internal_error(
        self,
        user_id,
    ):
        store = self.git_label_store(storage_backend=None)

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.count_by_user_id_and_label(
                user_id=user_id,
                label="prod",
            )

        exc = exc_info.value
        assert exc.error_type == MISSING_USER_ID_TITLE
        assert exc.user_message == MISSING_USER_ID_LOG_MESSAGE
        assert exc.log_message == MISSING_USER_ID_LOG_MESSAGE
        assert exc.log_level == "critical"

    @pytest.mark.parametrize("label", [None, "", " ", "\t"])
    async def test_count_by_user_id_and_label_missing_label_raises_internal_error(
        self,
        label,
    ):
        store = self.git_label_store(storage_backend=None)

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.count_by_user_id_and_label(
                user_id="valid-user",
                label=label,
            )

        exc = exc_info.value
        assert exc.error_type == MISSING_LABEL_ID_TITLE
        assert exc.user_message == MISSING_LABEL_LOG_MESSAGE
        assert exc.log_message == MISSING_LABEL_LOG_MESSAGE
        assert exc.log_level == "critical"

    @pytest.mark.parametrize(
        "label_id, user_id, expected",
        [
            (None, "user", -1),
            (uuid.uuid4(), None, -1),
            (uuid.uuid4(), "", -1),
            (uuid.uuid4(), " ", -1),
            (uuid.uuid4(), "\t", -1),
            ("not-a-uuid", "user", -1),
        ],
    )
    async def test_delete_by_id_and_user_id_invalid_args_return_minus_one(
        self,
        label_id,
        user_id,
        expected,
    ):
        store = self.git_label_store(storage_backend=None)

        result = await store.delete_by_id_and_user_id(
            label_id=label_id,
            user_id=user_id,
        )
        assert result == expected


@pytest.mark.asyncio
class TestInMemoryGitLabelBackend(TestGitLabelBackend):
    __test__ = True
    
    @pytest_asyncio.fixture
    async def repo(self):
        return InMemoryGitLabelBackend()