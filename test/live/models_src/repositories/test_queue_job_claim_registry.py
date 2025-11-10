import asyncio
import datetime
import uuid

import pytest
from pymongo.errors import DuplicateKeyError

from models_src.dto.queue_job_claim_registry import QueueProcessingRegistryRequestDTO
from models_src.exceptions.local_exception import JobAlreadyClaimed
from models_src.models import QRegistryStat
from models_src.repositories.queue_job_claim_registry import BeanieQueueProcessingRegistryStore


store = BeanieQueueProcessingRegistryStore


@pytest.mark.asyncio
async def test_repo_save_inserts_and_maps(db_client):

    repo = store()
    
    start_of_day = datetime.datetime.combine(datetime.datetime.now(tz=datetime.timezone.utc).date(), datetime.time.min)
    
    req = QueueProcessingRegistryRequestDTO(
	    message_id="24",
        queue_name="processing",
        step="audit_notifications",
        status=QRegistryStat.IN_PROGRESS,
        claimed_by="worker-1",
        previous_message_id=None,
        claimed_at=start_of_day,
        updated_at=start_of_day
    )
    
    dto = await repo.save(req)
    
    in_db = await repo.model.find_one(repo.model.id == dto.id)
    
    assert in_db is not None
    assert in_db.message_id == req.message_id
    assert in_db.queue_name == req.queue_name
    assert in_db.step == req.step
    assert in_db.status == req.status
    assert in_db.claimed_by == req.claimed_by
    assert in_db.previous_message_id == req.previous_message_id
    assert in_db.claimed_at == req.claimed_at
    assert in_db.created_at.date() == start_of_day.date()
    assert in_db.updated_at == start_of_day

@pytest.mark.asyncio
async def test_repo_save_inserts_concurrently_one_claims_one_fails(db_client):
    """In this test I will check whether the unique rule is working or not, where it only allows for one to be inserted while the other should return an erro"""
    repo = store()
    
    start_of_day = datetime.datetime.combine(datetime.datetime.now(tz=datetime.timezone.utc).date(), datetime.time.min)
    
    req = QueueProcessingRegistryRequestDTO(
        message_id="24",
        queue_name="processing",
        step="audit_notifications",
        status=QRegistryStat.IN_PROGRESS,
        claimed_by="worker-1",
        previous_message_id=None,
        claimed_at=start_of_day,
        updated_at=start_of_day
    )
    
    
    ok_result, already_claimed_result = await asyncio.gather(
        repo.save(req),
        repo.save(req),
        return_exceptions=True,
    )
    
    assert already_claimed_result.error_type == JobAlreadyClaimed().error_type
    assert ok_result.id
    
    in_db = await repo.model.find(repo.model.message_id == req.message_id).to_list()
    
    assert len(in_db) == 1
    assert in_db[0].message_id == req.message_id
    assert in_db[0].queue_name == req.queue_name
    assert in_db[0].step == req.step
    assert in_db[0].status == req.status
    assert in_db[0].claimed_by == req.claimed_by
    assert in_db[0].previous_message_id == req.previous_message_id
    assert in_db[0].claimed_at == req.claimed_at
    assert in_db[0].created_at.date() == start_of_day.date()
    assert in_db[0].updated_at == start_of_day

@pytest.mark.asyncio
async def test_update_status_or_message_id_variants_and_edge_cases(db_client):

    repo = store()

    # Insert one document
    d = repo.model(
        id=uuid.uuid4(),
        message_id="m-1",
        queue_name="q1",
        step="init",
        status=QRegistryStat.PENDING,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
    )
    await repo.model.insert_many([d])

    # 1) Update only status
    matched = await repo.update_status_or_message_id_by_id(
        id=str(d.id), status=QRegistryStat.IN_PROGRESS
    )
    assert matched == 1
    in_db = await repo.model.find_one(repo.model.id == d.id)
    assert in_db.status == QRegistryStat.IN_PROGRESS
    assert in_db.message_id == "m-1"

    # 2) Update message_id too
    matched2 = await repo.update_status_or_message_id_by_id(
        id=str(d.id), status=QRegistryStat.IN_PROGRESS, message_id="m-1b"
    )
    assert matched2 == 1
    in_db2 = await repo.model.find_one(repo.model.id == d.id)
    assert in_db2.message_id == "m-1b"
    assert in_db2.status == QRegistryStat.IN_PROGRESS

    # 3) id not found -> 0
    matched3 = await repo.update_status_or_message_id_by_id(
        id=str(uuid.uuid4()), status=QRegistryStat.RETRY
    )
    assert matched3 == 0

    # 4) blank/invalid -> -1
    assert await repo.update_status_or_message_id_by_id("", QRegistryStat.RETRY) == -1
    assert await repo.update_status_or_message_id_by_id("   ", QRegistryStat.RETRY) == -1
    assert await repo.update_status_or_message_id_by_id("not-a-uuid", QRegistryStat.RETRY) == -1

    # 5) partial-unique index collision case (special)
    #    Insert a second doc with a different message_id but PENDING,
    #    then try to change its message_id to collide with the first doc (also PENDING/IN_PROGRESS).
    d2 = repo.model(
        id=uuid.uuid4(),
        message_id="m-2",
        queue_name="q1",
        step="init",
        status=QRegistryStat.PENDING,  # still in partial unique set
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
    )
    await repo.model.insert_many([d2])

    # Turn the first doc back to PENDING so both will be in the restricted set.
    _ = await repo.update_status_or_message_id_by_id(str(d.id), QRegistryStat.PENDING)

    # Now changing d2.message_id -> "m-1b" should violate the unique partial index.
    with pytest.raises(DuplicateKeyError):
        await repo.update_status_or_message_id_by_id(str(d2.id), QRegistryStat.PENDING, message_id="m-1b")

