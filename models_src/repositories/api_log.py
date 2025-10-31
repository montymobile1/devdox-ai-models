from abc import abstractmethod
from dataclasses import asdict
from typing import Protocol

from models_src.dto.api_log import ApiLogRequestDTO, ApiLogResponseDTO
from models_src.dto.utils import TortoiseModelMapper
from models_src.models.api_log import ApiLog


class IApiLogStore(Protocol):

    @abstractmethod
    async def save(self, create_model: ApiLogRequestDTO) -> ApiLogResponseDTO: ...

class TortoiseApiLogStore(IApiLogStore):

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