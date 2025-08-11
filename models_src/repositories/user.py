from abc import abstractmethod
from dataclasses import asdict
from typing import Optional, Protocol

from tortoise.expressions import F

from models_src.dto.user import UserRequestDTO, UserResponseDTO
from models_src.dto.utils import TortoiseModelMapper
from models_src.models import User


class IUserStore(Protocol):

    @abstractmethod
    async def find_by_user_id(self, user_id: str) -> Optional[UserResponseDTO]: ...
    
    @abstractmethod
    async def save(self, user_model: UserRequestDTO) -> UserResponseDTO: ...
    
    @abstractmethod
    async def increment_token_usage(
        self, user_id: str, tokens_used: int
    ) -> int: ...
    

class TortoiseUserStore(IUserStore):

    model = User
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

    async def save(self, user_model: UserRequestDTO) -> UserResponseDTO:
        data = await self.model.create(**asdict(user_model))
        return self.model_mapper.map_model_to_dataclass(data, UserResponseDTO)

    async def find_by_user_id(self, user_id: str) -> Optional[UserResponseDTO]:
        if not user_id or not user_id.strip():
            return None

        model_data = await self.model.filter(user_id=user_id).first()
        mapped_model_to_dto = self.model_mapper.map_model_to_dataclass(model_data, UserResponseDTO)

        return mapped_model_to_dto

    async def increment_token_usage(
        self, user_id: str, tokens_used: int
    ) -> int:
        if (not user_id or not user_id.strip()) or not tokens_used:
            return -1

        return await self.model.filter(user_id=user_id).update(token_used=F("token_used") + tokens_used)
