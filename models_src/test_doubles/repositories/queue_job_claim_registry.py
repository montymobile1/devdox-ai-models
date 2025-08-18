import datetime
import uuid
from dataclasses import asdict
from typing import Any, List, Optional, Tuple
from uuid import uuid4

from models_src.dto.queue_job_claim_registry import (
    QueueProcessingRegistryRequestDTO,
    QueueProcessingRegistryResponseDTO,
)
from models_src.models import QRegistryStat
from models_src.repositories.queue_job_claim_registry import (
    IQueueProcessingRegistryStore,
)
from models_src.test_doubles.repositories.bases import FakeBase, StubPlanMixin


class FakeQueueProcessingRegistryStore(FakeBase, IQueueProcessingRegistryStore):

    def __init__(self):
        super().__init__()
        self.data_store: dict[Any, QueueProcessingRegistryResponseDTO] = {}
        self.total_count = 0

    def __get_data_store(self, id: str = None):

        if id:
            return self.data_store.get(uuid.UUID(id), None)

        return self.data_store

    def __set_data_store(self, data: QueueProcessingRegistryResponseDTO):
        self.data_store.setdefault(data.id, data)

    def set_fake_data(self, fake_data: List[QueueProcessingRegistryResponseDTO]):
        for data in fake_data:
            self.__set_data_store(data)

        self.total_count = len(self.__get_data_store())

    async def save(
        self, create_model: QueueProcessingRegistryRequestDTO
    ) -> QueueProcessingRegistryResponseDTO:
        self._before(self.save, create_model=create_model)

        response = QueueProcessingRegistryResponseDTO(**asdict(create_model))
        response.id = uuid4()
        response.created_at = datetime.datetime.now(datetime.timezone.utc)

        self.__set_data_store(response)
        self.total_count += 1

        return response

    async def update_status_or_message_id_by_id(
        self, id: str, status: QRegistryStat, message_id: Optional[str] = None
    ) -> int:
        self._before(
            self.update_status_or_message_id_by_id,
            id=id,
            status=status,
            message_id=message_id,
        )

        if (not id or not id.strip()) or not status:
            return -1

        updated = 0

        data_obj = self.__get_data_store(id=id)

        if not data_obj:
            return updated

        data_obj.status = status

        if message_id:
            data_obj.message_id = message_id

        updated += 1

        return updated

    async def update_step_by_id(self, id: str, step: str) -> int:
        self._before(self.update_step_by_id, id=id, step=step)

        if not id or not id.strip() or not step or not step.strip():
            return -1

        updated = 0

        data_obj = self.__get_data_store(id=id)

        if not data_obj:
            return updated

        data_obj.step = step

        updated += 1

        return updated

    async def update_status_and_step_by_id(
        self, id: str, status: QRegistryStat, step: str
    ) -> int:
        self._before(self.update_status_and_step_by_id, id=id, status=status, step=step)

        if not id or not id.strip() or not status or not step or not step.strip():
            return -1

        updated = 0

        data_obj = self.__get_data_store(id=id)

        if not data_obj:
            return updated

        data_obj.step = step
        data_obj.status = status

        updated += 1

        return updated

    async def find_previous_latest_message_by_message_id(
        self, message_id: str
    ) -> Optional[QueueProcessingRegistryResponseDTO]:

        self._before(
            self.find_previous_latest_message_by_message_id, message_id=message_id
        )

        data_obj = self.__get_data_store()

        for items in data_obj.values():
            if items.message_id == message_id:
                return items

        return None


class StubQueueProcessingRegistryStore(StubPlanMixin, IQueueProcessingRegistryStore):

    def __init__(self):
        super().__init__()

    async def save(
        self, create_model: QueueProcessingRegistryRequestDTO
    ) -> QueueProcessingRegistryResponseDTO:
        return await self._stub(self.save, create_model=create_model)

    async def update_status_or_message_id_by_id(
        self, id: str, status: QRegistryStat, message_id: Optional[str] = None
    ) -> int:
        return await self._stub(
            self.update_status_or_message_id_by_id,
            id=id,
            status=status,
            message_id=message_id,
        )

    async def update_step_by_id(self, id: str, step: str) -> int:
        return await self._stub(self.update_step_by_id, id=id, step=step)

    async def update_status_and_step_by_id(
        self, id: str, status: QRegistryStat, step: str
    ) -> int:
        return await self._stub(
            self.update_status_and_step_by_id, id=id, status=status, step=step
        )

    async def find_previous_latest_message_by_message_id(
        self, message_id: str
    ) -> Optional[QueueProcessingRegistryResponseDTO]:
        return await self._stub(
            self.find_previous_latest_message_by_message_id, message_id=message_id
        )
