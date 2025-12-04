import datetime
import uuid

import pytest
import pytest_asyncio

from models_src.dto.api_key import APIKeyResponseDTO
from models_src.repositories.api_key import BeanieApiKeyBackend, IApiKeyStore, InMemoryApiKeyBackend, \
    TortoiseApiKeyBackend
from test.conftest import _make_api_key_request

class TestApiKeyBackend:
    __test__ = False
    
    @pytest_asyncio.fixture
    async def repo(self) -> IApiKeyStore:
        """
		Concrete subclasses must override this to return
		the appropriate repo instance (Mongo or Postgres).
		"""
        raise NotImplementedError
    
    async def test_save(self, repo):
        # Arrange
        req = _make_api_key_request(
            user_id="user-save",
            api_key="hash-save-1",
            masked_api_key="****save1",
            is_active=True,
        )
        
        # Act
        saved = await repo.save(req)
        
        # Assert basic properties
        assert isinstance(saved, APIKeyResponseDTO)
        
        assert saved.id is not None
        assert isinstance(saved.id, uuid.UUID)
        
        assert isinstance(saved.user_id, str)
        assert saved.user_id == req.user_id
        
        assert isinstance(saved.api_key, str)
        assert saved.api_key == req.api_key
        
        assert isinstance(saved.masked_api_key, str)
        assert saved.masked_api_key == req.masked_api_key
        
        assert isinstance(saved.is_active, bool)
        assert saved.is_active is req.is_active
        
        assert saved.created_at is not None
        assert isinstance(saved.created_at, datetime.datetime)
        
        assert saved.updated_at is not None
        assert isinstance(saved.updated_at, datetime.datetime)
        
        assert not saved.last_used_at
        
        fetched = await repo.find_all()
        
        assert fetched is not None
        
        found_api_key = None
        for api_key in fetched:
            if api_key.id == saved.id:
                found_api_key = api_key
                break
        
        assert found_api_key
        assert isinstance(found_api_key, APIKeyResponseDTO)
        
        assert isinstance(found_api_key.id, uuid.UUID)
        
        assert isinstance(found_api_key.user_id, str)
        assert found_api_key.user_id == saved.user_id
        
        assert isinstance(found_api_key.api_key, str)
        assert found_api_key.api_key == saved.api_key
        
        assert isinstance(found_api_key.masked_api_key, str)
        assert found_api_key.masked_api_key == saved.masked_api_key
        
        assert isinstance(found_api_key.is_active, bool)
        assert found_api_key.is_active is saved.is_active
        
        assert found_api_key.created_at is not None
        assert isinstance(found_api_key.created_at, datetime.datetime)
        
        assert found_api_key.updated_at is not None
        assert isinstance(found_api_key.updated_at, datetime.datetime)
        
        assert not found_api_key.last_used_at
    
    # --------------------------------------------------
    # find_all_by_user_id
    # --------------------------------------------------
    async def test_find_all_by_user_id_returns_only_active_records_for_given_user(
        self,
        repo: IApiKeyStore,
    ):
        # Arrange: 2 active + 1 inactive for target user, 1 active for other user
        req1 = _make_api_key_request(
            user_id="user-find",
            api_key="hash-find-1",
            masked_api_key="****find1",
            is_active=True,
        )
        req2 = _make_api_key_request(
            user_id="user-find",
            api_key="hash-find-2",
            masked_api_key="****find2",
            is_active=True,
        )
        req_inactive = _make_api_key_request(
            user_id="user-find",
            api_key="hash-find-inactive",
            masked_api_key="****findX",
            is_active=False,
        )
        req_other = _make_api_key_request(
            user_id="other-user",
            api_key="hash-other-1",
            masked_api_key="****other1",
            is_active=True,
        )

        await repo.save(req1)
        await repo.save(req2)
        await repo.save(req_inactive)
        await repo.save(req_other)

        # Act
        result = await repo.find_all_by_user_id(
            offset=0,
            limit=10,
            user_id="user-find",
        )

        # Assert
        assert isinstance(result, list)
        assert len(result) == 2  # two active keys for this user

        api_keys = {item.api_key for item in result}

        for item in result:
            assert isinstance(item, APIKeyResponseDTO)
            assert isinstance(item.id, uuid.UUID)
            assert isinstance(item.user_id, str)
            assert isinstance(item.api_key, str)
            assert isinstance(item.masked_api_key, str)
            assert isinstance(item.is_active, bool)
            assert isinstance(item.created_at, datetime.datetime)
            assert isinstance(item.updated_at, datetime.datetime)

            assert item.user_id == "user-find"
            assert item.is_active is True
            assert item.api_key in {"hash-find-1", "hash-find-2"}
            assert item.masked_api_key in {"****find1", "****find2"}
            assert item.last_used_at is None

        # Ensure excluded keys really are excluded
        assert "hash-find-inactive" not in api_keys
        assert "hash-other-1" not in api_keys

        # Optional: ordering (newest first)
        if len(result) == 2:
            assert result[0].created_at >= result[1].created_at
    
    async def test_find_all_by_user_id_returns_empty_list_for_user_with_no_keys(self, repo: IApiKeyStore):
        result = await repo.find_all_by_user_id(offset=0, limit=10, user_id="non-existent-user")
        assert result == []
    
    async def test_find_all_by_user_id_applies_offset_and_limit(self, repo: IApiKeyStore):
        # create 3 keys for the same user
        for i in range(3):
            await repo.save(
                _make_api_key_request(
                    user_id="user-page",
                    api_key=f"hash-page-{i}",
                    masked_api_key=f"****page{i}",
                    is_active=True,
                )
            )
        
        # page 2 (offset=1, limit=1) => expect the "middle" item
        page = await repo.find_all_by_user_id(offset=1, limit=1, user_id="user-page")
        
        assert len(page) == 1
        assert isinstance(page[0], APIKeyResponseDTO)
    
    # --------------------------------------------------
    # count_by_user_id
    # --------------------------------------------------
    async def test_count_by_user_id_counts_only_active_keys_for_user(
        self,
        repo: IApiKeyStore,
    ):
        # Arrange: 2 active + 1 inactive for user-count, 1 active for other user
        await repo.save(
            _make_api_key_request(
                user_id="user-count",
                api_key="hash-count-1",
                masked_api_key="****count1",
                is_active=True,
            )
        )
        await repo.save(
            _make_api_key_request(
                user_id="user-count",
                api_key="hash-count-2",
                masked_api_key="****count2",
                is_active=True,
            )
        )
        await repo.save(
            _make_api_key_request(
                user_id="user-count",
                api_key="hash-count-inactive",
                masked_api_key="****countX",
                is_active=False,
            )
        )
        await repo.save(
            _make_api_key_request(
                user_id="other-user-count",
                api_key="hash-count-other",
                masked_api_key="****other",
                is_active=True,
            )
        )

        # Act
        count = await repo.count_by_user_id("user-count")

        # Assert
        assert isinstance(count, int)
        assert count == 2  # only active keys for that user
    
    async def test_count_by_user_id_returns_zero_for_user_with_no_keys(self, repo: IApiKeyStore):
        count = await repo.count_by_user_id("no-such-user")
        assert isinstance(count, int)
        assert count == 0
    
    # --------------------------------------------------
    # exists_by_hash_key
    # --------------------------------------------------
    async def test_exists_by_hash_key_returns_true_for_existing_and_false_for_missing(
        self,
        repo: IApiKeyStore,
    ):
        # Arrange
        await repo.save(
            _make_api_key_request(
                user_id="user-exists",
                api_key="hash-exists-1",
                masked_api_key="****exists1",
                is_active=True,
            )
        )
        
        await repo.save(
            _make_api_key_request(
                user_id="user-exists-inactive",
                api_key="hash-inactive-exists",
                masked_api_key="****iexists",
                is_active=False,
            )
        )
        
        # Act
        exists = await repo.exists_by_hash_key("hash-exists-1")
        exists_but_inactive = await repo.exists_by_hash_key("hash-inactive-exists")
        not_exists = await repo.exists_by_hash_key("hash-exists-2")
        
        # Assert
        assert isinstance(exists, bool)
        assert isinstance(exists_but_inactive, bool)
        assert isinstance(not_exists, bool)

        assert exists is True
        assert exists_but_inactive is True
        assert not_exists is False

    # --------------------------------------------------
    # update_is_active_by_user_id_and_api_key_id
    # --------------------------------------------------
    async def test_update_is_active_by_user_id_and_api_key_id_deactivates_only_matching_key(
        self,
        repo: IApiKeyStore,
    ):
        # Arrange: two keys for same user, one for another user
        target_req = _make_api_key_request(
            user_id="user-update",
            api_key="hash-update-1",
            masked_api_key="****update1",
            is_active=True,
        )
        other_same_user_req = _make_api_key_request(
            user_id="user-update",
            api_key="hash-update-2",
            masked_api_key="****update2",
            is_active=True,
        )
        other_user_req = _make_api_key_request(
            user_id="other-user-update",
            api_key="hash-update-3",
            masked_api_key="****update3",
            is_active=True,
        )

        saved_target = await repo.save(target_req)
        saved_other_same_user = await repo.save(other_same_user_req)
        await repo.save(other_user_req)

        # Act: deactivate only the target key
        updated_count = await repo.update_is_active_by_user_id_and_api_key_id(
            user_id="user-update",
            api_key_id=saved_target.id,
            is_active=False,
        )

        # Assert: exactly one row updated
        assert isinstance(updated_count, int)
        assert updated_count == 1

        # Verify only the other key for that user remains active
        user_keys = await repo.find_all_by_user_id(
            offset=0,
            limit=10,
            user_id="user-update",
        )
        assert isinstance(user_keys, list)

        active_ids = {k.id for k in user_keys}
        assert saved_other_same_user.id in active_ids
        assert saved_target.id not in active_ids
    
    async def test_update_is_active_by_user_id_and_api_key_id_returns_zero_when_key_already_inactive(self, repo: IApiKeyStore):
        saved = await repo.save(
            _make_api_key_request(
                user_id="user-update-inactive",
                api_key="hash-update-inactive",
                masked_api_key="****u-inactive",
                is_active=False,
            )
        )
        
        updated = await repo.update_is_active_by_user_id_and_api_key_id(
            user_id="user-update-inactive",
            api_key_id=saved.id,
            is_active=False,
        )
        
        assert updated == 0
    
    async def test_update_is_active_by_user_id_and_api_key_id_does_not_touch_other_users(self, repo: IApiKeyStore):
        saved = await repo.save(
            _make_api_key_request(
                user_id="user-update-owner",
                api_key="hash-update-owner",
                masked_api_key="****owner",
                is_active=True,
            )
        )
        await repo.save(
            _make_api_key_request(
                user_id="other-user-owner",
                api_key="hash-update-other",
                masked_api_key="****other",
                is_active=True,
            )
        )
        
        updated = await repo.update_is_active_by_user_id_and_api_key_id(
            user_id="totally-wrong-user",
            api_key_id=saved.id,
            is_active=False,
        )
        assert updated == 0
        
        # owner key should still be active
        found = await repo.find_by_active_api_key("hash-update-owner", is_active=True)
        assert found is not None
    
    # --------------------------------------------------
    # find_by_active_api_key
    # --------------------------------------------------
    async def test_find_by_active_api_key_respects_is_active_flag(
        self,
        repo: IApiKeyStore,
    ):
        # Arrange: one active, one inactive with different hashes
        active_req = _make_api_key_request(
            user_id="user-find-active",
            api_key="hash-active",
            masked_api_key="****active",
            is_active=True,
        )
        inactive_req = _make_api_key_request(
            user_id="user-find-active",
            api_key="hash-inactive",
            masked_api_key="****inactive",
            is_active=False,
        )

        saved_active = await repo.save(active_req)
        saved_inactive = await repo.save(inactive_req)

        # Act
        found_active = await repo.find_by_active_api_key(
            api_key="hash-active",
            is_active=True,
        )
        found_inactive_as_active = await repo.find_by_active_api_key(
            api_key="hash-inactive",
            is_active=True,
        )
        found_inactive = await repo.find_by_active_api_key(
            api_key="hash-inactive",
            is_active=False,
        )

        # Assert: active lookup
        assert isinstance(found_active, APIKeyResponseDTO)
        assert found_active.id == saved_active.id
        assert found_active.user_id == saved_active.user_id
        assert found_active.api_key == "hash-active"
        assert found_active.is_active is True

        # Assert: inactive should not be returned when is_active=True
        assert found_inactive_as_active is None

        # Assert: but should be returned when is_active=False
        assert isinstance(found_inactive, APIKeyResponseDTO)
        assert found_inactive.id == saved_inactive.id
        assert found_inactive.is_active is False
    
    async def test_find_by_active_api_key_returns_none_for_missing_key(self, repo: IApiKeyStore):
        result = await repo.find_by_active_api_key("non-existent-hash", is_active=True)
        assert result is None
    
    # --------------------------------------------------
    # update_last_used_by_id
    # --------------------------------------------------
    async def test_update_last_used_by_id_sets_last_used_timestamp_for_existing_key(
        self,
        repo: IApiKeyStore,
    ):
        # Arrange
        req = _make_api_key_request(
            user_id="user-last-used",
            api_key="hash-last-used",
            masked_api_key="****lastused",
            is_active=True,
        )
        saved = await repo.save(req)

        # sanity: initial last_used_at should be None
        assert saved.last_used_at is None

        fixed_time = datetime.datetime(
            2024,
            1,
            1,
            12,
            0,
            0,
            tzinfo=datetime.timezone.utc,
        )

        # Act
        updated_count = await repo.update_last_used_by_id(
            id=str(saved.id),
            last_used_at=fixed_time,
        )

        # Assert updated count
        assert isinstance(updated_count, int)
        assert updated_count == 1

        # Fetch again via API key lookup
        fetched = await repo.find_by_active_api_key(
            api_key="hash-last-used",
            is_active=True,
        )

        assert isinstance(fetched, APIKeyResponseDTO)
        assert fetched.id == saved.id
        assert fetched.user_id == saved.user_id
        assert fetched.api_key == saved.api_key
        assert fetched.is_active is True
        
        assert isinstance(fetched.last_used_at, datetime.datetime)
        assert fetched.last_used_at.date() == fixed_time.date()
        
        assert fetched.updated_at
        assert isinstance(fetched.updated_at, datetime.datetime)
        
    
    async def test_update_last_used_by_id_returns_zero_for_unknown_id(self, repo: IApiKeyStore):
        updated = await repo.update_last_used_by_id(id=str(uuid.uuid4()), last_used_at=datetime.datetime.now(datetime.timezone.utc))
        assert updated == 0
    
    
    async def test_update_last_used_by_id_uses_current_time_when_last_used_at_is_none(self, repo: IApiKeyStore):
        req = _make_api_key_request(
            user_id="user-last-used-none",
            api_key="hash-last-used-none",
            masked_api_key="****lastnone",
            is_active=True,
        )
        saved = await repo.save(req)
        
        updated = await repo.update_last_used_by_id(id=str(saved.id), last_used_at=None)
        
        assert updated == 1
        
        fetched = await repo.find_by_active_api_key("hash-last-used-none", is_active=True)
        assert fetched is not None
        assert fetched.last_used_at is not None

@pytest.mark.asyncio
class TestTortoiseApiKeyBackend(TestApiKeyBackend):
    __test__ = True
    
    @pytest_asyncio.fixture
    async def repo(self, postgresql_client):
        return TortoiseApiKeyBackend()

@pytest.mark.asyncio
class TestBeanieApiKeyBackend(TestApiKeyBackend):
    __test__ = True
    
    @pytest_asyncio.fixture
    async def repo(self, db_client):
        return BeanieApiKeyBackend()

@pytest.mark.asyncio
class TestInMemoryApiKeyBackend(TestApiKeyBackend):
    __test__ = True
    
    @pytest_asyncio.fixture
    async def repo(self):
        return InMemoryApiKeyBackend()