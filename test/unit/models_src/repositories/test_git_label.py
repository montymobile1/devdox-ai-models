import uuid

import pytest
from pymongo.errors import DuplicateKeyError

from models_src.dto.git_label import GitLabelResponseDTO
from models_src.dto.repo import GitHosting
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


@pytest.mark.asyncio
class TestInMemoryGitLabelBackend:
    inmemory_store = InMemoryGitLabelBackend

    async def test_save_and_find_by_token_id_and_user(self):
        store = self.inmemory_store()

        req = _make_git_label_request(
            user_id="mem-user-1",
            label="mem-label",
            git_hosting=GitHosting.GITHUB,
            username="u1",
            token_value="t1",
            masked_token="****1",
        )

        saved = await store.save(req)

        assert isinstance(saved, GitLabelResponseDTO)
        assert isinstance(saved.id, uuid.UUID)
        assert saved.user_id == req.user_id
        assert saved.label == req.label
        assert saved.username == req.username
        assert saved.masked_token == req.masked_token

        fetched = await store.find_by_token_id_and_user(
            token_id=str(saved.id),
            user_id=req.user_id,
        )
        assert fetched is not None
        assert fetched.id == saved.id

    async def test_save_duplicate_raises_duplicate_key_error(self):
        store = self.inmemory_store()
        user_id = "mem-user-dup"

        req1 = _make_git_label_request(
            user_id=user_id,
            label="same-label",
            git_hosting=GitHosting.GITHUB,
            username="u1",
            token_value="t1",
            masked_token="****dup",
        )
        await store.save(req1)

        # Same user_id + git_hosting + masked_token -> should raise DuplicateKeyError
        req2 = _make_git_label_request(
            user_id=user_id,
            label="different-label",
            git_hosting=GitHosting.GITHUB,
            username="u2",
            token_value="t2",
            masked_token="****dup",
        )

        with pytest.raises(DuplicateKeyError):
            await store.save(req2)

    async def test_find_git_hostings_by_ids_filters_by_ids(self):
        store = self.inmemory_store()

        saved1 = await store.save(
            _make_git_label_request(
                user_id="u1",
                label="l1",
                git_hosting=GitHosting.GITHUB,
                username="u1",
                token_value="t1",
                masked_token="****1",
            )
        )
        saved2 = await store.save(
            _make_git_label_request(
                user_id="u2",
                label="l2",
                git_hosting=GitHosting.GITLAB,
                username="u2",
                token_value="t2",
                masked_token="****2",
            )
        )
        await store.save(
            _make_git_label_request(
                user_id="u3",
                label="l3",
                git_hosting="BITBUCKET",
                username="u3",
                token_value="t3",
                masked_token="****3",
            )
        )

        token_ids = [str(saved1.id), str(saved2.id)]

        results = await store.find_git_hostings_by_ids(token_ids=token_ids)

        assert len(results) == 2
        ids = {r["id"] for r in results}
        assert ids == {saved1.id, saved2.id}

    async def test_find_by_id_and_user_id_and_git_hosting(self):
        store = self.inmemory_store()
        user_id = "mem-user-find"

        saved = await store.save(
            _make_git_label_request(
                user_id=user_id,
                label="mem-label-2",
                git_hosting=GitHosting.GITHUB,
                username="u",
                token_value="t",
                masked_token="****m",
            )
        )

        found = await store.find_by_id_and_user_id_and_git_hosting(
            id=str(saved.id),
            user_id=user_id,
            git_hosting=saved.git_hosting,
        )
        assert found is not None
        assert found.id == saved.id

        not_found = await store.find_by_id_and_user_id_and_git_hosting(
            id=str(saved.id),
            user_id=user_id,
            git_hosting=GitHosting.GITLAB,
        )
        assert not_found is None

    async def test_find_all_by_user_id_and_count(self):
        store = self.inmemory_store()
        user_id = "mem-user-all"

        await store.save(
            _make_git_label_request(
                user_id=user_id,
                label="l1",
                git_hosting=GitHosting.GITHUB,
                username="u1",
                token_value="t1",
                masked_token="****1",
            )
        )
        await store.save(
            _make_git_label_request(
                user_id=user_id,
                label="l2",
                git_hosting=GitHosting.GITHUB,
                username="u2",
                token_value="t2",
                masked_token="****2",
            )
        )
        await store.save(
            _make_git_label_request(
                user_id=user_id,
                label="l3",
                git_hosting=GitHosting.GITLAB,
                username="u3",
                token_value="t3",
                masked_token="****3",
            )
        )
        await store.save(
            _make_git_label_request(
                user_id="other-user",
                label="other",
                git_hosting=GitHosting.GITHUB,
                username="ux",
                token_value="tx",
                masked_token="****x",
            )
        )

        all_for_user = await store.find_all_by_user_id(
            offset=0,
            limit=10,
            user_id=user_id,
        )
        assert len(all_for_user) == 3

        count_all = await store.count_by_user_id(user_id=user_id)
        assert count_all == 3

        count_github = await store.count_by_user_id(
            user_id=user_id,
            git_hosting=GitHosting.GITHUB,
        )
        assert count_github == 2

    async def test_find_all_by_user_id_and_label_and_count_by_user_id_and_label(self):
        store = self.inmemory_store()
        user_id = "mem-user-label"

        await store.save(
            _make_git_label_request(
                user_id=user_id,
                label="prod",
                git_hosting=GitHosting.GITHUB,
                username="u1",
                token_value="t1",
                masked_token="****1",
            )
        )
        await store.save(
            _make_git_label_request(
                user_id=user_id,
                label="prod",
                git_hosting=GitHosting.GITLAB,
                username="u2",
                token_value="t2",
                masked_token="****2",
            )
        )
        await store.save(
            _make_git_label_request(
                user_id=user_id,
                label="dev",
                git_hosting=GitHosting.GITHUB,
                username="u3",
                token_value="t3",
                masked_token="****3",
            )
        )

        labels = await store.find_all_by_user_id_and_label(
            offset=0,
            limit=10,
            user_id=user_id,
            label="prod",
        )
        assert len(labels) == 2
        assert all(l.label == "prod" for l in labels)

        count_prod = await store.count_by_user_id_and_label(user_id=user_id, label="prod")
        assert count_prod == 2

        count_all = await store.count_by_user_id_and_label(user_id=user_id, label=None)
        assert count_all == 3

    async def test_delete_by_id_and_user_id(self):
        store = self.inmemory_store()
        user_id = "mem-user-delete"

        saved1 = await store.save(
            _make_git_label_request(
                user_id=user_id,
                label="delete-me",
                git_hosting=GitHosting.GITHUB,
                username="u1",
                token_value="t1",
                masked_token="****1",
            )
        )
        saved2 = await store.save(
            _make_git_label_request(
                user_id=user_id,
                label="keep-me",
                git_hosting=GitHosting.GITHUB,
                username="u2",
                token_value="t2",
                masked_token="****2",
            )
        )

        deleted = await store.delete_by_id_and_user_id(label_id=saved1.id, user_id=user_id)
        assert deleted == 1

        deleted_again = await store.delete_by_id_and_user_id(label_id=saved1.id, user_id=user_id)
        assert deleted_again == 0


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
