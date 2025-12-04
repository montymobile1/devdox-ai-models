import asyncio
import datetime
import uuid

import pytest
import pytest_asyncio
from pymongo.errors import DuplicateKeyError
from tortoise.exceptions import IntegrityError

from models_src.dto.user import UserResponseDTO
from models_src.exceptions.local_exception import InMemoryDuplicate
from models_src.repositories.user import (
    BeanieUserBackend, InMemoryUserBackend, IUserStore, TortoiseUserBackend,
)
from test.conftest import _make_user_request

# All backends should raise one of these when user_id uniqueness is violated.
UNIQUE_EXCEPTIONS = (DuplicateKeyError, IntegrityError, InMemoryDuplicate)


class TestUserBackend:
    """
    Common test suite for all IUserStore backends:
    - TortoiseUserBackend
    - BeanieUserBackend
    - InMemoryUserBackend
    """
    __test__ = False

    @pytest_asyncio.fixture
    async def repo(self) -> IUserStore:
        """
        Concrete subclasses must override this to return
        the appropriate repo instance (Mongo, Postgres, or InMemory).
        """
        raise NotImplementedError

    # =================================================================
    # save()
    # =================================================================

    async def test_save_should_create_user_and_set_audit_fields(self, repo: IUserStore):
        """Saving a new user should return a DTO with id and audit fields populated."""
        user_id = "user-save-1"
        req = _make_user_request(user_id=user_id)

        saved = await repo.save(req)

        assert isinstance(saved, UserResponseDTO)
        assert saved.id is not None
        assert isinstance(saved.id, uuid.UUID)

        # Core fields preserved
        assert saved.user_id == req.user_id
        assert saved.first_name == req.first_name
        assert saved.last_name == req.last_name
        assert saved.email == req.email
        assert saved.role == req.role
        assert saved.active == req.active
        assert saved.membership_level == req.membership_level
        assert saved.token_limit == req.token_limit
        assert saved.token_used == req.token_used

        # Audit fields
        assert saved.created_at is not None
        assert saved.updated_at is not None
        assert isinstance(saved.created_at, datetime.datetime)
        assert isinstance(saved.updated_at, datetime.datetime)

        # created_at should not be in the future relative to updated_at
        assert saved.created_at <= saved.updated_at

    async def test_save_should_forbid_second_user_with_same_user_id(self, repo: IUserStore):
        """
        Inserting a second user with the same user_id must fail with a uniqueness-related exception.
        """
        user_id = "user-dup-1"

        req1 = _make_user_request(user_id=user_id)
        req2 = _make_user_request(user_id=user_id)

        await repo.save(req1)

        with pytest.raises(UNIQUE_EXCEPTIONS):
            await repo.save(req2)

    # =================================================================
    # find_by_user_id()
    # =================================================================

    async def test_find_by_user_id_should_return_none_for_unknown_user(self, repo: IUserStore):
        """find_by_user_id should return None when no user exists for the given user_id."""
        result = await repo.find_by_user_id("non-existent-user")
        assert result is None

    async def test_find_by_user_id_should_return_saved_user(self, repo: IUserStore):
        """find_by_user_id should return the previously saved user."""
        user_id = "user-find-1"
        req = _make_user_request(user_id=user_id)

        saved = await repo.save(req)

        found = await repo.find_by_user_id(user_id)

        assert found is not None
        assert isinstance(found, UserResponseDTO)
        assert found.id == saved.id
        assert found.user_id == saved.user_id
        assert found.email == saved.email
        assert found.first_name == saved.first_name
        assert found.last_name == saved.last_name

    # =================================================================
    # exists_by_user_id()
    # =================================================================

    async def test_exists_by_user_id_should_be_false_before_and_true_after_save(self, repo: IUserStore):
        """exists_by_user_id should flip from False to True once the user is saved."""
        user_id = "user-exists-1"

        exists_before = await repo.exists_by_user_id(user_id)
        assert exists_before is False

        req = _make_user_request(user_id=user_id)
        await repo.save(req)

        exists_after = await repo.exists_by_user_id(user_id)
        assert exists_after is True

    # =================================================================
    # increment_token_usage()
    # =================================================================

    async def test_increment_token_usage_should_increment_and_bump_updated_at(self, repo: IUserStore):
        """
        increment_token_usage should:
        - return 1 when a user exists
        - increment token_used
        - keep created_at unchanged
        - bump updated_at forward
        """
        user_id = "user-tokens-1"
        req = _make_user_request(user_id=user_id)
        await repo.save(req)

        before = await repo.find_by_user_id(user_id)
        assert before is not None
        initial_tokens = before.token_used
        initial_created_at = before.created_at
        initial_updated_at = before.updated_at

        # Ensure a measurable time gap so updated_at is strictly greater
        await asyncio.sleep(0.02)

        increment_by = 42
        updated_count = await repo.increment_token_usage(user_id=user_id, tokens_used=increment_by)
        assert updated_count == 1

        after = await repo.find_by_user_id(user_id)
        assert after is not None

        # token_used incremented
        assert after.token_used == initial_tokens + increment_by

        # created_at stable across updates
        assert after.created_at == initial_created_at

        # updated_at strictly moved forward
        assert after.updated_at > initial_updated_at

    async def test_increment_token_usage_should_return_zero_for_unknown_user(self, repo: IUserStore):
        """increment_token_usage should return 0 when the user_id does not exist."""
        updated_count = await repo.increment_token_usage(user_id="does-not-exist", tokens_used=10)
        assert updated_count == 0

@pytest.mark.asyncio
class TestTortoiseUserBackend(TestUserBackend):
    __test__ = True
    
    @pytest_asyncio.fixture
    async def repo(self, postgresql_client):
        return TortoiseUserBackend()

@pytest.mark.asyncio
class TestBeanieUserBackend(TestUserBackend):
    __test__ = True
    
    @pytest_asyncio.fixture
    async def repo(self, db_client):
        return BeanieUserBackend()

@pytest.mark.asyncio
class TestInMemoryUserBackend(TestUserBackend):
    __test__ = True
    
    @pytest_asyncio.fixture
    async def repo(self):
        return InMemoryUserBackend()
