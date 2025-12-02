import datetime

import pytest
from models_src.exceptions.base_exceptions import DevDoxModelsException

from models_src.exceptions.exception_constants import MISSING_API_KEY_USER_ID_LOG_MESSAGE, MISSING_USER_ID_TITLE
from models_src.repositories.api_key import ApiKeyStore

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
            await self.api_key_store(storage_backend=None).find_all_by_user_id(
                offset=0,
                limit=10,
                user_id=user_id,
            )

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
            await self.api_key_store(storage_backend=None).count_by_user_id(
                user_id=user_id,
            )

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
        result = await self.api_key_store(storage_backend=None).exists_by_hash_key(
            hash_key=hash_key,
        )
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
        result = (
            await self.api_key_store(storage_backend=None)
            .update_is_active_by_user_id_and_api_key_id(
                user_id=user_id,
                api_key_id=api_key_id,
                is_active=True,
            )
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
        result = await self.api_key_store(storage_backend=None).find_by_active_api_key(
            api_key=api_key,
            is_active=True,
        )
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
