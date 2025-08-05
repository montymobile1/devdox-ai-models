from abc import abstractmethod
from typing import Optional, Protocol

from models_src.dto.user import UserResponseDTO
from models_src.dto.utils import TortoiseModelMapper
from models_src.models import User


class IUserStore(Protocol):

    @abstractmethod
    async def find_by_user_id(self, user_id: str) -> Optional[UserResponseDTO]: ...


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

    async def find_by_user_id(self, user_id: str) -> Optional[UserResponseDTO]:
        if not user_id or not user_id.strip():
            return None

        model_data = await self.model.filter(user_id=user_id).first()
        mapped_model_to_dto = self.model_mapper.map_model_to_dataclass(model_data, UserResponseDTO)
        
        return mapped_model_to_dto