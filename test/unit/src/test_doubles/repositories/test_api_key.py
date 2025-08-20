import datetime
import uuid

import pytest

from models_src.dto.api_key import APIKeyRequestDTO, APIKeyResponseDTO
from models_src.test_doubles.repositories.api_key import FakeApiKeyStore


def make_api_key_response(**kwargs) -> APIKeyResponseDTO:
    now = datetime.datetime.now(datetime.timezone.utc)
    return APIKeyResponseDTO(
        id=uuid.uuid4(),
        user_id=kwargs.get("user_id", "user1"),
        api_key=kwargs.get("api_key", str(uuid.uuid4())),
        masked_api_key=kwargs.get("masked_api_key", "****"),
        is_active=kwargs.get("is_active", True),
        created_at=kwargs.get("created_at", now),
        updated_at=kwargs.get("updated_at", now),
        last_used_at=kwargs.get("last_used_at", None),
    )


@pytest.mark.asyncio
async def test_set_fake_data_populates_store():
    fake = FakeApiKeyStore()
    data = [make_api_key_response(user_id="u1"), make_api_key_response(user_id="u2")]
    fake.set_fake_data(data)

    assert fake.total_count == 2
    assert data[0].api_key in fake.existing_hash_set
    assert data[1].user_id in fake.data_store


@pytest.mark.asyncio
async def test_save_inserts_data_correctly():
    fake = FakeApiKeyStore()
    dto = APIKeyRequestDTO(user_id="u1", api_key="abc123", masked_api_key="***")
    result = await fake.save(dto)

    assert result.id is not None
    assert result.created_at is not None
    assert result.api_key == "abc123"
    assert fake.total_count == 1
    assert "u1" in fake.data_store
    assert any(x.api_key == "abc123" for x in fake.data_store["u1"])


@pytest.mark.asyncio
async def test_exists_by_hash_key_works():
    fake = FakeApiKeyStore()
    dto = make_api_key_response(api_key="exists")
    fake.set_fake_data([dto])

    assert await fake.exists_by_hash_key("exists") is True
    assert await fake.exists_by_hash_key("missing") is False
    assert await fake.exists_by_hash_key("") is False


@pytest.mark.asyncio
async def test_find_all_by_user_id_returns_active_sorted():
    fake = FakeApiKeyStore()
    d1 = make_api_key_response(created_at=datetime.datetime(2022, 1, 1), user_id="u1")
    d2 = make_api_key_response(created_at=datetime.datetime(2023, 1, 1), user_id="u1")
    d3 = make_api_key_response(created_at=datetime.datetime(2021, 1, 1), user_id="u1", is_active=False)
    fake.set_fake_data([d1, d2, d3])

    result = await fake.find_all_by_user_id(offset=0, limit=10, user_id="u1")
    assert result == [d2, d1]  # Only active, sorted desc


@pytest.mark.asyncio
async def test_count_by_user_id_filters_active():
    fake = FakeApiKeyStore()
    fake.set_fake_data([
        make_api_key_response(user_id="u1", is_active=True),
        make_api_key_response(user_id="u1", is_active=False),
        make_api_key_response(user_id="u1", is_active=True),
    ])
    count = await fake.count_by_user_id("u1")
    assert count == 2


@pytest.mark.asyncio
async def test_update_is_active_by_user_id_and_api_key_id_correctly():
    fake = FakeApiKeyStore()
    key = str(uuid.uuid4())
    dto = make_api_key_response(user_id="u1", api_key=key)
    fake.set_fake_data([dto])

    updated = await fake.update_is_active_by_user_id_and_api_key_id("u1", uuid.UUID(key), False)
    assert updated == 1
    assert dto.is_active is False


@pytest.mark.asyncio
async def test_find_first_by_api_key_and_is_active_returns_match():
    fake = FakeApiKeyStore()
    dto = make_api_key_response(api_key="match")
    fake.set_fake_data([dto])

    result = await fake.find_first_by_api_key_and_is_active("match")
    assert result == dto

    result_none = await fake.find_first_by_api_key_and_is_active("missing")
    assert result_none is None


@pytest.mark.asyncio
async def test_update_last_used_by_id_sets_timestamp():
    fake = FakeApiKeyStore()
    dto = make_api_key_response()
    fake.set_fake_data([dto])

    result = await fake.update_last_used_by_id(str(dto.id))
    assert result == 1
    assert dto.last_used_at is not None


@pytest.mark.asyncio
async def test_update_is_active_handles_missing_or_bad_inputs():
    fake = FakeApiKeyStore()
    result = await fake.update_is_active_by_user_id_and_api_key_id("", None, False)
    assert result == -1


@pytest.mark.asyncio
async def test_count_by_user_id_empty_or_invalid():
    fake = FakeApiKeyStore()
    with pytest.raises(Exception):
        await fake.count_by_user_id("")


@pytest.mark.asyncio
async def test_find_all_by_user_id_empty():
    fake = FakeApiKeyStore()
    with pytest.raises(Exception):
        await fake.find_all_by_user_id(0, 10, "")
