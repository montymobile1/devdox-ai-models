# tests/test_inmemory_queue_processing_registry_backend_and_store.py

import datetime
import uuid

import pytest
from models_src.dto.queue_job_claim_registry import QueueProcessingRegistryResponseDTO
from pymongo.errors import DuplicateKeyError

from models_src.exceptions.base_exceptions import DevDoxModelsException
from models_src.exceptions.exception_constants import JOB_ALREADY_CLAIMED
from models_src.exceptions.local_exception import JobAlreadyClaimed
from models_src.models.queue_job_claim_registry_constants import (
    queue_processing_registry_one_claim_unique,
)
from models_src.models.queue_job_claim_registry_enums import QRegistryStat
from models_src.repositories.queue_job_claim_registry import InMemoryQueueProcessingRegistryStore, \
	QueueProcessingRegistryStore
from test.conftest import _make_queue_registry_request


@pytest.mark.asyncio
class TestInMemoryQueueProcessingRegistryStore:
    inmemory_store = InMemoryQueueProcessingRegistryStore

    async def test_save_sets_id_and_claimed_at(self):
        store = self.inmemory_store()

        req = _make_queue_registry_request(
            message_id="mem-msg-1",
            queue_name="mem-queue",
            step="step-1",
            status=QRegistryStat.PENDING,
            claimed_by="worker-1",
        )

        saved = await store.save(req)

        assert isinstance(saved, QueueProcessingRegistryResponseDTO)
        assert isinstance(saved.id, uuid.UUID)
        assert saved.message_id == req.message_id
        assert saved.queue_name == req.queue_name
        assert saved.status == req.status
        assert saved.step == req.step
        assert isinstance(saved.claimed_at, datetime.datetime)
        assert store.total_count == 1

    async def test_update_status_or_message_id_by_id_updates_and_returns_1(self):
        store = self.inmemory_store()

        req = _make_queue_registry_request(
            message_id="mem-msg-update",
            queue_name="mem-queue-update",
            step="step-1",
            status=QRegistryStat.PENDING,
        )
        saved = await store.save(req)

        updated = await store.update_status_or_message_id_by_id(
            id=str(saved.id),
            status=QRegistryStat.IN_PROGRESS,
            message_id="mem-msg-updated",
        )
        assert updated == 1

        # Directly peek into data_store
        data = store._InMemoryQueueProcessingRegistryStore__get_data_store(id=str(saved.id))
        assert data is not None
        assert data.status == QRegistryStat.IN_PROGRESS
        assert data.message_id == "mem-msg-updated"

    async def test_update_status_or_message_id_by_id_returns_zero_for_missing_id(self):
        store = self.inmemory_store()

        updated = await store.update_status_or_message_id_by_id(
            id=str(uuid.uuid4()),
            status=QRegistryStat.PENDING,
        )
        assert updated == 0

    async def test_update_step_by_id_updates_step(self):
        store = self.inmemory_store()

        saved = await store.save(
            _make_queue_registry_request(
                message_id="mem-msg-step",
                queue_name="mem-queue-step",
                step="step-1",
                status=QRegistryStat.PENDING,
            )
        )

        updated = await store.update_step_by_id(id=str(saved.id), step="step-2")
        assert updated == 1

        data = store._InMemoryQueueProcessingRegistryStore__get_data_store(id=str(saved.id))
        assert data is not None
        assert data.step == "step-2"

    async def test_update_step_by_id_missing_id_returns_zero(self):
        store = self.inmemory_store()

        updated = await store.update_step_by_id(id=str(uuid.uuid4()), step="step-2")
        assert updated == 0

    async def test_update_status_and_step_by_id_updates_both(self):
        store = self.inmemory_store()

        saved = await store.save(
            _make_queue_registry_request(
                message_id="mem-msg-both",
                queue_name="mem-queue-both",
                step="step-1",
                status=QRegistryStat.PENDING,
            )
        )

        updated = await store.update_status_and_step_by_id(
            id=str(saved.id),
            status=QRegistryStat.COMPLETED,
            step="step-final",
        )
        assert updated == 1

        data = store._InMemoryQueueProcessingRegistryStore__get_data_store(id=str(saved.id))
        assert data is not None
        assert data.status == QRegistryStat.COMPLETED
        assert data.step == "step-final"

    async def test_find_previous_latest_message_by_message_id_returns_first_match(self):
        store = self.inmemory_store()
        msg_id = "mem-msg-prev"

        first = await store.save(
            _make_queue_registry_request(
                message_id=msg_id,
                queue_name="q1",
                step="step-1",
                status=QRegistryStat.PENDING,
            )
        )
        await store.save(
            _make_queue_registry_request(
                message_id=msg_id,
                queue_name="q1",
                step="step-2",
                status=QRegistryStat.IN_PROGRESS,
            )
        )

        result = await store.find_previous_latest_message_by_message_id(message_id=msg_id)
        assert result is not None
        assert result.message_id == msg_id
        # current in-memory implementation returns the first one it encounters
        # we only assert it matches some record with that message_id


