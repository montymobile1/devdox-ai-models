import datetime
import uuid

import pytest

from models_src import UserResponseDTO
from models_src.repositories.user import InMemorUserStore, UserStore
from test.conftest import _make_user_request


@pytest.mark.asyncio
class TestInMemoryUserStore:
    inmemory_store = InMemorUserStore

    async def test_save_and_find_by_user_id(self):
        store = self.inmemory_store()

        req = _make_user_request(
            user_id="mem-user-1",
            first_name="Carol",
            last_name="Brown",
            email="carol@example.com",
            role="user",
        )

        saved = await store.save(req)

        assert isinstance(saved, UserResponseDTO)
        assert isinstance(saved.id, uuid.UUID)
        assert saved.user_id == req.user_id
        assert isinstance(saved.created_at, datetime.datetime)

        fetched = await store.find_by_user_id("mem-user-1")
        assert fetched is not None
        assert fetched.id == saved.id

    async def test_increment_token_usage_increments(self):
        store = self.inmemory_store()

        req = _make_user_request(
            user_id="mem-user-2",
            token_limit=1000,
            token_used=10,
        )
        saved = await store.save(req)

        updated = await store.increment_token_usage(
            user_id="mem-user-2",
            tokens_used=25,
        )
        assert updated == 1

        refreshed = await store.find_by_user_id("mem-user-2")
        assert refreshed is not None
        assert refreshed.id == saved.id
        assert refreshed.token_used == 35  # 10 + 25

    async def test_increment_token_usage_missing_user_returns_zero(self):
        store = self.inmemory_store()

        updated = await store.increment_token_usage(
            user_id="non-existent",
            tokens_used=10,
        )
        assert updated == 0

    async def test_exists_by_user_id_true_and_false(self):
        store = self.inmemory_store()

        req = _make_user_request(user_id="mem-user-3")
        await store.save(req)

        assert await store.exists_by_user_id("mem-user-3") is True
        assert await store.exists_by_user_id("mem-user-missing") is False


@pytest.mark.asyncio
class TestUserStoreValidation:
    user_store = UserStore

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
