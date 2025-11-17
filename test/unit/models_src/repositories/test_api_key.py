import datetime
import uuid

import pytest
from models_src.exceptions.base_exceptions import DevDoxModelsException

from models_src import APIKeyResponseDTO
from models_src.exceptions.exception_constants import MISSING_API_KEY_USER_ID_LOG_MESSAGE, MISSING_USER_ID_TITLE
from models_src.repositories.api_key import ApiKeyStore, InMemoryApiKeyBackend
from test.conftest import _make_api_key_request


@pytest.mark.asyncio
class TestInMemoryApiKeyBackend:
    
    inmemory_store = InMemoryApiKeyBackend
    
    async def test_save_and_get_by_active_api_key(self):
        
        store = self.inmemory_store()
        
        req = _make_api_key_request(
            user_id="user-save",
            api_key="hash-save-1",
            masked_api_key="****save1",
            is_active=True,
        )

        saved = await store.save(req)

        assert isinstance(saved, APIKeyResponseDTO)
        assert saved.id is not None
        assert isinstance(saved.id, uuid.UUID)
        assert saved.user_id == req.user_id
        assert saved.api_key == req.api_key
        assert saved.masked_api_key == req.masked_api_key
        assert saved.is_active is True
        assert isinstance(saved.created_at, datetime.datetime)

        fetched = await store.find_by_active_api_key("hash-save-1")
        assert fetched is not None
        assert fetched.id == saved.id

    async def test_exists_by_hash_key_true_and_false(self):
        
        store = self.inmemory_store()
        
        req = _make_api_key_request(
            user_id="user-exists",
            api_key="hash-exists",
            masked_api_key="****exists",
            is_active=True,
        )
        await store.save(req)

        assert await store.exists_by_hash_key("hash-exists") is True
        assert await store.exists_by_hash_key("hash-missing") is False

    async def test_count_by_user_id_counts_only_active(self):
        
        store = self.inmemory_store()
        
        user_id = "user-count"

        await store.save(
            _make_api_key_request(user_id=user_id, api_key="hash-active-1", masked_api_key="****a1", is_active=True)
        )
        await store.save(
            _make_api_key_request(user_id=user_id, api_key="hash-active-2", masked_api_key="****a2", is_active=True)
        )
        await store.save(
            _make_api_key_request(user_id=user_id, api_key="hash-inactive", masked_api_key="****i", is_active=False)
        )
        await store.save(
            _make_api_key_request(user_id="other-user", api_key="hash-other", masked_api_key="****o", is_active=True)
        )

        count = await store.count_by_user_id(user_id)
        assert count == 2

    async def test_find_all_by_user_id_sorted_and_filtered(self):
        """
        The current InMemory implementation:
        - Returns ALL active keys for a user
        - Sorted by created_at desc
        - Ignores offset/limit
        This test encodes that behavior.
        """
        store = self.inmemory_store()
        
        user_id = "user-find-all"

        saved1 = await store.save(
            _make_api_key_request(user_id=user_id, api_key="hash-fa-1", masked_api_key="****fa1", is_active=True)
        )
        saved2 = await store.save(
            _make_api_key_request(user_id=user_id, api_key="hash-fa-2", masked_api_key="****fa2", is_active=True)
        )
        saved3 = await store.save(
            _make_api_key_request(user_id=user_id, api_key="hash-fa-3", masked_api_key="****fa3", is_active=True)
        )

        await store.save(
            _make_api_key_request(user_id=user_id, api_key="hash-fa-inactive", masked_api_key="****fai", is_active=False)
        )

        # Even though we pass offset/limit, current implementation returns all active
        result = await store.find_all_by_user_id(offset=0, limit=2, user_id=user_id)

        assert len(result) == 3
        ids = [item.id for item in result]
        # Should contain exactly the 3 active IDs
        assert set(ids) == {saved1.id, saved2.id, saved3.id}

        # Should be in descending created_at order
        created_times = [item.created_at for item in result]
        assert created_times == sorted(created_times, reverse=True)

    async def test_find_by_active_api_key_respects_is_active(self):
        
        store = self.inmemory_store()
        
        user_id = "user-find-by-hash"

        active = await store.save(
            _make_api_key_request(user_id=user_id, api_key="hash-active", masked_api_key="****ha", is_active=True)
        )
        inactive = await store.save(
            _make_api_key_request(user_id=user_id, api_key="hash-inactive", masked_api_key="****hi", is_active=False)
        )

        found_active = await store.find_by_active_api_key("hash-active")
        assert found_active is not None
        assert found_active.id == active.id
        assert found_active.is_active is True

        assert await store.find_by_active_api_key("hash-inactive") is None

        found_inactive = await store.find_by_active_api_key("hash-inactive", is_active=False)
        assert found_inactive is not None
        assert found_inactive.id == inactive.id
        assert found_inactive.is_active is False

    async def test_update_is_active_by_user_id_and_api_key_id(self):
        """
        NOTE: This test encodes the *intended* IApiKeyStore contract:
        - Look up by ID + user_id when active
        - Toggle is_active and return 1 on success
        With current InMemory implementation, this may fail (it compares UUID(api_key) to api_key_id).
        If this test fails, you'll likely want to fix that method.
        """
        
        store = self.inmemory_store()
        
        user_id = "user-update-active"
        
        api_key_uuid = uuid.uuid4()
        
        saved = await store.save(
            _make_api_key_request(user_id=user_id, api_key=str(api_key_uuid), masked_api_key="****upd", is_active=True)
        )

        updated_count = await store.update_is_active_by_user_id_and_api_key_id(
            user_id=user_id,
            api_key_id=uuid.UUID(saved.api_key),
            is_active=False,
        )

        assert updated_count == 1

        assert await store.find_by_active_api_key(str(api_key_uuid)) is None

        inactive = await store.find_by_active_api_key(str(api_key_uuid), is_active=False)
        assert inactive is not None
        assert inactive.is_active is False

    async def test_update_last_used_by_id_with_explicit_timestamp(self):
        
        store = self.inmemory_store()
        
        user_id = "user-last-used-explicit"

        saved = await store.save(
            _make_api_key_request(user_id=user_id, api_key="hash-last-specific", masked_api_key="****ls", is_active=True)
        )

        assert saved.last_used_at is None

        fixed_time = datetime.datetime(2020, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)

        updated_count = await store.update_last_used_by_id(id=str(saved.id), last_used_at=fixed_time)
        assert updated_count == 1

        refreshed = await store.find_by_active_api_key("hash-last-specific", is_active=True)
        assert refreshed is not None
        assert refreshed.last_used_at == fixed_time

    async def test_update_last_used_by_id_sets_now_when_not_provided(self):
        
        store = self.inmemory_store()
        
        user_id = "user-last-used-auto"

        saved = await store.save(
            _make_api_key_request(user_id=user_id, api_key="hash-last-auto", masked_api_key="****la", is_active=True)
        )
        assert saved.last_used_at is None

        updated_count = await store.update_last_used_by_id(id=str(saved.id), last_used_at=None)
        assert updated_count == 1

        refreshed = await store.find_by_active_api_key("hash-last-auto", is_active=True)
        assert refreshed is not None
        assert isinstance(refreshed.last_used_at, datetime.datetime)

    async def test_update_last_used_by_id_returns_zero_for_missing_id(self):
        
        store = self.inmemory_store()
        
        missing_id = str(uuid.uuid4())
        updated_count = await store.update_last_used_by_id(
            id=missing_id,
            last_used_at=datetime.datetime.now(datetime.timezone.utc),
        )
        assert updated_count == 0


