import uuid
from abc import abstractmethod
from dataclasses import asdict
from typing import List, Protocol

from models_src.dto.api_key import APIKeyRequestDTO, APIKeyResponseDTO
from models_src.dto.utils import TortoiseModelMapper
from models_src.models import APIKEY


class IApiKeyStore(Protocol):

    @abstractmethod
    async def query_for_existing_hashes(self, hash_key: str) -> bool: ...

    @abstractmethod
    async def save_api_key(self, create_model: APIKeyRequestDTO) -> APIKeyResponseDTO: ...

    @abstractmethod
    async def set_inactive_by_user_id_and_api_key_id(
        self, user_id, api_key_id
    ) -> int: ...

    @abstractmethod
    async def get_all_api_keys(self, user_id) -> List[APIKeyResponseDTO]: ...

class TortoiseApiKeyStore(IApiKeyStore):
    
    model=APIKEY
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

    async def query_for_existing_hashes(self, hash_key: str) -> bool:
        
        if not hash_key or not hash_key.strip():
            return False
        
        if not hash_key or not hash_key.strip():
            return False

        return await self.model.filter(api_key=hash_key).exists()

    async def save_api_key(self, create_model: APIKeyRequestDTO) -> APIKeyResponseDTO:
        data = await self.model.create(**asdict(create_model))
        return self.model_mapper.map_model_to_dataclass(data, APIKeyResponseDTO)

    async def set_inactive_by_user_id_and_api_key_id(
        self, user_id: str, api_key_id: uuid.UUID
    ) -> int:
        if (not user_id or not user_id.strip()) or not api_key_id:
            return -1

        return await self.model.filter(
            user_id=user_id, id=api_key_id, is_active=True
        ).update(is_active=False)

    async def get_all_api_keys(self, user_id: str) -> List[APIKeyResponseDTO]:

        if not user_id or not user_id.strip():
            return []

        data = (
            await self.model.filter(user_id=user_id, is_active=True)
            .order_by("-created_at")
            .all()
        )
        
        return self.model_mapper.map_models_to_dataclasses_list(data, APIKeyResponseDTO)


