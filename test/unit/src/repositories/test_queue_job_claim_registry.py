import pytest
import datetime as dt
from unittest.mock import MagicMock, AsyncMock

from models_src.models import QRegistryStat
from models_src.dto.queue_job_claim_registry import (
    QueueProcessingRegistryRequestDTO,
    QueueProcessingRegistryResponseDTO,
)
from models_src.repositories.queue_job_claim_registry import TortoiseQueueProcessingRegistryStore
import models_src.repositories.queue_job_claim_registry as repo_mod  # to patch class reference
from test.unit.common_test_tools.model_factories import make_qreg
from test.unit.common_test_tools.qs_chain import make_qs_chain


# Freeze time inside THIS repo module so we can assert exact updated_at values.
@pytest.fixture
def freeze_qreg_time(monkeypatch):
    fixed = dt.datetime(2031, 2, 3, 4, 5, 6, tzinfo=dt.timezone.utc)

    class _FrozenDatetimeModule:
        timezone = dt.timezone
        class datetime(dt.datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed

    monkeypatch.setattr(repo_mod, "datetime", _FrozenDatetimeModule)
    return fixed


class TestSave:
    @pytest.mark.asyncio
    async def test_save_returns_dto_with_real_model_instance(self, monkeypatch):
        """Saving should call model.create() and hand back a DTO (no DB)."""
        store = TortoiseQueueProcessingRegistryStore()

        model = MagicMock()
        model.create = AsyncMock(return_value=make_qreg(message_id="m1", queue_name="q1"))
        monkeypatch.setattr(store, "model", model)

        req = QueueProcessingRegistryRequestDTO(
            message_id="m1",
            queue_name="q1",
            step="ingest",
            status=QRegistryStat.PENDING,
        )
        dto = await store.save(req)

        assert isinstance(dto, QueueProcessingRegistryResponseDTO)
        assert dto.message_id == "m1" and dto.queue_name == "q1"
        model.create.assert_awaited_once()


class TestUpdateStatusOrMessageIdById:
    @pytest.mark.asyncio
    async def test_bad_inputs_return_minus1(self):
        """Blank id or missing status -> -1 and no DB work."""
        store = TortoiseQueueProcessingRegistryStore()
        assert await store.update_status_or_message_id_by_id("", QRegistryStat.PENDING) == -1
        assert await store.update_status_or_message_id_by_id("id", None) == -1  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_updates_status_only(self, freeze_qreg_time, monkeypatch):
        """filter(id=...), update(updated_at=fixed, status=...)."""
        store = TortoiseQueueProcessingRegistryStore()
        qs = make_qs_chain(update_value=1)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        changed = await store.update_status_or_message_id_by_id("abc", QRegistryStat.IN_PROGRESS)
        assert changed == 1

        model.filter.assert_called_once_with(id="abc")
        kwargs = qs.update.call_args.kwargs
        assert kwargs["status"] == QRegistryStat.IN_PROGRESS
        assert kwargs["updated_at"] == freeze_qreg_time

    @pytest.mark.asyncio
    async def test_updates_status_and_message_id(self, freeze_qreg_time, monkeypatch):
        """If message_id is provided, it is included in the update payload."""
        store = TortoiseQueueProcessingRegistryStore()
        qs = make_qs_chain(update_value=1)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        changed = await store.update_status_or_message_id_by_id("abc", QRegistryStat.RETRY, message_id="m-next")
        assert changed == 1

        kwargs = qs.update.call_args.kwargs
        assert kwargs["status"] == QRegistryStat.RETRY
        assert kwargs["message_id"] == "m-next"
        assert kwargs["updated_at"] == freeze_qreg_time


class TestUpdateStepById:
    @pytest.mark.asyncio
    async def test_bad_inputs_return_minus1(self):
        """Blank id or blank step -> -1."""
        store = TortoiseQueueProcessingRegistryStore()
        assert await store.update_step_by_id("", "step-1") == -1
        assert await store.update_step_by_id("id", "   ") == -1

    @pytest.mark.asyncio
    async def test_updates_step(self, freeze_qreg_time, monkeypatch):
        """filter(id=...), update(updated_at=fixed, step=...)."""
        store = TortoiseQueueProcessingRegistryStore()
        qs = make_qs_chain(update_value=1)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        changed = await store.update_step_by_id("abc", "transform")
        assert changed == 1

        model.filter.assert_called_once_with(id="abc")
        kwargs = qs.update.call_args.kwargs
        assert kwargs["step"] == "transform"
        assert kwargs["updated_at"] == freeze_qreg_time


class TestUpdateStatusAndStepById:
    @pytest.mark.asyncio
    async def test_bad_inputs_return_minus1(self):
        """Any invalid input (blank id/status/step) -> -1."""
        store = TortoiseQueueProcessingRegistryStore()
        assert await store.update_status_and_step_by_id("", QRegistryStat.PENDING, "s") == -1
        assert await store.update_status_and_step_by_id("id", None, "s") == -1  # type: ignore[arg-type]
        assert await store.update_status_and_step_by_id("id", QRegistryStat.PENDING, " ") == -1

    @pytest.mark.asyncio
    async def test_updates_status_and_step(self, freeze_qreg_time, monkeypatch):
        """filter(id=...), update(updated_at=fixed, status=..., step=...)."""
        store = TortoiseQueueProcessingRegistryStore()
        qs = make_qs_chain(update_value=1)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        changed = await store.update_status_and_step_by_id("abc", QRegistryStat.COMPLETED, "finalize")
        assert changed == 1

        model.filter.assert_called_once_with(id="abc")
        kwargs = qs.update.call_args.kwargs
        assert kwargs["status"] == QRegistryStat.COMPLETED
        assert kwargs["step"] == "finalize"
        assert kwargs["updated_at"] == freeze_qreg_time


class TestFindPreviousLatestMessageByMessageId:
    @pytest.mark.asyncio
    async def test_happy_path_filters_orders_then_first_and_maps(self, monkeypatch):
        """
        Uses the QueueProcessingRegistry class symbol directly (not store.model),
        so patch the class inside the repo module.
        """
        store = TortoiseQueueProcessingRegistryStore()

        row = make_qreg(message_id="m1")
        qs = make_qs_chain(result_for_first=row)

        fake_class = MagicMock()
        fake_class.filter.return_value = qs
        monkeypatch.setattr(repo_mod, "QueueProcessingRegistry", fake_class)

        dto = await store.find_previous_latest_message_by_message_id("m1")
        assert isinstance(dto, QueueProcessingRegistryResponseDTO)

        fake_class.filter.assert_called_once_with(message_id="m1")
        qs.order_by.assert_called_once_with("-message_id", "-updated_at")
        qs.first.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_none_when_not_found(self, monkeypatch):
        """If first() returns None, repo returns None."""
        store = TortoiseQueueProcessingRegistryStore()

        qs = make_qs_chain(result_for_first=None)
        fake_class = MagicMock()
        fake_class.filter.return_value = qs
        monkeypatch.setattr(repo_mod, "QueueProcessingRegistry", fake_class)

        dto = await store.find_previous_latest_message_by_message_id("missing")
        assert dto is None
        fake_class.filter.assert_called_once_with(message_id="missing")
