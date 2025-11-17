import datetime
import uuid
from abc import abstractmethod
from dataclasses import asdict
from typing import Any, List, Optional, Protocol

from beanie.odm.operators.update.general import Set

from models_src.dto.api_key import APIKeyRequestDTO, APIKeyResponseDTO
from models_src.dto.utils import BeanieModelMapper, TortoiseModelMapper
from models_src.exceptions.utils import ApiKeysErrors, internal_error
from models_src.models.api_key import APIKEY
from models_src.models.api_key_document import APIKEY as APIKeyDocument

# --------------------------------------------------
# Specification
# --------------------------------------------------

class IApiKeyStore(Protocol):

    @abstractmethod
    async def save(self, create_model: APIKeyRequestDTO) -> APIKeyResponseDTO: ...

    @abstractmethod
    async def find_all_by_user_id(
        self, offset, limit, user_id: str
    ) -> List[APIKeyResponseDTO]: ...

    @abstractmethod
    async def count_by_user_id(self, user_id: str) -> int: ...

    @abstractmethod
    async def exists_by_hash_key(self, hash_key: str) -> bool: ...

    @abstractmethod
    async def update_is_active_by_user_id_and_api_key_id(
        self, user_id, api_key_id, is_active
    ) -> int: ...

    @abstractmethod
    async def find_by_active_api_key(
        self, api_key: str, is_active=True
    ) -> Optional[APIKeyResponseDTO]: ...

    @abstractmethod
    async def update_last_used_by_id(self, id: str, last_used_at:datetime.datetime=None) -> int: ...

# --------------------------------------------------
# Storage Backend
# --------------------------------------------------

class TortoiseApiKeyBackend(IApiKeyStore):

    model = APIKEY
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
    
    async def save(self, create_model: APIKeyRequestDTO) -> APIKeyResponseDTO:
        data = await self.model.create(**asdict(create_model))
        return self.model_mapper.map_model_to_dataclass(data, APIKeyResponseDTO)
    
    async def exists_by_hash_key(self, hash_key: str) -> bool:
        return await self.model.filter(api_key=hash_key).exists()

    async def update_is_active_by_user_id_and_api_key_id(
        self, user_id: str, api_key_id: uuid.UUID, is_active: bool
    ) -> int:
        return await self.model.filter(
            user_id=user_id, id=api_key_id, is_active=True
        ).update(is_active=is_active)

    def __find_all_api_keys_query(self, user_id: str):
        query = self.model.filter(user_id=user_id, is_active=True)

        return query

    async def count_by_user_id(self, user_id: str) -> int:
        query = self.__find_all_api_keys_query(user_id)
        return await query.count()

    async def find_all_by_user_id(
        self, offset, limit, user_id: str
    ) -> List[APIKeyResponseDTO]:

        query = self.__find_all_api_keys_query(user_id)

        data = (
            await query.order_by("-created_at")
            .offset(offset * limit)
            .limit(limit)
            .all()
        )

        return self.model_mapper.map_models_to_dataclasses_list(data, APIKeyResponseDTO)

    async def find_by_active_api_key(
        self, api_key: str, is_active=True
    ) -> Optional[APIKeyResponseDTO]:
        data = await self.model.filter(api_key=api_key, is_active=is_active).first()

        return self.model_mapper.map_model_to_dataclass(data, APIKeyResponseDTO)

    async def update_last_used_by_id(self, id: str, last_used_at:datetime.datetime=None) -> int:
        return await self.model.filter(id=id).update(
            last_used_at= last_used_at or datetime.datetime.now(datetime.timezone.utc)
        )

class BeanieApiKeyBackend(IApiKeyStore):
    
    model = APIKeyDocument
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
    
    async def save(self, create_model: APIKeyRequestDTO) -> APIKeyResponseDTO:
        doc = self.model(**asdict(create_model))
        data = await doc.create()
        return self.model_mapper.map_document_to_dataclass(data, APIKeyResponseDTO)
    
    async def exists_by_hash_key(self, hash_key: str) -> bool:
        return await self.model.find(self.model.api_key == hash_key).exists()
    
    async def update_is_active_by_user_id_and_api_key_id(
            self, user_id: str, api_key_id: uuid.UUID, is_active: bool
    ) -> int:
        result = await self.model.find(
            self.model.user_id == user_id,
            self.model.id == api_key_id,
            self.model.is_active == True
        ).update(
            Set({self.model.is_active: is_active})
        )

        return  result.matched_count
    
    def __find_all_api_keys_query(self, user_id: str):
        return self.model.find(
            self.model.user_id == user_id, self.model.is_active == True
        )
    
    async def count_by_user_id(self, user_id: str) -> int:
        return await self.__find_all_api_keys_query(user_id).count()
    
    async def find_all_by_user_id(
            self, offset: int, limit: int, user_id: str
    ) -> List[APIKeyResponseDTO]:
        q = self.__find_all_api_keys_query(user_id)
        
        docs = await (
            q.sort(-self.model.created_at)
            .skip(offset * limit)
            .limit(limit)
            .to_list()
        )
        
        return self.model_mapper.map_documents_to_dataclasses_list(docs, APIKeyResponseDTO)
    
    async def find_by_active_api_key(
            self, api_key: str, is_active: bool = True
    ) -> Optional[APIKeyResponseDTO]:
        doc = await self.model.find(
            self.model.api_key == api_key, self.model.is_active == is_active
        ).first_or_none()
        
        return self.model_mapper.map_document_to_dataclass(doc, APIKeyResponseDTO)
    
    async def update_last_used_by_id(self, id: str, last_used_at:datetime=None) -> int:
        now = last_used_at or datetime.datetime.now(datetime.timezone.utc)
        
        result = await self.model.find(self.model.id == uuid.UUID(id)).update(
            Set({self.model.last_used_at: now})
        )
        return result.matched_count

