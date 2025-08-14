import datetime
import uuid
from abc import abstractmethod
from dataclasses import asdict
from typing import List, Optional, Protocol

from models_src.dto.api_key import APIKeyRequestDTO, APIKeyResponseDTO
from models_src.dto.utils import TortoiseModelMapper
from models_src.exceptions.utils import ApiKeysErrors, internal_error
from models_src.models import APIKEY


class IApiKeyStore(Protocol):

    @abstractmethod
    async def save(self, create_model: APIKeyRequestDTO) -> APIKeyResponseDTO: ...

    @abstractmethod
    async def get_all_by_user_id(
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
    async def find_first_by_api_key_and_is_active(
        self, api_key: str, is_active=True
    ) -> Optional[APIKeyResponseDTO]: ...

    @abstractmethod
    async def update_last_used_by_id(self, id: str) -> int: ...


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

    def __get_all_api_keys_query(self, user_id: str):
        if not user_id or not user_id.strip():
            raise internal_error(**ApiKeysErrors.MISSING_USER_ID.value)

        query = self.model.filter(user_id=user_id, is_active=True)

        return query

    async def count_by_user_id(self, user_id: str) -> int:
        query = self.__get_all_api_keys_query(user_id)
        return await query.count()

    async def get_all_by_user_id(
        self, offset, limit, user_id: str
    ) -> List[APIKeyResponseDTO]:

        query = self.__get_all_api_keys_query(user_id)

        data = (
            await query.order_by("-created_at")
            .offset(offset * limit)
            .limit(limit)
            .all()
        )

        return self.model_mapper.map_models_to_dataclasses_list(data, APIKeyResponseDTO)

    async def find_first_by_api_key_and_is_active(
        self, api_key: str, is_active=True
    ) -> Optional[APIKeyResponseDTO]:

        if not api_key or not api_key.strip():
            return None

        data = await self.model.filter(api_key=api_key, is_active=is_active).first()

        return self.model_mapper.map_model_to_dataclass(data, APIKeyResponseDTO)

    async def update_last_used_by_id(self, id: str) -> int:
        if not id or not id.strip():
            return -1

        return await self.model.filter(id=id).update(
            last_used_at=datetime.datetime.now(datetime.timezone.utc)
        )
