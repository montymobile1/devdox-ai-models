import datetime
import uuid

import pytest

from models_src.dto.user import UserRequestDTO
from models_src.test_doubles.repositories.user import (
    FakeUserStore,
    make_fake_user,
)


@pytest.mark.asyncio
async def test_set_fake_data_populates_store_and_count():
    store = FakeUserStore()
    u1 = make_fake_user(user_id="u1")
    u2 = make_fake_user(user_id="u2")

    store.set_fake_data([u1, u2])

    assert store.total_count == 2
    assert store._FakeUserStore__get_data_store("u1") is u1
    assert store._FakeUserStore__get_data_store("u2") is u2


@pytest.mark.asyncio
async def test_save_assigns_id_created_at_and_inserts():
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


@pytest.mark.asyncio
async def test_find_by_user_id_happy_and_invalid_inputs():
    store = FakeUserStore()
    u = make_fake_user(user_id="u1")
    store.set_fake_data([u])

    found = await store.find_by_user_id("u1")
    assert found is u

    # invalid inputs
    assert await store.find_by_user_id("") is None
    assert await store.find_by_user_id("   ") is None


@pytest.mark.asyncio
async def test_increment_token_usage_updates_when_present():
    store = FakeUserStore()
    u = make_fake_user(user_id="u1")
    u.token_used = 3
    store.set_fake_data([u])

    updated = await store.increment_token_usage("u1", 5)

    assert updated == 1
    assert u.token_used == 8


@pytest.mark.asyncio
async def test_increment_token_usage_validation_and_not_found():
    store = FakeUserStore()

    # validations (empty id or zero tokens)
    assert (await store.increment_token_usage("", 1)) == -1
    assert (await store.increment_token_usage("u1", 0)) == -1

    # not found
    assert (await store.increment_token_usage("u-missing", 2)) == 0


@pytest.mark.asyncio
async def test_saving_same_user_twice_does_not_duplicate_mapping_and_highlights_count_semantics():
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
