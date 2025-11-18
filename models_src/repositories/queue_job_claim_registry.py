import datetime
import uuid
from abc import abstractmethod
from dataclasses import asdict
from typing import Any, List, Optional, Protocol

from beanie.odm.operators.update.general import Set
from tortoise.exceptions import IntegrityError

from models_src.models.queue_job_claim_registry import QueueProcessingRegistry
from models_src.models.queue_job_claim_registry_enums import QRegistryStat
from pymongo.errors import DuplicateKeyError

from models_src.dto.queue_job_claim_registry import (
    QueueProcessingRegistryRequestDTO,
    QueueProcessingRegistryResponseDTO,
)
from models_src.dto.utils import BeanieModelMapper, TortoiseModelMapper
from models_src.exceptions.local_exception import JobAlreadyClaimed
from models_src.models.queue_job_claim_registry_document import QueueProcessingRegistry as QueueProcessingRegistryDocument
from models_src.models.queue_job_claim_registry_constants import queue_processing_registry_one_claim_unique

# --------------------------------------------------
# Specification
# --------------------------------------------------

class IQueueProcessingRegistryStore(Protocol):

    @abstractmethod
    async def save(
        self, create_model: QueueProcessingRegistryRequestDTO
    ) -> QueueProcessingRegistryResponseDTO: ...

    @abstractmethod
    async def update_status_or_message_id_by_id(
        self, id: str, status: QRegistryStat, message_id: Optional[str] = None
    ) -> int: ...

    @abstractmethod
    async def update_step_by_id(self, id: str, step: str) -> int: ...

    @abstractmethod
    async def update_status_and_step_by_id(
        self, id: str, status: QRegistryStat, step: str
    ) -> int: ...

    @abstractmethod
    async def find_previous_latest_message_by_message_id(
        self, message_id: str
    ) -> Optional[QueueProcessingRegistryResponseDTO]: ...

# --------------------------------------------------
# Base Store
# --------------------------------------------------

class QueueProcessingRegistryStore(IQueueProcessingRegistryStore):
    
    def __init__(self, storage_backend:IQueueProcessingRegistryStore):
        self._storage_backend = storage_backend
    
    async def save(
            self, create_model: QueueProcessingRegistryRequestDTO
    ) -> QueueProcessingRegistryResponseDTO:
        try:
            return await self._storage_backend.save(create_model=create_model)
        except (DuplicateKeyError, IntegrityError) as e:
            if queue_processing_registry_one_claim_unique in str(e):
                raise JobAlreadyClaimed() from e
            raise
    
    async def _uuid_or_neg1(self, id: Optional[str]) -> Optional[uuid.UUID]:
        if not id or not id.strip():
            return None
        try:
            return uuid.UUID(id)
        except ValueError:
            return None
    
    async def update_status_or_message_id_by_id(
            self, id: str, status: QRegistryStat, message_id: Optional[str] = None
    ) -> int:
        
        if not status:
            return -1
        uuid_id = await self._uuid_or_neg1(id)
        if uuid_id is None:
            return -1
        
        return await self._storage_backend.update_status_or_message_id_by_id(id=id, status=status, message_id=message_id)
    
    async def update_step_by_id(self, id: str, step: str) -> int:
        if not step or not step.strip():
            return -1
        uuid_id = await self._uuid_or_neg1(id)
        if uuid_id is None:
            return -1
        
        return await self._storage_backend.update_step_by_id(id=id, step=step)
    
    async def update_status_and_step_by_id(
            self, id: str, status: QRegistryStat, step: str
    ) -> int:
        
        if (not status) or (not step or not step.strip()):
            return -1
        uuid_id = await self._uuid_or_neg1(id)
        if uuid_id is None:
            return -1
        
        return await self._storage_backend.update_status_and_step_by_id(id=id, status=status, step=step)
    
    async def find_previous_latest_message_by_message_id(
            self, message_id: str
    ) -> Optional[QueueProcessingRegistryResponseDTO]:
        
        if not message_id or not message_id.strip():
            return None
        
        return await self._storage_backend.find_previous_latest_message_by_message_id(message_id=message_id)