class InMemoryApiKeyBackend(IApiKeyStore):

    def __init__(self):
        self.data_store: dict[Any, List[APIKeyResponseDTO]] = {}
        self.existing_hash_set = set()
        self.total_count = 0

    def __get_data_store(self, user_id=None):

        if user_id:
            return self.data_store.get(user_id) or []

        return self.data_store

    def __set_data_store(self, data: APIKeyResponseDTO):
        self.data_store.setdefault(data.user_id, []).append(data)

    def set_fake_data(self, fake_data: list[APIKeyResponseDTO]):
        for data in fake_data:
            self.__set_data_store(data)
            self.existing_hash_set.add(data.api_key)

        full_total = 0
        for values in self.data_store.values():
            full_total = full_total + len(values)

        self.total_count = full_total

    async def exists_by_hash_key(self, hash_key: str) -> bool:
        return hash_key in self.existing_hash_set

    async def save(self, create_model: APIKeyRequestDTO) -> APIKeyResponseDTO:
        response = APIKeyResponseDTO(**asdict(create_model))
        response.id = uuid.uuid4()
        response.created_at = datetime.datetime.now(datetime.timezone.utc)

        self.__set_data_store(response)
        self.existing_hash_set.add(response.api_key)
        self.total_count += 1

        return response

    async def update_is_active_by_user_id_and_api_key_id(
        self, user_id, api_key_id, is_active
    ) -> int:
        updated = 0

        data: list = self.__get_data_store(user_id=user_id)

        for index, value in enumerate(data):
            if value.api_key_id == api_key_id and value.is_active:
                value.is_active = is_active
                updated += 1
        return updated

    async def find_all_by_user_id(
        self, offset, limit, user_id
    ) -> List[APIKeyResponseDTO]:
        data: List[APIKeyResponseDTO] = self.__get_data_store(user_id=user_id)

        sorted_data = sorted(
            [value for value in data if value.is_active],
            key=lambda k: k.created_at,
            reverse=True,
        )

        return sorted_data

    async def count_by_user_id(self, user_id: str) -> int:
        data: List[APIKeyResponseDTO] = self.__get_data_store(user_id=user_id)

        is_active_data = [value for value in data if value.is_active]

        return len(is_active_data)

    async def find_by_active_api_key(
        self, api_key: str, is_active=True
    ) -> Optional[APIKeyResponseDTO]:
        data = self.__get_data_store()

        if not data:
            return None

        discovered_result = None
        for val in data.values():
            for i in val:
                if i.api_key == api_key and i.is_active == is_active:
                    discovered_result = i
                    break

            if discovered_result:
                break

        return discovered_result

    async def update_last_used_by_id(self, id: str, last_used_at:datetime=None) -> int:
        data = self.__get_data_store()
        updated = 0

        if not data:
            return updated

        for val in data.values():
            for i in val:
                if i.id == uuid.UUID(id):
                    updated += 1
                    i.last_used_at = last_used_at or datetime.datetime.now(datetime.timezone.utc)

        return updated

# --------------------------------------------------
# Base Store
# --------------------------------------------------

class ApiKeyStore(IApiKeyStore):
    
    def __init__(self, storage_backend:IApiKeyStore):
        self._storage_backend = storage_backend
    
    async def save(self, create_model: APIKeyRequestDTO) -> APIKeyResponseDTO:
        return await self._storage_backend.save(create_model=create_model)
    
    async def find_all_by_user_id(self, offset, limit, user_id: str) -> List[APIKeyResponseDTO]:
        
        if not user_id or not user_id.strip():
            raise internal_error(**ApiKeysErrors.MISSING_USER_ID.value)
        
        return await self._storage_backend.find_all_by_user_id(offset=offset, limit=limit, user_id=user_id)
    
    async def count_by_user_id(self, user_id: str) -> int:
        
        if not user_id or not user_id.strip():
            raise internal_error(**ApiKeysErrors.MISSING_USER_ID.value)
        
        return await self._storage_backend.count_by_user_id(user_id=user_id)
    
    async def exists_by_hash_key(self, hash_key: str) -> bool:
        
        if not hash_key or not hash_key.strip():
            return False
        
        return await self._storage_backend.exists_by_hash_key(hash_key=hash_key)
    
    async def update_is_active_by_user_id_and_api_key_id(self, user_id, api_key_id, is_active) -> int:
        
        if not user_id or not user_id.strip() or not api_key_id:
            return -1
        
        return await self._storage_backend.update_is_active_by_user_id_and_api_key_id(user_id=user_id, api_key_id=api_key_id, is_active=is_active)
    
    async def find_by_active_api_key(self, api_key: str, is_active=True) -> Optional[APIKeyResponseDTO]:
        
        if not api_key or not api_key.strip():
            return None
        
        return await self._storage_backend.find_by_active_api_key(api_key=api_key, is_active=is_active)
    
    async def update_last_used_by_id(self, id: str, last_used_at: datetime.datetime = None) -> int:
        
        # validate if its a valid uuid
        if not id or not id.strip():
            return -1
        try:
            uuid.UUID(id)   # convert input string to UUID
        except ValueError:
            return -1
        
        return await self._storage_backend.update_last_used_by_id(id=id, last_used_at=last_used_at)

# --------------------------------------------------
# Factory
# --------------------------------------------------

def get_active_api_key_store():
    return ApiKeyStore(storage_backend=BeanieApiKeyBackend())
