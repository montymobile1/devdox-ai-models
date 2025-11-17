import datetime
import uuid

import pytest

from models_src.dto.api_key import APIKeyResponseDTO
from models_src.repositories.api_key import BeanieApiKeyBackend
from test.conftest import _make_api_key_request


@pytest.mark.asyncio
class TestBeanieApiKeyBackend:
    
    beanie_store = BeanieApiKeyBackend
    
    async def test_save_and_get_by_active_api_key(self, db_client):
        # Arrange
        req = _make_api_key_request(
            user_id="user-save",
            api_key="hash-save-1",
            masked_api_key="****save1",
            is_active=True,
        )

        # Act
        saved = await self.beanie_store().save(req)

        # Assert basic properties
        assert isinstance(saved, APIKeyResponseDTO)
        assert saved.id is not None
        assert isinstance(saved.id, uuid.UUID)
        assert saved.user_id == req.user_id
        assert saved.api_key == req.api_key
        assert saved.masked_api_key == req.masked_api_key
        assert saved.is_active is True
        assert isinstance(saved.created_at, datetime.datetime)

        # And we can fetch it back by active api key
        fetched = await self.beanie_store().find_by_active_api_key("hash-save-1")
        assert fetched is not None
        assert fetched.id == saved.id

    async def test_exists_by_hash_key_true_and_false(self, db_client):
        # Arrange
        req = _make_api_key_request(
            user_id="user-exists",
            api_key="hash-exists",
            masked_api_key="****exists",
            is_active=True,
        )
        await self.beanie_store().save(req)

        # Act / Assert
        assert await self.beanie_store().exists_by_hash_key("hash-exists") is True
        assert await self.beanie_store().exists_by_hash_key("hash-missing") is False

    async def test_count_by_user_id_counts_only_active(self, db_client):
        # Arrange
        user_id = "user-count"

        # 2 active for target user
        await self.beanie_store().save(
            _make_api_key_request(user_id=user_id, api_key="hash-active-1", masked_api_key="****a1", is_active=True)
        )
        await self.beanie_store().save(
            _make_api_key_request(user_id=user_id, api_key="hash-active-2", masked_api_key="****a2", is_active=True)
        )

        # 1 inactive for same user
        await self.beanie_store().save(
            _make_api_key_request(user_id=user_id, api_key="hash-inactive", masked_api_key="****i", is_active=False)
        )

        # 1 active for other user
        await self.beanie_store().save(
            _make_api_key_request(user_id="other-user", api_key="hash-other", masked_api_key="****o", is_active=True)
        )

        # Act
        count = await self.beanie_store().count_by_user_id(user_id)

        # Assert
        assert count == 2

    async def test_find_all_by_user_id_pagination(self, db_client):
        """
        Verifies:
        - Only active keys are returned
        - Pagination via (offset, limit) works as page-based: skip = offset * limit
        We don't rely on exact order, just counts + membership.
        """
        user_id = "user-find-all"

        saved1 = await self.beanie_store().save(
            _make_api_key_request(user_id=user_id, api_key="hash-fa-1", masked_api_key="****fa1", is_active=True)
        )
        saved2 = await self.beanie_store().save(
            _make_api_key_request(user_id=user_id, api_key="hash-fa-2", masked_api_key="****fa2", is_active=True)
        )
        saved3 = await self.beanie_store().save(
            _make_api_key_request(user_id=user_id, api_key="hash-fa-3", masked_api_key="****fa3", is_active=True)
        )

        # inactive – should never show up
        await self.beanie_store().save(
            _make_api_key_request(user_id=user_id, api_key="hash-fa-inactive", masked_api_key="****fai", is_active=False)
        )

        # Act: page 0 (offset=0, limit=2)
        page0 = await self.beanie_store().find_all_by_user_id(offset=0, limit=2, user_id=user_id)
        # Act: page 1 (offset=1, limit=2)
        page1 = await self.beanie_store().find_all_by_user_id(offset=1, limit=2, user_id=user_id)

        # Assert
        assert len(page0) == 2
        assert len(page1) == 1

        # Combine and check we got all 3 active ones, no duplicates
        got_ids = {k.id for k in page0 + page1}
        expected_ids = {saved1.id, saved2.id, saved3.id}
        assert got_ids == expected_ids

    async def test_find_by_active_api_key_respects_is_active(self, db_client):
        user_id = "user-find-by-hash"

        active = await self.beanie_store().save(
            _make_api_key_request(user_id=user_id, api_key="hash-active", masked_api_key="****ha", is_active=True)
        )
        inactive = await self.beanie_store().save(
            _make_api_key_request(user_id=user_id, api_key="hash-inactive", masked_api_key="****hi", is_active=False)
        )

        # Default (is_active=True) finds only active
        found_active = await self.beanie_store().find_by_active_api_key("hash-active")
        assert found_active is not None
        assert found_active.id == active.id
        assert found_active.is_active is True

        assert await self.beanie_store().find_by_active_api_key("hash-inactive") is None

        # Explicit is_active=False finds the inactive one
        found_inactive = await self.beanie_store().find_by_active_api_key("hash-inactive", is_active=False)
        assert found_inactive is not None
        assert found_inactive.id == inactive.id
        assert found_inactive.is_active is False

    async def test_update_is_active_by_user_id_and_api_key_id(self, db_client):
        user_id = "user-update-active"

        saved = await self.beanie_store().save(
            _make_api_key_request(user_id=user_id, api_key="hash-update", masked_api_key="****upd", is_active=True)
        )

        # Act: deactivate
        updated_count = await self.beanie_store().update_is_active_by_user_id_and_api_key_id(
            user_id=user_id,
            api_key_id=saved.id,
            is_active=False,
        )

        assert updated_count == 1

        # Now it should not be found as active
        assert await self.beanie_store().find_by_active_api_key("hash-update") is None

        # But found as inactive
        inactive = await self.beanie_store().find_by_active_api_key("hash-update", is_active=False)
        assert inactive is not None
        assert inactive.is_active is False

        # Calling again with same values should be a no-op
        updated_count_again = await self.beanie_store().update_is_active_by_user_id_and_api_key_id(
            user_id=user_id,
            api_key_id=saved.id,
            is_active=False,
        )
        assert updated_count_again == 0

    async def test_update_last_used_by_id_with_explicit_timestamp(self, db_client):
        user_id = "user-last-used-explicit"

        saved = await self.beanie_store().save(
            _make_api_key_request(user_id=user_id, api_key="hash-last-specific", masked_api_key="****ls", is_active=True)
        )

        assert saved.last_used_at is None

        fixed_time = datetime.datetime(2020, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)

        # Act
        updated_count = await self.beanie_store().update_last_used_by_id(id=str(saved.id), last_used_at=fixed_time)

        assert updated_count == 1

        refreshed = await self.beanie_store().find_by_active_api_key("hash-last-specific", is_active=True)
        assert refreshed is not None
        assert refreshed.last_used_at.date() == fixed_time.date()

    async def test_update_last_used_by_id_sets_now_when_not_provided(self, db_client):
        user_id = "user-last-used-auto"

        saved = await self.beanie_store().save(
            _make_api_key_request(user_id=user_id, api_key="hash-last-auto", masked_api_key="****la", is_active=True)
        )

        assert saved.last_used_at is None

        # Act
        updated_count = await self.beanie_store().update_last_used_by_id(id=str(saved.id), last_used_at=None)
        assert updated_count == 1

        refreshed = await self.beanie_store().find_by_active_api_key("hash-last-auto", is_active=True)
        assert refreshed is not None
        assert isinstance(refreshed.last_used_at, datetime.datetime)

    async def test_update_last_used_by_id_returns_zero_for_missing_id(self, db_client):
        missing_id = str(uuid.uuid4())

        updated_count = await self.beanie_store().update_last_used_by_id(
            id=missing_id,
            last_used_at=datetime.datetime.now(datetime.timezone.utc),
        )

        assert updated_count == 0