# --------------------------------------------------
# Storage Backend
# --------------------------------------------------

class TortoiseQueueProcessingRegistryBackend(IQueueProcessingRegistryStore):

    model = QueueProcessingRegistry
    model_mapper = TortoiseModelMapper

    def __init__(self):
        """
        Have to add this as an empty __init__ to override it, because when using it with Depends(),
        FastAPI dependency mechanism will automatically assume its
        ```
        def __init__(self, *args, **kwargs):
                pass
        ```
        Causing unneeded behavior.
        """
        pass

    async def __internal_update_by_id(self, id: str, **kwargs):
        return await self.model.filter(id=id).update(
            updated_at=datetime.datetime.now(datetime.timezone.utc), **kwargs
        )

    async def save(
        self, create_model: QueueProcessingRegistryRequestDTO
    ) -> QueueProcessingRegistryResponseDTO:
        raw_data = await self.model.create(**asdict(create_model))
        return self.model_mapper.map_model_to_dataclass(
            raw_data, QueueProcessingRegistryResponseDTO
        )

    async def update_status_or_message_id_by_id(
        self, id: str, status: QRegistryStat, message_id: Optional[str] = None
    ) -> int:
        if (not id or not id.strip()) or not status:
            return -1

        values_to_update_dict: dict = {"status": status}

        if message_id:
            values_to_update_dict["message_id"] = message_id

        return await self.__internal_update_by_id(id, **values_to_update_dict)

    async def update_step_by_id(self, id: str, step: str) -> int:
        if not id or not id.strip() or not step or not step.strip():
            return -1

        return await self.__internal_update_by_id(id, step=step)

    async def update_status_and_step_by_id(
        self, id: str, status: QRegistryStat, step: str
    ) -> int:
        if not id or not id.strip() or not status or not step or not step.strip():
            return -1

        return await self.__internal_update_by_id(id, status=status, step=step)

    async def find_previous_latest_message_by_message_id(
        self, message_id: str
    ) -> Optional[QueueProcessingRegistryResponseDTO]:
        previous_latest_message = (
            await QueueProcessingRegistry.filter(message_id=message_id)
            .order_by("-message_id", "-updated_at")
            .first()
        )

        return self.model_mapper.map_model_to_dataclass(
            previous_latest_message, QueueProcessingRegistryResponseDTO
        )

