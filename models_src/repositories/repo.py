import datetime
from abc import abstractmethod
from dataclasses import asdict
from typing import List, Optional, Protocol

from tortoise.exceptions import DoesNotExist, IntegrityError

from models_src.dto.repo import RepoRequestDTO, RepoResponseDTO
from models_src.dto.utils import TortoiseModelMapper
from models_src.exceptions.utils import internal_error, RepoErrors
from models_src.models import Repo


class IRepoStore(Protocol):

    @abstractmethod
    async def save(self, repo_model: RepoRequestDTO) -> RepoResponseDTO: ...

    @abstractmethod
    async def save_context(
        self, repo_id: str, user_id: str, config: dict
    ) -> RepoResponseDTO: ...

    @abstractmethod
    async def get_by_id(self, repo_id: str) -> RepoResponseDTO: ...

    @abstractmethod
    async def find_by_repo_id(self, repo_id: str) -> Optional[RepoResponseDTO]: ...

    @abstractmethod
    async def find_by_id(self, id: str) -> Optional[RepoResponseDTO]: ...

    @abstractmethod
    async def find_by_user_id_and_html_url(
        self, user_id: str, html_url: str
    ) -> Optional[RepoResponseDTO]: ...

    @abstractmethod
    async def find_all_by_user_id(
        self, user_id: str, offset: int, limit: int
    ) -> List[RepoResponseDTO]: ...

    @abstractmethod
    async def count_by_user_id(self, user_id: str) -> int: ...
    
    @abstractmethod
    async def update_analysis_metadata_by_id(
            self,
            id: str,
            status: str,
            processing_end_time: datetime.datetime,
            total_files: int,
            total_chunks: int,
            total_embeddings: int,
    ) -> int: ...
    
    @abstractmethod
    async def update_repo_system_reference_by_id(
        self, id: str, repo_system_reference: str
    ) -> int: ...
    
    @abstractmethod
    async def find_by_user_and_path(self, user_id: str, relative_path: str) -> RepoResponseDTO: ...

    @abstractmethod
    async def find_by_user_and_alias_name(
            self, user_id: str, repo_alias_name: str
    ) -> RepoResponseDTO: ...

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

    async def find_all_by_user_id(
        self, user_id: str, offset: int, limit: int
    ) -> List[RepoResponseDTO]:

        list_raw_data = (
            await self.model.filter(user_id=user_id)
            .order_by("-created_at")
            .offset(offset * limit)
            .limit(limit)
            .all()
        )

        return self.model_mapper.map_models_to_dataclasses_list(
            list_raw_data, RepoResponseDTO
        )

    async def count_by_user_id(self, user_id: str) -> int:
        return await self.model.filter(user_id=user_id).count()

    async def save(self, repo: RepoRequestDTO) -> RepoResponseDTO:

        try:
            saved_raw_data = await self.model.create(**asdict(repo))
            return self.model_mapper.map_model_to_dataclass(
                saved_raw_data, RepoResponseDTO
            )
        except IntegrityError as e:
            raise internal_error(**RepoErrors.REPOSITORY_ALREADY_EXIST.value) from e

    async def save_context(
        self, repo_id: str, user_id: str, config: dict
    ) -> RepoResponseDTO:
        raw_data = await Repo.create(
            repo_id=repo_id, user_id=user_id, config=config, status="pending"
        )
        return self.model_mapper.map_model_to_dataclass(raw_data, RepoResponseDTO)

    async def get_by_id(self, repo_id: str) -> RepoResponseDTO:
        try:
            raw_data = await self.model.get(id=repo_id)
        except DoesNotExist as e:
            raise internal_error(**RepoErrors.REPOSITORY_DOESNT_EXIST.value) from e

        return self.model_mapper.map_model_to_dataclass(raw_data, RepoResponseDTO)

    async def find_by_repo_id(self, repo_id: str) -> Optional[RepoResponseDTO]:
        raw_data = await self.model.filter(repo_id=repo_id).first()
        return self.model_mapper.map_model_to_dataclass(raw_data, RepoResponseDTO)

    async def find_by_id(self, id: str) -> Optional[RepoResponseDTO]:
        raw_data = await Repo.filter(id=id).first()
        return self.model_mapper.map_model_to_dataclass(raw_data, RepoResponseDTO)

    async def find_by_user_id_and_html_url(
        self, user_id: str, html_url: str
    ) -> Optional[RepoResponseDTO]:
        raw_data = await self.model.filter(user_id=user_id, html_url=html_url).first()
        return self.model_mapper.map_model_to_dataclass(raw_data, RepoResponseDTO)
    
    async def update_analysis_metadata_by_id(
            self,
            id: str,
            status: str,
            processing_end_time: datetime.datetime,
            total_files: int,
            total_chunks: int,
            total_embeddings: int,
    ) -> int:
        if (not id or not id.strip()) or (not status or not status.strip()):
            return -1
        
        updated_count = await self.model.filter(id=id).update(
            status=status,
            processing_end_time=processing_end_time,
            total_files=total_files,
            total_chunks=total_chunks,
            total_embeddings=total_embeddings,
        )
        
        return updated_count

    async def update_repo_system_reference_by_id(
        self, id: str, repo_system_reference: str
    ) -> int:
        if (
            not id
            or not id.strip()
            or not repo_system_reference
            or not repo_system_reference.strip()
        ):
            return -1

        return await self.model.filter(id=id).update(
            repo_system_reference=repo_system_reference
        )

    async def find_by_user_and_path(
        self, user_id: str, relative_path: str
    ) -> RepoResponseDTO:
        raw_data= await Repo.filter(user_id=user_id, relative_path=relative_path).first()
        return self.model_mapper.map_model_to_dataclass(raw_data, RepoResponseDTO)

    async def find_by_user_and_alias_name(
            self, user_id: str, repo_alias_name: str
    ) -> RepoResponseDTO:
        raw_data = await Repo.filter(user_id=user_id, repo_alias_name=repo_alias_name).first()
        return self.model_mapper.map_model_to_dataclass(raw_data, RepoResponseDTO)