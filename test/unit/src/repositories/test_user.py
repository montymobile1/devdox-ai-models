import pytest
from unittest.mock import MagicMock, AsyncMock

from models_src.dto.user import UserRequestDTO, UserResponseDTO
from models_src.repositories.user import TortoiseUserStore
from test.unit.common_test_tools.model_factories import make_user
from test.unit.common_test_tools.qs_chain import make_qs_chain


class TestSave:
    @pytest.mark.asyncio
    async def test_save_returns_dto_with_real_model_instance(self, no_model_io, monkeypatch):
        """Saving a user should call model.create() and return a mapped DTO (no DB)."""
        store = TortoiseUserStore()

        model = MagicMock()
        model.create = AsyncMock(return_value=make_user(user_id="u1", first_name="Alice"))
        monkeypatch.setattr(store, "model", model)

        req = UserRequestDTO(
            user_id="u1", first_name="Alice", last_name="Doe", email="alice@example.com",
            role="member",
        )
        dto = await store.save(req)

        assert isinstance(dto, UserResponseDTO)
        assert dto.user_id == "u1" and dto.first_name == "Alice"
        model.create.assert_awaited_once()


class TestFindByUserId:
    @pytest.mark.asyncio
    async def test_blank_input_returns_none(self, monkeypatch):
        """Blank user_id → None and no DB calls."""
        store = TortoiseUserStore()
        model = MagicMock()
        monkeypatch.setattr(store, "model", model)

        assert await store.find_by_user_id("") is None
        assert await store.find_by_user_id("   ") is None
        model.filter.assert_not_called()

    @pytest.mark.asyncio
    async def test_filters_then_first_then_maps(self, monkeypatch):
        """Filter(user_id=...), first() → mapped DTO."""
        store = TortoiseUserStore()

        row = make_user(user_id="u42", first_name="Bob")
        qs = make_qs_chain(result_for_first=row)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        dto = await store.find_by_user_id("u42")
        assert isinstance(dto, UserResponseDTO)
        assert dto.first_name == "Bob"

        model.filter.assert_called_once_with(user_id="u42")
        qs.first.assert_awaited_once()


class TestIncrementTokenUsage:
    @pytest.mark.asyncio
    async def test_bad_inputs_return_minus1(self, monkeypatch):
        """Blank user_id or tokens_used == 0 → -1 and no DB work."""
        store = TortoiseUserStore()
        model = MagicMock()
        monkeypatch.setattr(store, "model", model)

        assert await store.increment_token_usage("", 5) == -1
        assert await store.increment_token_usage("u1", 0) == -1
        model.filter.assert_not_called()

    @pytest.mark.asyncio
    async def test_happy_path_uses_expression_update(self, monkeypatch):
        """
        Should filter by user_id and call update(token_used=F('token_used') + tokens_used).
        We don't evaluate the F-expression, just assert the key is present.
        """
        store = TortoiseUserStore()

        qs = make_qs_chain(update_value=1)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        changed = await store.increment_token_usage("u9", 7)
        assert changed == 1

        model.filter.assert_called_once_with(user_id="u9")
        qs.update.assert_awaited_once()
        # ensure the expression was passed (we only check the presence of the key)
        kwargs = qs.update.call_args.kwargs
        assert "token_used" in kwargs

    @pytest.mark.asyncio
    async def test_negative_tokens_are_allowed_and_passed_through(self, monkeypatch):
        """
        Negative numbers are truthy, so they'll be forwarded.
        We only verify the call shape (expression present), not ORM internals.
        """
        store = TortoiseUserStore()

        qs = make_qs_chain(update_value=1)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        changed = await store.increment_token_usage("u5", -3)
        assert changed == 1

        model.filter.assert_called_once_with(user_id="u5")
        kwargs = qs.update.call_args.kwargs
        assert "token_used" in kwargs
