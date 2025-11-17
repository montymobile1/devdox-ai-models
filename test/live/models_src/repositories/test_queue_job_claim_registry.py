import datetime
import uuid
from time import sleep

import pytest
from models_src.repositories.queue_job_claim_registry import BeanieQueueProcessingRegistryBackend

from models_src.dto.queue_job_claim_registry import QueueProcessingRegistryResponseDTO

from models_src.models.queue_job_claim_registry_enums import QRegistryStat
from test.conftest import _make_queue_registry_request


@pytest.mark.asyncio
class TestBeanieQueueProcessingRegistryStore:
    beanie_store = BeanieQueueProcessingRegistryBackend

    async def test_save_sets_id_and_claimed_at(self, db_client):
        store = self.beanie_store()

        req = _make_queue_registry_request(
            message_id="msg-save-1",
            queue_name="queue-main",
            step="step-1",
            status=QRegistryStat.PENDING,
            claimed_by="worker-1",
        )

        saved = await store.save(req)

        assert isinstance(saved, QueueProcessingRegistryResponseDTO)
        assert isinstance(saved.id, uuid.UUID)
        assert saved.message_id == req.message_id
        assert saved.queue_name == req.queue_name
        assert saved.step == req.step
        assert saved.status == req.status
        assert saved.claimed_by == req.claimed_by
        assert isinstance(saved.claimed_at, datetime.datetime) or saved.claimed_at is None
        assert isinstance(saved.created_at, datetime.datetime)

    async def test_update_status_or_message_id_by_id_updates_status_only(self, db_client):
        store = self.beanie_store()

        req = _make_queue_registry_request(
            message_id="msg-update-1",
            queue_name="queue-update",
            step="step-1",
            status=QRegistryStat.PENDING,
        )
        saved = await store.save(req)

        updated_count = await store.update_status_or_message_id_by_id(
            id=str(saved.id),
            status=QRegistryStat.IN_PROGRESS,
        )
        assert updated_count == 1

        refreshed = await store.find_previous_latest_message_by_message_id(
            message_id=req.message_id
        )
        assert refreshed is not None
        assert refreshed.status == QRegistryStat.IN_PROGRESS
        # message_id unchanged
        assert refreshed.message_id == req.message_id

    async def test_update_status_or_message_id_by_id_updates_message_id_when_provided(self, db_client):
        store = self.beanie_store()

        req = _make_queue_registry_request(
            message_id="msg-old",
            queue_name="queue-update-msg",
            step="step-1",
            status=QRegistryStat.PENDING,
        )
        saved = await store.save(req)

        new_message_id = "msg-new"
        updated_count = await store.update_status_or_message_id_by_id(
            id=str(saved.id),
            status=QRegistryStat.IN_PROGRESS,
            message_id=new_message_id,
        )
        assert updated_count == 1

        refreshed = await store.find_previous_latest_message_by_message_id(
            message_id=new_message_id
        )
        assert refreshed is not None
        assert refreshed.status == QRegistryStat.IN_PROGRESS
        assert refreshed.message_id == new_message_id

    async def test_update_step_by_id_updates_step_and_updated_at(self, db_client):
        store = self.beanie_store()

        req = _make_queue_registry_request(
            message_id="msg-step-1",
            queue_name="queue-step",
            step="step-1",
            status=QRegistryStat.PENDING,
        )
        saved = await store.save(req)

        before = saved.updated_at

        updated_count = await store.update_step_by_id(
            id=str(saved.id),
            step="step-2",
        )
        assert updated_count == 1

        refreshed = await store.find_previous_latest_message_by_message_id(
            message_id=req.message_id
        )
        assert refreshed is not None
        assert refreshed.step == "step-2"
        if before is not None:
            assert refreshed.updated_at.date() >= before.date()

    async def test_update_status_and_step_by_id_updates_both(self, db_client):
        store = self.beanie_store()

        req = _make_queue_registry_request(
            message_id="msg-status-step",
            queue_name="queue-status-step",
            step="step-1",
            status=QRegistryStat.PENDING,
        )
        saved = await store.save(req)

        updated_count = await store.update_status_and_step_by_id(
            id=str(saved.id),
            status=QRegistryStat.COMPLETED,
            step="step-final",
        )
        assert updated_count == 1

        refreshed = await store.find_previous_latest_message_by_message_id(
            message_id=req.message_id
        )
        assert refreshed is not None
        assert refreshed.status == QRegistryStat.COMPLETED
        assert refreshed.step == "step-final"

    async def test_find_previous_latest_message_by_message_id_returns_latest(self, db_client):
        """
        Beanie backend sorts by (-updated_at, -message_id).
        This attempts to use it as close as it can be to the real operation, which is:
        - Once the order for retry happens, a new record is added
        
        upon deleting and readding the queue message, it usually generates a new message_id,
        until it reaches the last retry attempt, then it does not generate a new one, the message_id remains the same as the previous
        
        
        1. Message is dequed, and operation is allowed, e.g: dequed_message = {"message_id" = "1"}
        2. An operation is done on the dequed_message, but it fails and requires a retry, thus we Delete the old dequed_message then reinsert it in the Queue.
         and the  dequed_message "message_id" is updated from "1" to "2", The operations 1 and 2 keep repeating according to total of the retries set
        3. If no retry attempts remain, and suppose at that state "message_id" = "3", then it remains "message_id" = "3"
        
        
        """
        store = self.beanie_store()
        
        # Retry attempts from start to finish
        after_update_of_1st_retry_msg_id = "1"
        first_retry_attempt = await store.save(
            _make_queue_registry_request(
                message_id=after_update_of_1st_retry_msg_id,
                queue_name="queue-history",
                step="step-1",
                status=QRegistryStat.RETRY
            )
        )
        
        sleep(5)
        
        after_update_of_2nd_retry_msg_id = "2"
        second_retry_attempt = await store.save(
            _make_queue_registry_request(
                message_id=after_update_of_2nd_retry_msg_id,
                queue_name="queue-history",
                step="step-2",
                status=QRegistryStat.RETRY,
                previous_message_id=first_retry_attempt.id,
            )
        )
        
        sleep(5)
        
        after_update_of_3rd_retry_msg_id = "3"
        third_retry_attempt = await store.save(
            _make_queue_registry_request(
                message_id=after_update_of_3rd_retry_msg_id,
                queue_name="queue-history",
                step="step-1",
                status=QRegistryStat.RETRY,
                previous_message_id=second_retry_attempt.id,
            )
        )
        
        sleep(5)
        
        # new 4th retry attempt
        new_deque_attempt_msg_id = after_update_of_3rd_retry_msg_id
        
        
        latest = await store.find_previous_latest_message_by_message_id(message_id=new_deque_attempt_msg_id)
        assert latest is not None
        # Should be the one we updated last
        assert latest.id == third_retry_attempt.id
