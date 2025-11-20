import pytest
import pytest_asyncio
from models_src.exceptions import exception_constants
from pymongo.errors import DuplicateKeyError
from tortoise.exceptions import IntegrityError

from models_src import DevDoxModelsException, RecordNotFound
from models_src.repositories.user import InMemoryUserBackend, UserStore
from test.live.models_src.repositories.test_user import TestUserBackend


@pytest.mark.asyncio
class TestUserStoreValidation:
    user_store = UserStore

    @pytest.mark.parametrize("exception_cls", [DuplicateKeyError, IntegrityError])
    async def test_save_db_conflict_exceptions_wrapped_as_internal_error(
        self,
        exception_cls,
    ):
        """
        UserStore.save should convert DuplicateKeyError / IntegrityError
        into DevDoxModelsException via internal_error(USER_ALREADY_EXIST).
        """

        class FakeBackend:
            async def save(self, user_model):
                raise exception_cls("conflict")

        store = self.user_store(storage_backend=FakeBackend())
        dummy_user = object()

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.save(user_model=dummy_user)

        exc = exc_info.value
        # we don't rely on specific error_type string to avoid coupling;
        # just assert it's our domain exception and log_level is error.
        assert isinstance(exc, DevDoxModelsException)
        assert exc.log_level == "error"

    @pytest.mark.parametrize("user_id", [None, "", " ", "\t"])
    async def test_find_by_user_id_invalid_returns_none(self, user_id):
        store = self.user_store(storage_backend=None)

        result = await store.find_by_user_id(user_id=user_id)
        assert result is None

    @pytest.mark.parametrize(
        "user_id, tokens_used, expected",
        [
            (None, 10, -1),
            ("", 10, -1),
            (" ", 10, -1),
            ("\t", 10, -1),
            ("valid-user", 0, -1),
            ("valid-user", None, -1),
        ],
    )
    async def test_increment_token_usage_invalid_args_return_minus_one(
        self,
        user_id,
        tokens_used,
        expected,
    ):
        store = self.user_store(storage_backend=None)

        result = await store.increment_token_usage(
            user_id=user_id,
            tokens_used=tokens_used,
        )
        assert result == expected
    
    @pytest.mark.parametrize("user_id", [None, "", " ", "\t"])
    async def test_exists_by_user_id_invalid_returns_false(self, user_id):
        store = self.user_store(storage_backend=None)
        
        result = await store.exists_by_user_id(user_id=user_id)
        assert result is False
    
    @pytest.mark.parametrize("user_id", [None, "", " ", "\t"])
    async def test_get_encryption_salt_invalid_causes_exception(self, user_id):
        store = self.user_store(storage_backend=None)
        
        with pytest.raises(RecordNotFound) as exp:
            await store.get_encryption_salt(user_id=user_id)
        
        assert exp.value.user_message == exception_constants.INVALID_PASSED_FIELDS


@pytest.mark.asyncio
class TestInMemoryUserBackend(TestUserBackend):
    __test__ = True
    
    @pytest_asyncio.fixture
    async def repo(self):
        return InMemoryUserBackend()