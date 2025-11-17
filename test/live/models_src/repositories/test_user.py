import datetime
import uuid

import pytest

from models_src.dto.user import UserResponseDTO
from models_src.repositories.user import (
    BeanieUserStore,
)
from test.conftest import _make_user_request


@pytest.mark.asyncio
class TestBeanieUserStore:
    beanie_store = BeanieUserStore

    async def test_save_and_find_by_user_id(self, db_client):
        store = self.beanie_store()

        # Arrange
        req = _make_user_request(
            user_id="beanie-user-1",
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            role="admin",
            username="alice",
            token_limit=1000,
            token_used=0,
        )

        # Act
        saved = await store.save(req)

        # Assert saved DTO
        assert isinstance(saved, UserResponseDTO)
        assert isinstance(saved.id, uuid.UUID)
        assert saved.user_id == req.user_id
        assert saved.first_name == req.first_name
        assert saved.last_name == req.last_name
        assert saved.email == req.email
        assert saved.role == req.role
        assert saved.username == req.username
        assert saved.active is True
        assert isinstance(saved.created_at, datetime.datetime)

        # And we can fetch it back by user_id
        fetched = await store.find_by_user_id(req.user_id)
        assert fetched is not None
        assert fetched.id == saved.id

    async def test_increment_token_usage_increments_in_db(self, db_client):
        store = self.beanie_store()

        req = _make_user_request(
            user_id="beanie-user-2",
            first_name="Bob",
            last_name="Jones",
            email="bob@example.com",
            role="user",
            token_limit=500,
            token_used=0,
        )
        saved = await store.save(req)

        # Act
        updated_count = await store.increment_token_usage(
            user_id=req.user_id,
            tokens_used=150,
        )

        assert updated_count == 1

        refreshed = await store.find_by_user_id(req.user_id)
        assert refreshed is not None
        assert refreshed.id == saved.id
        assert refreshed.token_used == 150

    async def test_exists_by_user_id_true_and_false(self, db_client):
        store = self.beanie_store()

        req = _make_user_request(
            user_id="beanie-user-3",
            email="exists@example.com",
            role="user",
        )
        await store.save(req)

        assert await store.exists_by_user_id("beanie-user-3") is True
        assert await store.exists_by_user_id("missing-user") is False