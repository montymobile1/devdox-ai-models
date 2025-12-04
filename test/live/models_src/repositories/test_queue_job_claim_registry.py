import datetime
import uuid
from time import sleep

import pytest
import pytest_asyncio
from pymongo.errors import DuplicateKeyError
from tortoise.exceptions import IntegrityError

from models_src.exceptions.local_exception import InMemoryDuplicate
from models_src.repositories.queue_job_claim_registry import BeanieQueueProcessingRegistryBackend, \
    InMemoryQueueProcessingRegistryBackend, IQueueProcessingRegistryStore, TortoiseQueueProcessingRegistryBackend

from models_src.dto.queue_job_claim_registry import QueueProcessingRegistryResponseDTO

from models_src.models.common.queue_job_claim_registry_enums import QRegistryStat
from test.conftest import _make_queue_registry_request

# All backends should raise one of these when the partial-unique invariant is violated.
UNIQUE_EXCEPTIONS = (DuplicateKeyError, IntegrityError, InMemoryDuplicate)

class TestQueueProcessingRegistryBackend:
    __test__ = False

    @pytest_asyncio.fixture
    async def repo(self) -> IQueueProcessingRegistryStore:
        raise NotImplementedError

    # =================================================================
    # save()
    # =================================================================

    async def test_save_should_save_single_active_row_for_message_id(
        self, repo: IQueueProcessingRegistryStore
    ):
        """Saving a single active row for a given message_id should succeed and return a DTO."""
        req = _make_queue_registry_request(
            message_id="msg-active-single",
            status=QRegistryStat.PENDING,
        )

        result = await repo.save(req)

        assert isinstance(result, QueueProcessingRegistryResponseDTO)
        assert result.id is not None
        assert result.message_id == "msg-active-single"
        assert result.status == QRegistryStat.PENDING
        # timestamps should be filled by the backend
        assert isinstance(result.created_at, datetime.datetime)
        assert isinstance(result.updated_at, datetime.datetime)

    async def test_save_should_allow_multiple_inactive_rows_for_same_message_id(
        self, repo: IQueueProcessingRegistryStore
    ):
        """Multiple inactive rows (e.g. COMPLETED, FAILED) for the same message_id should be allowed."""
        msg = "msg-inactive-multi"

        req1 = _make_queue_registry_request(
            message_id=msg,
            status=QRegistryStat.COMPLETED,
        )
        req2 = _make_queue_registry_request(
            message_id=msg,
            status=QRegistryStat.FAILED,
        )

        res1 = await repo.save(req1)
        res2 = await repo.save(req2)

        assert res1.message_id == msg
        assert res2.message_id == msg
        assert res1.id != res2.id

    async def test_save_should_allow_one_active_per_each_message_id(
        self, repo: IQueueProcessingRegistryStore
    ):
        """
        Different message_ids should each be allowed to have one active row.
        """
        req1 = _make_queue_registry_request(
            message_id="msg-active-a",
            status=QRegistryStat.PENDING,
        )
        req2 = _make_queue_registry_request(
            message_id="msg-active-b",
            status=QRegistryStat.PENDING,
        )

        res1 = await repo.save(req1)
        res2 = await repo.save(req2)

        assert res1.message_id == "msg-active-a"
        assert res2.message_id == "msg-active-b"
        assert res1.id != res2.id

    async def test_save_should_prevent_second_active_insert_for_same_message_id(
        self, repo: IQueueProcessingRegistryStore
    ):
        """Inserting a second active row for the same message_id should raise a uniqueness-related exception."""
        msg = "msg-dup-insert"

        first = _make_queue_registry_request(
            message_id=msg,
            status=QRegistryStat.PENDING,
        )
        await repo.save(first)

        second = _make_queue_registry_request(
            message_id=msg,
            status=QRegistryStat.IN_PROGRESS,
        )

        with pytest.raises(UNIQUE_EXCEPTIONS):
            await repo.save(second)

    # =================================================================
    # update_status_or_message_id_by_id()
    # =================================================================

    async def test_update_status_or_message_id_by_id_should_update_status_for_existing_row(
        self, repo: IQueueProcessingRegistryStore
    ):
        """update_status_or_message_id_by_id should update the status of an existing row and return 1."""
        req = _make_queue_registry_request(
            message_id="msg-update-status",
            status=QRegistryStat.PENDING,
        )
        created = await repo.save(req)

        updated_count = await repo.update_status_or_message_id_by_id(
            id=str(created.id),
            status=QRegistryStat.IN_PROGRESS,
        )

        assert updated_count == 1

        latest = await repo.find_previous_latest_message_by_message_id(
            "msg-update-status"
        )
        assert latest is not None
        assert latest.id == created.id
        assert latest.status == QRegistryStat.IN_PROGRESS

    async def test_update_status_or_message_id_by_id_should_allow_transition_between_active_statuses_for_same_row(
        self, repo: IQueueProcessingRegistryStore
    ):
        """
        Transitioning from one active status to another on the *same* row
        (e.g. PENDING -> IN_PROGRESS) should be allowed.
        """
        req = _make_queue_registry_request(
            message_id="msg-active-transition",
            status=QRegistryStat.PENDING,
        )
        created = await repo.save(req)

        # active -> active on the same row
        updated_count = await repo.update_status_or_message_id_by_id(
            id=str(created.id),
            status=QRegistryStat.IN_PROGRESS,
        )
        assert updated_count == 1

        latest = await repo.find_previous_latest_message_by_message_id(
            "msg-active-transition"
        )
        assert latest is not None
        assert latest.status == QRegistryStat.IN_PROGRESS

    async def test_update_status_or_message_id_by_id_should_update_message_id_when_provided(
        self, repo: IQueueProcessingRegistryStore
    ):
        """
        update_status_or_message_id_by_id should update message_id when provided.
        """
        req = _make_queue_registry_request(
            message_id="msg-old",
            status=QRegistryStat.PENDING,
        )
        created = await repo.save(req)

        new_msg = "msg-new"

        updated_count = await repo.update_status_or_message_id_by_id(
            id=str(created.id),
            status=QRegistryStat.IN_PROGRESS,
            message_id=new_msg,
        )

        assert updated_count == 1

        latest = await repo.find_previous_latest_message_by_message_id(new_msg)
        assert latest is not None
        assert latest.id == created.id
        assert latest.message_id == new_msg
        assert latest.status == QRegistryStat.IN_PROGRESS

    async def test_update_status_or_message_id_by_id_should_return_zero_when_updating_status_for_unknown_id(
        self, repo: IQueueProcessingRegistryStore
    ):
        """update_status_or_message_id_by_id should return 0 when the given id does not exist."""
        unknown_id = str(uuid.uuid4())

        updated_count = await repo.update_status_or_message_id_by_id(
            id=unknown_id,
            status=QRegistryStat.IN_PROGRESS,
        )

        assert updated_count == 0

    async def test_update_status_or_message_id_by_id_should_forbid_updating_inactive_to_active_when_active_exists_for_same_message_id(
        self, repo: IQueueProcessingRegistryStore
    ):
        """
        Updating an inactive row to an active status must fail
        if another active row with the same message_id already exists.
        """
        msg = "msg-dup-update-status"

        active_req = _make_queue_registry_request(
            message_id=msg,
            status=QRegistryStat.PENDING,
        )
        await repo.save(active_req)

        inactive_req = _make_queue_registry_request(
            message_id=msg,
            status=QRegistryStat.COMPLETED,
        )
        inactive = await repo.save(inactive_req)

        with pytest.raises(UNIQUE_EXCEPTIONS):
            await repo.update_status_or_message_id_by_id(
                id=str(inactive.id),
                status=QRegistryStat.PENDING,
            )

    # =================================================================
    # update_step_by_id()
    # =================================================================

    async def test_update_step_by_id_should_update_step_for_existing_row(
        self, repo: IQueueProcessingRegistryStore
    ):
        """update_step_by_id should update the step for an existing row and return 1."""
        req = _make_queue_registry_request(
            message_id="msg-update-step",
            status=QRegistryStat.COMPLETED,
            step="initial-step",
        )
        created = await repo.save(req)

        updated_count = await repo.update_step_by_id(
            id=str(created.id),
            step="next-step",
        )

        assert updated_count == 1

        latest = await repo.find_previous_latest_message_by_message_id(
            "msg-update-step"
        )
        assert latest is not None
        assert latest.step == "next-step"

    async def test_update_step_by_id_should_return_zero_when_updating_step_for_unknown_id(
        self, repo: IQueueProcessingRegistryStore
    ):
        """update_step_by_id should return 0 when the given id does not exist."""
        unknown_id = str(uuid.uuid4())

        updated_count = await repo.update_step_by_id(
            id=unknown_id,
            step="some-step",
        )

        assert updated_count == 0

    # =================================================================
    # update_status_and_step_by_id()
    # =================================================================

    async def test_update_status_and_step_by_id_should_update_status_and_step_for_existing_row(
        self, repo: IQueueProcessingRegistryStore
    ):
        """update_status_and_step_by_id should update both status and step for an existing row and return 1."""
        req = _make_queue_registry_request(
            message_id="msg-update-both",
            status=QRegistryStat.PENDING,
            step="s1",
        )
        created = await repo.save(req)

        updated_count = await repo.update_status_and_step_by_id(
            id=str(created.id),
            status=QRegistryStat.IN_PROGRESS,
            step="s2",
        )

        assert updated_count == 1

        latest = await repo.find_previous_latest_message_by_message_id(
            "msg-update-both"
        )
        assert latest is not None
        assert latest.status == QRegistryStat.IN_PROGRESS
        assert latest.step == "s2"

    async def test_update_status_and_step_by_id_should_forbid_update_status_and_step_to_active_when_active_exists_for_same_message_id(
        self, repo: IQueueProcessingRegistryStore
    ):
        """
        update_status_and_step_by_id should fail when turning an inactive row active
        while another active row with the same message_id already exists.
        """
        msg = "msg-dup-update-both"

        active_req = _make_queue_registry_request(
            message_id=msg,
            status=QRegistryStat.PENDING,
            step="s1",
        )
        await repo.save(active_req)

        inactive_req = _make_queue_registry_request(
            message_id=msg,
            status=QRegistryStat.COMPLETED,
            step="s-old",
        )
        inactive = await repo.save(inactive_req)

        with pytest.raises(UNIQUE_EXCEPTIONS):
            await repo.update_status_and_step_by_id(
                id=str(inactive.id),
                status=QRegistryStat.PENDING,
                step="s-new",
            )

    # =================================================================
    # find_previous_latest_message_by_message_id()
    # =================================================================

    async def test_find_previous_latest_message_by_message_id_should_return_none_when_no_record_for_message_id(
        self, repo: IQueueProcessingRegistryStore
    ):
        """find_previous_latest_message_by_message_id should return None when no rows exist for the given message_id."""
        result = await repo.find_previous_latest_message_by_message_id(
            "non-existent-msg"
        )
        assert result is None

    async def test_find_previous_latest_message_by_message_id_should_return_latest_record_by_updated_at_for_message_id(
        self, repo: IQueueProcessingRegistryStore
    ):
        """
        find_previous_latest_message_by_message_id should return the record with
        the latest updated_at when multiple rows share the same message_id.
        """
        msg = "msg-latest"

        first_req = _make_queue_registry_request(
            message_id=msg,
            status=QRegistryStat.COMPLETED,
            step="first",
        )
        first = await repo.save(first_req)

        # Ensure timestamps are different across backends
        sleep(0.02)

        second_req = _make_queue_registry_request(
            message_id=msg,
            status=QRegistryStat.COMPLETED,
            step="second",
        )
        second = await repo.save(second_req)

        latest = await repo.find_previous_latest_message_by_message_id(msg)

        assert latest is not None
        assert latest.id in {first.id, second.id}
        # by updated_at, the second insert should be the latest
        assert latest.id == second.id
        assert latest.step == "second"

@pytest.mark.asyncio
class TestTortoiseQueueProcessingRegistryBackend(TestQueueProcessingRegistryBackend):
    __test__ = True
    
    @pytest_asyncio.fixture
    async def repo(self, postgresql_client):
        return TortoiseQueueProcessingRegistryBackend()

@pytest.mark.asyncio
class TestBeanieQueueProcessingRegistryBackend(TestQueueProcessingRegistryBackend):
    __test__ = True
    
    @pytest_asyncio.fixture
    async def repo(self, db_client):
        return BeanieQueueProcessingRegistryBackend()

@pytest.mark.asyncio
class TestInMemoryQueueProcessingRegistryBackend(TestQueueProcessingRegistryBackend):
    __test__ = True
    
    @pytest_asyncio.fixture
    async def repo(self):
        return InMemoryQueueProcessingRegistryBackend()