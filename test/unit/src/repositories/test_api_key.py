import uuid
import pytest
from unittest.mock import MagicMock, AsyncMock

from models_src.dto.api_key import APIKeyRequestDTO, APIKeyResponseDTO
from models_src.repositories.api_key import TortoiseApiKeyStore
from test.unit.common_test_tools.model_factories import make_apikey
from test.unit.common_test_tools.qs_chain import make_qs_chain


class TestSave:
    @pytest.mark.asyncio
    async def test_save_returns_dto_with_real_model_instance(self, no_model_io, forbid_db, monkeypatch):
        """Saving should call model.create() and hand back a DTO. No DB calls."""
        store = TortoiseApiKeyStore()

        model = MagicMock()
        model.create = AsyncMock(return_value=make_apikey(user_id="u1", api_key="K1"))
        monkeypatch.setattr(store, "model", model)

        dto = await store.save(APIKeyRequestDTO(user_id="u1", api_key="K1", masked_api_key="*K1*"))
        model.create.assert_awaited_once()
        assert isinstance(dto, APIKeyResponseDTO)
        assert (dto.user_id, dto.api_key) == ("u1", "K1")


class TestExistsByHashKey:
    @pytest.mark.asyncio
    async def test_blank_input_short_circuits(self, monkeypatch):
        """Blank key -> False and zero DB work."""
        store = TortoiseApiKeyStore()
        model = MagicMock()
        monkeypatch.setattr(store, "model", model)
        assert await store.exists_by_hash_key("") is False
        assert await store.exists_by_hash_key("   ") is False
        model.filter.assert_not_called()

    @pytest.mark.asyncio
    async def test_hit_and_miss(self, monkeypatch):
        """When a key exists, return True; when it doesn't, return False."""
        store = TortoiseApiKeyStore()
        model = MagicMock()

        qs_true = make_qs_chain(exists_value=True)
        qs_false = make_qs_chain(exists_value=False)

        # First call returns True, second returns False
        model.filter.side_effect = [qs_true, qs_false]
        monkeypatch.setattr(store, "model", model)

        assert await store.exists_by_hash_key("HIT") is True
        assert await store.exists_by_hash_key("MISS") is False

        model.filter.assert_any_call(api_key="HIT")
        model.filter.assert_any_call(api_key="MISS")


class TestUpdateIsActive:
    @pytest.mark.asyncio
    async def test_bad_inputs_return_minus1(self):
        """Bad user_id or missing id -> -1 and no DB calls."""
        store = TortoiseApiKeyStore()
        assert await store.update_is_active_by_user_id_and_api_key_id("", uuid.UUID(int=0), True) == -1
        assert await store.update_is_active_by_user_id_and_api_key_id("u", None, True) == -1  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_happy_path_filters_then_updates(self, monkeypatch):
        """Filter by (user_id, id, is_active=True), then set is_active to the new value."""
        store = TortoiseApiKeyStore()
        api_id = uuid.uuid4()

        qs = make_qs_chain(update_value=1)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        changed = await store.update_is_active_by_user_id_and_api_key_id("u1", api_id, False)
        assert changed == 1

        model.filter.assert_called_once_with(user_id="u1", id=api_id, is_active=True)
        qs.update.assert_awaited_once_with(is_active=False)


class TestCountByUserId:
    @pytest.mark.asyncio
    async def test_blank_user_raises(self):
        """Blank user_id -> repo raises its internal error."""
        store = TortoiseApiKeyStore()
        with pytest.raises(Exception):
            await store.count_by_user_id(" ")

    @pytest.mark.asyncio
    async def test_filters_active_and_calls_count(self, monkeypatch):
        """Normal case: filter active-only then call count()."""
        store = TortoiseApiKeyStore()
        qs = make_qs_chain(count_value=3)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        n = await store.count_by_user_id("u9")
        assert n == 3
        model.filter.assert_called_once_with(user_id="u9", is_active=True)
        qs.count.assert_awaited_once()


class TestFindAllByUserId:
    @pytest.mark.asyncio
    async def test_orders_desc_then_pages_then_maps(self, monkeypatch):
        """Builds query, orders by newest, paginates (offset*limit), maps to DTOs."""
        store = TortoiseApiKeyStore()

        rows = [
            make_apikey(user_id="u", api_key="K2"),
            make_apikey(user_id="u", api_key="K1"),
        ]
        qs = make_qs_chain(result_for_all=rows)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        out = await store.find_all_by_user_id(offset=2, limit=3, user_id="u")
        assert all(isinstance(x, APIKeyResponseDTO) for x in out)

        model.filter.assert_called_once_with(user_id="u", is_active=True)
        qs.order_by.assert_called_once_with("-created_at")
        qs.offset.assert_called_once_with(2 * 3)   # important: offset * limit
        qs.limit.assert_called_once_with(3)
        qs.all.assert_awaited_once()


class TestFindByActiveApiKey:
    @pytest.mark.asyncio
    async def test_blank_api_key_returns_none(self, monkeypatch):
        """Blank api_key -> None and zero DB calls."""
        store = TortoiseApiKeyStore()
        model = MagicMock()
        monkeypatch.setattr(store, "model", model)
        assert await store.find_by_active_api_key("") is None
        assert await store.find_by_active_api_key("   ") is None
        model.filter.assert_not_called()

    @pytest.mark.asyncio
    async def test_filters_by_key_and_active_then_maps(self, monkeypatch):
        """Filter(api_key=..., is_active=...), take first(), map to DTO."""
        store = TortoiseApiKeyStore()
        row = make_apikey(user_id="u", api_key="LIVE", is_active=True)
        qs = make_qs_chain(result_for_first=row)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        dto = await store.find_by_active_api_key("LIVE", is_active=True)
        assert isinstance(dto, APIKeyResponseDTO)
        model.filter.assert_called_once_with(api_key="LIVE", is_active=True)
        qs.first.assert_awaited_once()


class TestUpdateLastUsedById:
    @pytest.mark.asyncio
    async def test_blank_id_returns_minus1(self, monkeypatch):
        """Blank id -> -1 and zero DB calls."""
        store = TortoiseApiKeyStore()
        model = MagicMock()
        monkeypatch.setattr(store, "model", model)
        assert await store.update_last_used_by_id("") == -1
        assert await store.update_last_used_by_id("   ") == -1
        model.filter.assert_not_called()

    @pytest.mark.asyncio
    async def test_sets_utc_timestamp_exactly(self, freeze_repo_time, monkeypatch):
        """
        Should call filter(id=...) then update(last_used_at=<our frozen UTC time>).
        We freeze time inside the repo so the value is exact, not "close".
        """
        store = TortoiseApiKeyStore()

        qs = make_qs_chain(update_value=1)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        changed = await store.update_last_used_by_id("abc")
        assert changed == 1

        model.filter.assert_called_once_with(id="abc")
        kwargs = qs.update.call_args.kwargs
        assert kwargs.get("last_used_at") == freeze_repo_time  # exact match