from abc import abstractmethod
from dataclasses import asdict
from typing import List, Protocol

from tortoise.exceptions import DoesNotExist, IntegrityError

from models_src.dto.repo import RepoRequestDTO, RepoResponseDTO
from models_src.dto.utils import TortoiseModelMapper
from models_src.exceptions.utils import internal_error, RepoErrors
from models_src.models import Repo


class IRepoStore(Protocol):

    @abstractmethod
    async def save(self, repo_model: RepoRequestDTO) -> RepoResponseDTO: ...
    
    @abstractmethod
    async def get_by_id(self, repo_id: str) -> RepoResponseDTO: ...
    
    @abstractmethod
    async def get_all_by_user_id(
        self, user_id: str, offset: int, limit: int
    ) -> List[RepoResponseDTO]: ...

    @abstractmethod
    async def count_by_user_id(self, user_id: str) -> int: ...

class TortoiseRepoStore(IRepoStore):

    model = Repo
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

    async def get_all_by_user_id(
        self, user_id: str, offset: int, limit: int
    ) -> List[RepoResponseDTO]:

        list_raw_data = (
            await self.model.filter(user_id=user_id)
            .order_by("-created_at")
            .offset(offset)
            .limit(limit)
            .all()
        )

        return self.model_mapper.map_models_to_dataclasses_list(list_raw_data, RepoResponseDTO)

    async def count_by_user_id(self, user_id: str) -> int:
        return await self.model.filter(user_id=user_id).count()

    async def save(self, repo: RepoRequestDTO) -> RepoResponseDTO:

        try:
            saved_raw_data = await self.model.create(**asdict(repo))
            return self.model_mapper.map_model_to_dataclass(saved_raw_data, RepoResponseDTO)
        except IntegrityError as e:
            raise internal_error(**RepoErrors.REPOSITORY_ALREADY_EXIST.value) from e

    async def get_by_id(self, repo_id: str) -> RepoResponseDTO:
        try:
            raw_data = await self.model.get(id=repo_id)
        except DoesNotExist as e:
            raise internal_error(
                **RepoErrors.REPOSITORY_DOESNT_EXIST.value
            ) from e

        return self.model_mapper.map_model_to_dataclass(raw_data, RepoResponseDTO)
