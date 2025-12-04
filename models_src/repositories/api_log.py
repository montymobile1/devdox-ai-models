import datetime
import uuid
from abc import abstractmethod
from dataclasses import asdict
from typing import Any, Protocol

from models_src.dto.api_log import ApiLogRequestDTO, ApiLogResponseDTO
from models_src.dto.utils import BeanieModelMapper, TortoiseModelMapper
from models_src.models.tortoise_orm.api_log import ApiLog
from models_src.models.beanie_odm.api_log_document import ApiLog as ApiLogDocument

# --------------------------------------------------
# Specification
# --------------------------------------------------

class IApiLogStore(Protocol):

    @abstractmethod
    async def save(self, create_model: ApiLogRequestDTO) -> ApiLogResponseDTO: ...

# --------------------------------------------------
# Base Store
# --------------------------------------------------

class ApiLogStore(IApiLogStore):
    def __init__(self, storage_backend:IApiLogStore):
        self._storage_backend = storage_backend

    async def save(self, create_model: ApiLogRequestDTO) -> ApiLogResponseDTO:
        return await self._storage_backend.save(create_model=create_model)

# --------------------------------------------------
# Storage Backend
# --------------------------------------------------


class TortoiseApiLogBackend(IApiLogStore):

    model = ApiLog
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

    async def save(self, create_model: ApiLogRequestDTO) -> ApiLogResponseDTO:
        data = await self.model.create(**asdict(create_model))
        return self.model_mapper.map_model_to_dataclass(data, ApiLogResponseDTO)

class BeanieApiLogBackend(IApiLogStore):

    model = ApiLogDocument
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

    async def save(self, create_model: ApiLogRequestDTO) -> ApiLogResponseDTO:
        doc = self.model(**asdict(create_model))
        data = await doc.create()
        return self.model_mapper.map_document_to_dataclass(data, ApiLogResponseDTO)

class InMemoryApiLogBackend(IApiLogStore):
    
    store_cls = ApiLogStore
    
    def __init__(self):
        self.__data_store: dict[Any, list[ApiLogResponseDTO]] = {}
        self.total_count = 0
    
    @property
    def data_store(self):
        return self.__data_store
    
    def get_data_store(self, user_id=None):
        
        if user_id:
            return self.__data_store.get(user_id) or []
        
        return self.__data_store
    
    def add_record(self, data: ApiLogResponseDTO):
        self.__data_store.setdefault(data.user_id, []).append(data)
    
    def set_data_store(self, fake_data: list[ApiLogResponseDTO]):
        for data in fake_data:
            self.add_record(data)
        
        full_total = 0
        for values in self.__data_store.values():
            full_total = full_total + len(values)
        
        self.total_count = full_total
    
    async def save(self, create_model: ApiLogRequestDTO) -> ApiLogResponseDTO:
        response = ApiLogResponseDTO(**asdict(create_model))
        response.id = uuid.uuid4()
        
        now = datetime.datetime.now(datetime.timezone.utc)
        response.created_at = now
        response.updated_at = now

        self.add_record(response)
        self.total_count += 1

        return response

# --------------------------------------------------
# Factory
# --------------------------------------------------

def get_active_api_log_store():
    return ApiLogStore(storage_backend=BeanieApiLogBackend())