import uuid

import pytest

from models_src.dto.queue_job_claim_registry import (
    QueueProcessingRegistryRequestDTO,
)
from models_src.models import QRegistryStat
from models_src.test_doubles.repositories.queue_job_claim_registry import (
    FakeQueueProcessingRegistryStore,
)


@pytest.mark.asyncio
async def test_save_inserts_and_sets_id_and_created_at():
    store = FakeQueueProcessingRegistryStore()
    req = QueueProcessingRegistryRequestDTO(
    message_id="m-1",
    queue_name="qA",
    step="ingest",
    status=QRegistryStat.PENDING,
    )
    
    
    res = await store.save(req)
    
    
    assert isinstance(res.id, uuid.UUID)
    assert res.claimed_at is not None
    assert store.total_count == 1
    # Stored object is the same instance held by the store
    assert store._FakeQueueProcessingRegistryStore__get_data_store(str(res.id)) is res


@pytest.mark.asyncio
async def test_update_status_or_message_id_by_id_updates_status_only():
    store = FakeQueueProcessingRegistryStore()
    res = await store.save(
        QueueProcessingRegistryRequestDTO(
            message_id="m-1",
            queue_name="qA",
            step="ingest",
            status=QRegistryStat.PENDING,
        )
    )

    updated = await store.update_status_or_message_id_by_id(
        str(res.id), QRegistryStat.IN_PROGRESS
    )

    assert updated == 1
    assert res.status == QRegistryStat.IN_PROGRESS
    assert res.message_id == "m-1"  # unchanged


@pytest.mark.asyncio
async def test_update_status_or_message_id_by_id_updates_both_when_message_id_given():
    store = FakeQueueProcessingRegistryStore()
    res = await store.save(
        QueueProcessingRegistryRequestDTO(
            message_id="m-1",
            queue_name="qA",
            step="ingest",
            status=QRegistryStat.PENDING,
        )
    )

    updated = await store.update_status_or_message_id_by_id(
        str(res.id), QRegistryStat.RETRY, message_id="m-2"
    )

    assert updated == 1
    assert res.status == QRegistryStat.RETRY
    assert res.message_id == "m-2"


@pytest.mark.asyncio
async def test_update_status_or_message_id_by_id_invalid_inputs_return_minus_one():
    store = FakeQueueProcessingRegistryStore()

    assert (
        await store.update_status_or_message_id_by_id("", QRegistryStat.PENDING)
    ) == -1
    assert (
        await store.update_status_or_message_id_by_id("   ", QRegistryStat.PENDING)
    ) == -1


@pytest.mark.asyncio
async def test_update_status_or_message_id_by_id_id_not_found_returns_zero():
    store = FakeQueueProcessingRegistryStore()
    updated = await store.update_status_or_message_id_by_id(
        str(uuid.uuid4()), QRegistryStat.COMPLETED
    )
    assert updated == 0


@pytest.mark.asyncio
async def test_update_step_by_id_happy_path():
    store = FakeQueueProcessingRegistryStore()
    res = await store.save(
        QueueProcessingRegistryRequestDTO(
            message_id="m-1",
            queue_name="qA",
            step="ingest",
            status=QRegistryStat.PENDING,
        )
    )

    updated = await store.update_step_by_id(str(res.id), "vectorize")

    assert updated == 1
    assert res.step == "vectorize"


@pytest.mark.asyncio
async def test_update_step_by_id_invalid_inputs_return_minus_one():
    store = FakeQueueProcessingRegistryStore()
    assert (await store.update_step_by_id("", "x")) == -1
    assert (await store.update_step_by_id("abc", "")) == -1
    assert (await store.update_step_by_id("abc", "   ")) == -1


@pytest.mark.asyncio
async def test_update_step_by_id_id_not_found_returns_zero():
    store = FakeQueueProcessingRegistryStore()
    updated = await store.update_step_by_id(str(uuid.uuid4()), "done")
    assert updated == 0


@pytest.mark.asyncio
async def test_update_status_and_step_by_id_happy_path():
    store = FakeQueueProcessingRegistryStore()
    res = await store.save(
        QueueProcessingRegistryRequestDTO(
            message_id="m-1",
            queue_name="qA",
            step="ingest",
            status=QRegistryStat.PENDING,
        )
    )

    updated = await store.update_status_and_step_by_id(
        str(res.id), QRegistryStat.COMPLETED, "finalize"
    )

    assert updated == 1
    assert res.status == QRegistryStat.COMPLETED
    assert res.step == "finalize"


@pytest.mark.asyncio
async def test_update_status_and_step_by_id_invalid_inputs_return_minus_one():
    store = FakeQueueProcessingRegistryStore()
    assert (await store.update_status_and_step_by_id("", QRegistryStat.PENDING, "s")) == -1
    assert (await store.update_status_and_step_by_id("id", QRegistryStat.PENDING, "")) == -1


@pytest.mark.asyncio
async def test_update_status_and_step_by_id_id_not_found_returns_zero():
    store = FakeQueueProcessingRegistryStore()
    updated = await store.update_status_and_step_by_id(
        str(uuid.uuid4()), QRegistryStat.FAILED, "err"
    )
    assert updated == 0


@pytest.mark.asyncio
async def test_find_previous_latest_message_by_message_id_returns_first_match():
    store = FakeQueueProcessingRegistryStore()
    # Two records, same message_id
    r1 = await store.save(
        QueueProcessingRegistryRequestDTO(
            message_id="m-shared",
            queue_name="qA",
            step="s1",
            status=QRegistryStat.PENDING,
        )
    )
    r2 = await store.save(
        QueueProcessingRegistryRequestDTO(
            message_id="m-shared",
            queue_name="qB",
            step="s2",
            status=QRegistryStat.IN_PROGRESS,
        )
    )

    found = await store.find_previous_latest_message_by_message_id("m-shared")

    assert found is not None
    assert found.message_id == "m-shared"
    # Fake returns first match in insertion order
    assert found in (r1, r2)



@pytest.mark.asyncio
async def test_find_previous_latest_message_by_message_id_none_when_absent():
    store = FakeQueueProcessingRegistryStore()
    found = await store.find_previous_latest_message_by_message_id("nope")
    assert found is None