@pytest.mark.asyncio
class TestApiKeyStoreValidation:
    
    api_key_store = ApiKeyStore
    
    # ------------------------------------------------------------------
    # find_all_by_user_id: invalid user_id → DevDoxModelsException
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("user_id", [None, "", " ", "\t"])
    async def test_find_all_by_user_id_invalid_user_id_raises_internal_error(
        self,
        user_id,
    ):
        with pytest.raises(DevDoxModelsException) as exc_info:
            await self.api_key_store(storage_backend=None).find_all_by_user_id(offset=0, limit=10, user_id=user_id)

        exc = exc_info.value
        assert exc.error_type == MISSING_USER_ID_TITLE
        assert exc.user_message == MISSING_API_KEY_USER_ID_LOG_MESSAGE
        assert exc.log_message == MISSING_API_KEY_USER_ID_LOG_MESSAGE
        # internal_error uses log_level=logging.FATAL → "critical"
        assert exc.log_level == "critical"

    # ------------------------------------------------------------------
    # count_by_user_id: invalid user_id → DevDoxModelsException
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("user_id", [None, "", " ", "\t"])
    async def test_count_by_user_id_invalid_user_id_raises_internal_error(
        self,
        user_id,
    ):
        with pytest.raises(DevDoxModelsException) as exc_info:
            await self.api_key_store(storage_backend=None).count_by_user_id(user_id=user_id)

        exc = exc_info.value
        assert exc.error_type == MISSING_USER_ID_TITLE
        assert exc.user_message == MISSING_API_KEY_USER_ID_LOG_MESSAGE
        assert exc.log_message == MISSING_API_KEY_USER_ID_LOG_MESSAGE
        assert exc.log_level == "critical"

    # ------------------------------------------------------------------
    # exists_by_hash_key: invalid hash_key → False (no backend call)
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("hash_key", [None, "", " ", "\t"])
    async def test_exists_by_hash_key_invalid_returns_false(
        self,
        hash_key,
    ):
        result = await self.api_key_store(storage_backend=None).exists_by_hash_key(hash_key=hash_key)
        assert result is False

    # ------------------------------------------------------------------
    # update_is_active_by_user_id_and_api_key_id:
    #   invalid user_id OR missing api_key_id → -1
    # ------------------------------------------------------------------
    @pytest.mark.parametrize(
        "user_id, api_key_id, expected",
        [
            (None, "some-id", -1),
            ("", "some-id", -1),
            (" ", "some-id", -1),
            ("\t", "some-id", -1),
            ("valid-user", None, -1),
        ],
    )
    async def test_update_is_active_invalid_args_return_minus_one(
        self,
        user_id,
        api_key_id,
        expected,
    ):
        result = await self.api_key_store(storage_backend=None).update_is_active_by_user_id_and_api_key_id(
            user_id=user_id,
            api_key_id=api_key_id,
            is_active=True,
        )
        assert result == expected

    # ------------------------------------------------------------------
    # find_by_active_api_key:
    #   invalid api_key → None
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("api_key", [None, "", " ", "\t"])
    async def test_find_by_active_api_key_invalid_returns_none(
        self,
        api_key,
    ):
        result = await self.api_key_store(storage_backend=None).find_by_active_api_key(api_key=api_key, is_active=True)
        assert result is None

    # ------------------------------------------------------------------
    # update_last_used_by_id:
    #   invalid id (empty/blank/invalid UUID) → -1
    # ------------------------------------------------------------------
    @pytest.mark.parametrize(
        "id_value",
        [
            None,
            "",
            " ",
            "\t",
            "not-a-uuid",
            "1234",  # still invalid UUID
        ],
    )
    async def test_update_last_used_by_id_invalid_id_returns_minus_one(
        self,
        id_value,
    ):
        now = datetime.datetime.now(datetime.timezone.utc)

        result = await self.api_key_store(storage_backend=None).update_last_used_by_id(
            id=id_value,
            last_used_at=now,
        )
        assert result == -1
