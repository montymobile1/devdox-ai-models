import datetime
import uuid

import pytest

from models_src.dto.user import UserRequestDTO
from models_src.test_doubles.repositories.user import (
    FakeUserStore,
    make_fake_user, StubUserStore,
)

@pytest.mark.asyncio
class TestFakeUserStore:
    
    async def test_set_fake_data_populates_store_and_count(self):
        store = FakeUserStore()
        u1 = make_fake_user(user_id="u1")
        u2 = make_fake_user(user_id="u2")
    
        store.set_fake_data([u1, u2])
    
        assert store.total_count == 2
        assert store._FakeUserStore__get_data_store("u1") is u1
        assert store._FakeUserStore__get_data_store("u2") is u2
    
    async def test_exists_by_user_id(self):
        store = FakeUserStore()
        u1 = make_fake_user(user_id="u1")
        u2 = make_fake_user(user_id="u2")
        
        store.set_fake_data([u1, u2])
        
        exist = await store.exists_by_user_id(user_id=u1.user_id)
        not_exist = await store.exists_by_user_id(user_id="does not exist user_id")
        
        assert exist
        assert not not_exist
    
    
    async def test_save_assigns_id_created_at_and_inserts(self):
        store = FakeUserStore()
        req = UserRequestDTO(
            user_id="u1",
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            role="admin",
        )
    
        saved = await store.save(req)
    
        assert isinstance(saved.id, uuid.UUID)
        assert isinstance(saved.created_at, datetime.datetime)
        assert store.total_count == 1
        assert store._FakeUserStore__get_data_store("u1") is saved
    
    
    async def test_find_by_user_id_happy_and_invalid_inputs(self):
        store = FakeUserStore()
        u = make_fake_user(user_id="u1")
        store.set_fake_data([u])
    
        found = await store.find_by_user_id("u1")
        assert found is u
    
        # invalid inputs
        assert await store.find_by_user_id("") is None
        assert await store.find_by_user_id("   ") is None
    
    
    async def test_increment_token_usage_updates_when_present(self):
        store = FakeUserStore()
        u = make_fake_user(user_id="u1")
        u.token_used = 3
        store.set_fake_data([u])
    
        updated = await store.increment_token_usage("u1", 5)
    
        assert updated == 1
        assert u.token_used == 8
    
    
    async def test_increment_token_usage_validation_and_not_found(self):
        store = FakeUserStore()
    
        # validations (empty id or zero tokens)
        assert (await store.increment_token_usage("", 1)) == -1
        assert (await store.increment_token_usage("u1", 0)) == -1
    
        # not found
        assert (await store.increment_token_usage("u-missing", 2)) == 0
    
    
    async def test_saving_same_user_twice_does_not_duplicate_mapping_and_highlights_count_semantics(self):
        """
        The current Fake uses a dict keyed by user_id and setdefault, so saving the same user twice
        will keep a single mapping but increments total_count twice. This test documents the behavior
        so regressions or desired changes can be made explicitly.
        """
        store = FakeUserStore()
        req = UserRequestDTO(
            user_id="u1", first_name="A", last_name="B", email="e@x", role="user"
        )
    
        first = await store.save(req)
        second = await store.save(req)
    
        # Mapping remains one entry
        assert store._FakeUserStore__get_data_store("u1") is first or store._FakeUserStore__get_data_store("u1") is second
    
        # total_count increments on each save (may diverge from len(dict)); keep as a guardrail for intent
        assert store.total_count == 2

@pytest.mark.asyncio
class TestStubUserStore:
    
    async def test_received_calls(self):
        store = StubUserStore()
        
        store.set_output(
            store.save, None
        )
        
        store.set_output(
            store.find_by_user_id, None
        )
        
        store.set_output(
            store.increment_token_usage, None
        )
        
        store.set_output(
            store.exists_by_user_id, None
        )
        
        _ = await store.save(
            UserRequestDTO(user_id="u1", first_name="first_name", last_name="last_name", email="email", role="user")
        )
        
        _ = await store.find_by_user_id(user_id="user_id")
        
        _ = await store.increment_token_usage(user_id="user_id", tokens_used=10)
        
        _ = await store.exists_by_user_id(user_id="user_id")
        
        assert store.received_calls == [
            ('save', (), {'user_model': UserRequestDTO(user_id='u1', first_name='first_name', last_name='last_name', email='email', role='user', username='', active=True, membership_level='free', token_limit=0, token_used=0, encryption_salt='0')}),
            ('find_by_user_id', (), {'user_id': 'user_id'}),
            ('increment_token_usage', (), {'tokens_used': 10, 'user_id': 'user_id'}),
            ('exists_by_user_id', (), {'user_id': 'user_id'})
        ]
    
    async def test_set_exception(self):
        store = StubUserStore()
        
        store.set_exception(
            store.save, Exception("BOOOM Save!!!")
        )
        
        store.set_exception(
            store.find_by_user_id, Exception("BOOOM find_by_user_id!!!")
        )
        
        store.set_exception(
            store.increment_token_usage, Exception("BOOOM increment_token_usage!!!")
        )
        
        store.set_exception(
            store.exists_by_user_id, Exception("BOOOM exists_by_user_id!!!")
        )
        
        with pytest.raises(Exception):
            _ = await store.save(
                UserRequestDTO(user_id="u1", first_name="first_name", last_name="last_name", email="email", role="user")
            )
        
        with pytest.raises(Exception):
            _ = await store.find_by_user_id(user_id="user_id")
        
        with pytest.raises(Exception):
            _ = await store.increment_token_usage(user_id="user_id", tokens_used=10)
        
        with pytest.raises(Exception):
            _ = await store.exists_by_user_id(user_id="user_id")