@pytest.mark.asyncio
class TestQueueProcessingRegistryStoreValidation:
    queue_store = QueueProcessingRegistryStore

    async def test_save_duplicate_key_error_with_index_name_raises_job_already_claimed(self):
        class FakeBackend:
            async def save(self, create_model):
                # Simulate DB duplicate error on the partial unique index
                msg = f"E11000 duplicate key error index: {queue_processing_registry_one_claim_unique}"
                raise DuplicateKeyError(msg)

        store = self.queue_store(storage_backend=FakeBackend())
        req = _make_queue_registry_request()

        with pytest.raises(JobAlreadyClaimed) as exc_info:
            await store.save(create_model=req)

        exc = exc_info.value
        assert isinstance(exc, DevDoxModelsException)
        assert exc.user_message == JOB_ALREADY_CLAIMED
        assert exc.log_message == JOB_ALREADY_CLAIMED
        assert exc.log_level == "warning"  # default from DevDoxModelsException

    async def test_save_duplicate_key_error_without_index_name_reraises_original(self):
        class FakeBackend:
            async def save(self, create_model):
                raise DuplicateKeyError("some other unique index")

        store = self.queue_store(storage_backend=FakeBackend())
        req = _make_queue_registry_request()

        with pytest.raises(DuplicateKeyError):
            await store.save(create_model=req)

    @pytest.mark.parametrize(
        "id_value, status, expected",
        [
            (None, QRegistryStat.PENDING, -1),
            ("", QRegistryStat.PENDING, -1),
            (" ", QRegistryStat.PENDING, -1),
            ("\t", QRegistryStat.PENDING, -1),
            ("not-a-uuid", QRegistryStat.PENDING, -1),
            (str(uuid.uuid4()), None, -1),
        ],
    )
    async def test_update_status_or_message_id_by_id_invalid_args_return_minus_one(
        self,
        id_value,
        status,
        expected,
    ):
        store = self.queue_store(storage_backend=None)

        result = await store.update_status_or_message_id_by_id(
            id=id_value,
            status=status,
            message_id=None,
        )
        assert result == expected

    @pytest.mark.parametrize(
        "id_value, step, expected",
        [
            (None, "step-1", -1),
            ("", "step-1", -1),
            (" ", "step-1", -1),
            ("\t", "step-1", -1),
            ("not-a-uuid", "step-1", -1),
            (str(uuid.uuid4()), None, -1),
            (str(uuid.uuid4()), "", -1),
            (str(uuid.uuid4()), " ", -1),
            (str(uuid.uuid4()), "\t", -1),
        ],
    )
    async def test_update_step_by_id_invalid_args_return_minus_one(
        self,
        id_value,
        step,
        expected,
    ):
        store = self.queue_store(storage_backend=None)

        result = await store.update_step_by_id(
            id=id_value,
            step=step,
        )
        assert result == expected

    @pytest.mark.parametrize(
        "id_value, status, step, expected",
        [
            (None, QRegistryStat.PENDING, "step", -1),
            ("", QRegistryStat.PENDING, "step", -1),
            (" ", QRegistryStat.PENDING, "step", -1),
            ("\t", QRegistryStat.PENDING, "step", -1),
            ("not-a-uuid", QRegistryStat.PENDING, "step", -1),
            (str(uuid.uuid4()), None, "step", -1),
            (str(uuid.uuid4()), QRegistryStat.PENDING, None, -1),
            (str(uuid.uuid4()), QRegistryStat.PENDING, "", -1),
            (str(uuid.uuid4()), QRegistryStat.PENDING, " ", -1),
            (str(uuid.uuid4()), QRegistryStat.PENDING, "\t", -1),
        ],
    )
    async def test_update_status_and_step_by_id_invalid_args_return_minus_one(
        self,
        id_value,
        status,
        step,
        expected,
    ):
        store = self.queue_store(storage_backend=None)

        result = await store.update_status_and_step_by_id(
            id=id_value,
            status=status,
            step=step,
        )
        assert result == expected

    @pytest.mark.parametrize("message_id", [None, "", " ", "\t"])
    async def test_find_previous_latest_message_by_message_id_invalid_returns_none(
        self,
        message_id,
    ):
        store = self.queue_store(storage_backend=None)

        result = await store.find_previous_latest_message_by_message_id(
            message_id=message_id
        )
        assert result is None
