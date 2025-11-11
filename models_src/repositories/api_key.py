import datetime
import uuid
from abc import abstractmethod
from dataclasses import asdict
from typing import List, Optional, Protocol

from beanie.odm.operators.update.general import Set

from models_src.dto.api_key import APIKeyRequestDTO, APIKeyResponseDTO
from models_src.dto.utils import BeanieModelMapper, TortoiseModelMapper
from models_src.exceptions.utils import ApiKeysErrors, internal_error
from models_src.models.api_key import APIKEY
from models_src.models.api_key_document import APIKEY as APIKeyDocument


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


class TortoiseApiKeyStore(IApiKeyStore):

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

        if not hash_key or not hash_key.strip():
            return False

        return await self.model.filter(api_key=hash_key).exists()

    async def update_is_active_by_user_id_and_api_key_id(
        self, user_id: str, api_key_id: uuid.UUID, is_active: bool
    ) -> int:
        if not user_id or not user_id.strip() or not api_key_id:
            return -1

        return await self.model.filter(
            user_id=user_id, id=api_key_id, is_active=True
        ).update(is_active=is_active)

    def __find_all_api_keys_query(self, user_id: str):
        if not user_id or not user_id.strip():
            raise internal_error(**ApiKeysErrors.MISSING_USER_ID.value)

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

        if not api_key or not api_key.strip():
            return None

        data = await self.model.filter(api_key=api_key, is_active=is_active).first()

        return self.model_mapper.map_model_to_dataclass(data, APIKeyResponseDTO)

    async def update_last_used_by_id(self, id: str, last_used_at:datetime=None) -> int:
        if not id or not id.strip():
            return -1

        return await self.model.filter(id=id).update(
            last_used_at= last_used_at or datetime.datetime.now(datetime.timezone.utc)
        )

class BeanieApiKeyStore(IApiKeyStore):
    
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
        
        if not hash_key or not hash_key.strip():
            return False
        
        return await self.model.find(self.model.api_key == hash_key).exists()
    
    async def update_is_active_by_user_id_and_api_key_id(
            self, user_id: str, api_key_id: uuid.UUID, is_active: bool
    ) -> int:
        if not user_id or not user_id.strip() or not api_key_id:
            return -1
        
        result = await self.model.find(
            self.model.user_id == user_id,
            self.model.id == api_key_id,
            self.model.is_active == True
        ).update(
            Set({self.model.is_active: is_active})
        )

        return  result.matched_count
    
    def __find_all_api_keys_query(self, user_id: str):
        if not user_id or not user_id.strip():
            raise internal_error(**ApiKeysErrors.MISSING_USER_ID.value)

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
        if not api_key or not api_key.strip():
            return None
        
        doc = await self.model.find(
            self.model.api_key == api_key, self.model.is_active == is_active
        ).first_or_none()
        
        return self.model_mapper.map_document_to_dataclass(doc, APIKeyResponseDTO)
    
    async def update_last_used_by_id(self, id: str, last_used_at:datetime=None) -> int:
        # validate
        if not id or not id.strip():
            return -1
        try:
            uuid_id = uuid.UUID(id)   # convert input string to UUID
        except ValueError:
            return -1
        
        now = last_used_at or datetime.datetime.now(datetime.timezone.utc)
        
        # match on UUID-typed _id
        result = await self.model.find(self.model.id == uuid_id).update(
            Set({self.model.last_used_at: now})
        )
        return result.matched_count

def get_active_api_key_store():
    return BeanieApiKeyStore()