@pytest.mark.asyncio
async def test_update_status_and_step_by_id(db_client):

    repo = store()

    d = repo.model(
        id=uuid.uuid4(),
        message_id="m-9",
        queue_name="qZ",
        step="start",
        status=QRegistryStat.PENDING,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
    )
    await repo.model.insert_many([d])

    # update step only
    matched1 = await repo.update_step_by_id(str(d.id), "phase-2")
    assert matched1 == 1
    in_db1 = await repo.model.find_one(repo.model.id == d.id)
    assert in_db1.step == "phase-2"

    # invalid step -> -1
    assert await repo.update_step_by_id(str(d.id), "   ") == -1
    assert await repo.update_step_by_id("", "x") == -1

    # update status + step
    matched2 = await repo.update_status_and_step_by_id(
        str(d.id), QRegistryStat.IN_PROGRESS, "phase-3"
    )
    assert matched2 == 1
    in_db2 = await repo.model.find_one(repo.model.id == d.id)
    assert in_db2.status == QRegistryStat.IN_PROGRESS
    assert in_db2.step == "phase-3"

    # invalid combos
    assert await repo.update_status_and_step_by_id(str(d.id), QRegistryStat.RETRY, "   ") == -1
    assert await repo.update_status_and_step_by_id("   ", QRegistryStat.RETRY, "x") == -1
    assert await repo.update_status_and_step_by_id("not-a-uuid", QRegistryStat.RETRY, "x") == -1

@pytest.mark.asyncio
async def test_find_previous_latest_message_by_message_id(db_client):
    """
    Because of the partial-unique index, we can only have multiple docs with the same message_id
    if at most one of them is in {pending, in_progress}. Others must be in {retry, failed, completed}.
    """

    repo = store()
    base = datetime.datetime.now(datetime.timezone.utc).replace(second=0, microsecond=0)

    # Three docs for the same message_id "shared".
    # Order by updated_at: d3 newest, then d2, then d1.
    d1 = repo.model(
        id=uuid.uuid4(),
        message_id="shared",
        queue_name="q",
        step="s1",
        status=QRegistryStat.COMPLETED,  # outside partial-unique set
        created_at=base + datetime.timedelta(minutes=0),
        updated_at=base + datetime.timedelta(minutes=0),
    )
    d2 = repo.model(
        id=uuid.uuid4(),
        message_id="shared",
        queue_name="q",
        step="s2",
        status=QRegistryStat.RETRY,      # outside partial-unique set
        created_at=base + datetime.timedelta(minutes=1),
        updated_at=base + datetime.timedelta(minutes=1),
    )
    d3 = repo.model(
        id=uuid.uuid4(),
        message_id="shared",
        queue_name="q",
        step="s3",
        status=QRegistryStat.PENDING,    # the only one in partial-unique set
        created_at=base + datetime.timedelta(minutes=2),
        updated_at=base + datetime.timedelta(minutes=2),
    )
    await repo.model.insert_many([d1, d2, d3])

    dto = await repo.find_previous_latest_message_by_message_id("shared")
    # Should return the one with the highest updated_at (d3)
    assert dto is not None
    assert dto.step == "s3"
    assert dto.status == QRegistryStat.PENDING

    # Not found
    assert await repo.find_previous_latest_message_by_message_id("nope") is None