class BeanieQueueProcessingRegistryBackend(IQueueProcessingRegistryStore):
    model = QueueProcessingRegistryDocument
    model_mapper = BeanieModelMapper
    
    def __init__(self):
        """
        Have to add this as an empty __init__ to override it, because when using it with Depends(),
        FastAPI dependency mechanism will automatically assume its
        ```
        def __init__(self, *args, **kwargs):
                pass
        ```
        Causing unneeded behavior.
        """
        pass

    async def save(
        self, create_model: QueueProcessingRegistryRequestDTO
    ) -> QueueProcessingRegistryResponseDTO:
        
        model_dict = asdict(create_model)
        if model_dict.get("updated_at") is None:
            model_dict.pop("updated_at", None)
        
        doc = self.model(**model_dict)
        data = await doc.create()
        return self.model_mapper.map_document_to_dataclass(
            data, QueueProcessingRegistryResponseDTO
        )

    async def update_status_or_message_id_by_id(
        self, id: str, status: QRegistryStat, message_id: Optional[str] = None
    ) -> int:
        now = datetime.datetime.now(datetime.timezone.utc)
        updates = {
            self.model.status: status,
            self.model.updated_at: now,
        }
        if message_id and message_id.strip():
            updates[self.model.message_id] = message_id

        # NOTE: if message_id collides with another doc that is PENDING/IN_PROGRESS,
        # this will raise DuplicateKeyError due to partial-unique index.
        result = await self.model.find(self.model.id == uuid.UUID(id)).update(Set(updates))
        return result.matched_count

    async def update_step_by_id(self, id: str, step: str) -> int:
        now = datetime.datetime.now(datetime.timezone.utc)
        result = await self.model.find(self.model.id == uuid.UUID(id)).update(
            Set({self.model.step: step, self.model.updated_at: now})
        )
        return result.matched_count

    async def update_status_and_step_by_id(
        self, id: str, status: QRegistryStat, step: str
    ) -> int:
        now = datetime.datetime.now(datetime.timezone.utc)
        result = await self.model.find(self.model.id == uuid.UUID(id)).update(
            Set(
                {
                    self.model.status: status,
                    self.model.step: step.strip(),
                    self.model.updated_at: now,
                }
            )
        )
        return result.matched_count

    async def find_previous_latest_message_by_message_id(
        self, message_id: str
    ) -> Optional[QueueProcessingRegistryResponseDTO]:
        doc = (
            await self.model.find(self.model.message_id == message_id.strip())
            .sort(-self.model.updated_at, -self.model.message_id)
            .first_or_none()
        )
        return self.model_mapper.map_document_to_dataclass(
            doc, QueueProcessingRegistryResponseDTO
        )

class InMemoryQueueProcessingRegistryBackend(IQueueProcessingRegistryStore):
    
    store_cls = QueueProcessingRegistryStore
    
    def __init__(self):
        self.__data_store: dict[Any, QueueProcessingRegistryResponseDTO] = {}
        self.total_count = 0
    
    @property
    def data_store(self):
        return self.__data_store
    
    def get_data_store(self, id: str = None):

        if id:
            return self.__data_store.get(uuid.UUID(id), None)

        return self.__data_store

    def add_record(self, data: QueueProcessingRegistryResponseDTO):
        self.__data_store.setdefault(data.id, data)

    def set_data_store(self, fake_data: List[QueueProcessingRegistryResponseDTO]):
        for data in fake_data:
            self.add_record(data)

        self.total_count = len(self.get_data_store())

    async def save(
        self, create_model: QueueProcessingRegistryRequestDTO
    ) -> QueueProcessingRegistryResponseDTO:
        response = QueueProcessingRegistryResponseDTO(**asdict(create_model))
        response.id = uuid.uuid4()
        response.claimed_at = datetime.datetime.now(datetime.timezone.utc)

        self.add_record(response)
        self.total_count += 1

        return response

    async def update_status_or_message_id_by_id(
        self, id: str, status: QRegistryStat, message_id: Optional[str] = None
    ) -> int:
        updated = 0

        data_obj = self.get_data_store(id=id)

        if not data_obj:
            return updated

        data_obj.status = status

        if message_id:
            data_obj.message_id = message_id

        updated += 1

        return updated

    async def update_step_by_id(self, id: str, step: str) -> int:

        updated = 0

        data_obj = self.get_data_store(id=id)

        if not data_obj:
            return updated

        data_obj.step = step

        updated += 1

        return updated

    async def update_status_and_step_by_id(
        self, id: str, status: QRegistryStat, step: str
    ) -> int:
        updated = 0

        data_obj = self.get_data_store(id=id)

        if not data_obj:
            return updated

        data_obj.step = step
        data_obj.status = status

        updated += 1

        return updated

    async def find_previous_latest_message_by_message_id(
        self, message_id: str
    ) -> Optional[QueueProcessingRegistryResponseDTO]:

        data_obj = self.get_data_store()

        for items in data_obj.values():
            if items.message_id == message_id:
                return items

        return None

# --------------------------------------------------
# Factory
# --------------------------------------------------

def get_active_qpr_store():
    return QueueProcessingRegistryStore(storage_backend=BeanieQueueProcessingRegistryBackend())