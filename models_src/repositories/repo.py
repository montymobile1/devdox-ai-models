import datetime
import uuid
from abc import abstractmethod
from dataclasses import asdict
from typing import List, Optional, Protocol

from beanie.odm.operators.update.general import Set
from pymongo.errors import DuplicateKeyError
from tortoise.exceptions import DoesNotExist, IntegrityError

from models_src.dto.repo import RepoRequestDTO, RepoResponseDTO
from models_src.dto.utils import BeanieModelMapper, TortoiseModelMapper
from models_src.exceptions.utils import internal_error, RepoErrors
from models_src.models.repo_enums import StatusTypes
from models_src.models.repo import Repo
from models_src.models.repo_document import Repo as RepoDocument

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

    @abstractmethod
    async def find_by_repo_id_user_id(
            self, repo_id: str, user_id: str
    ) -> Optional[RepoResponseDTO]: ...

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

    async def find_by_repo_id_user_id(self, repo_id: str, user_id: str) -> Optional[RepoResponseDTO]:
        try:
            raw_data = await self.model.filter(repo_id=str(repo_id), user_id=user_id).first()

        except DoesNotExist as e:
            raise internal_error(**RepoErrors.REPOSITORY_DOESNT_EXIST.value) from e
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

class BeanieRepoStore(IRepoStore):
    model = RepoDocument
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

    async def save(self, repo_model: RepoRequestDTO) -> RepoResponseDTO:
        try:
            doc = self.model(**asdict(repo_model))
            data = await doc.create()
            return self.model_mapper.map_document_to_dataclass(data, RepoResponseDTO)
        except DuplicateKeyError as e:
            raise internal_error(**RepoErrors.REPOSITORY_ALREADY_EXIST.value) from e

    async def save_context(self, repo_id: str, user_id: str, config: dict) -> RepoResponseDTO:
        """
        Beanie doc has no `config` field and several required fields,
        so we update an existing repo’s status to 'pending' (context kick-off).
        """
        if (not repo_id or not repo_id.strip()) or (not user_id or not user_id.strip()):
            raise internal_error(**RepoErrors.REPOSITORY_DOESNT_EXIST.value)

        result = await self.model.find(
            self.model.user_id == user_id,
            self.model.repo_id == repo_id,
        ).update(
            Set({self.model.status: StatusTypes.PENDING})
        )

        if result.matched_count == 0:
            raise internal_error(**RepoErrors.REPOSITORY_DOESNT_EXIST.value)

        doc = await self.model.find(
            self.model.user_id == user_id,
            self.model.repo_id == repo_id,
        ).first_or_none()

        return self.model_mapper.map_document_to_dataclass(doc, RepoResponseDTO)

    async def get_by_id(self, repo_id: str) -> RepoResponseDTO:
        # repo_id here = Document._id (UUID as string)
        if not repo_id or not repo_id.strip():
            raise internal_error(**RepoErrors.REPOSITORY_DOESNT_EXIST.value)
        try:
            uuid_id = uuid.UUID(repo_id)
        except ValueError as e:
            raise internal_error(**RepoErrors.REPOSITORY_DOESNT_EXIST.value) from e

        doc = await self.model.find(self.model.id == uuid_id).first_or_none()
        if doc is None:
            raise internal_error(**RepoErrors.REPOSITORY_DOESNT_EXIST.value)
        return self.model_mapper.map_document_to_dataclass(doc, RepoResponseDTO)

    async def find_by_repo_id(self, repo_id: str) -> Optional[RepoResponseDTO]:
        doc = await self.model.find(self.model.repo_id == repo_id).first_or_none()
        return self.model_mapper.map_document_to_dataclass(doc, RepoResponseDTO)

    async def find_by_repo_id_user_id(self, repo_id: str, user_id: str) -> Optional[RepoResponseDTO]:
        doc = await self.model.find(
            self.model.repo_id == str(repo_id),
            self.model.user_id == user_id
        ).first_or_none()
        return self.model_mapper.map_document_to_dataclass(doc, RepoResponseDTO)

    async def find_by_id(self, id: str) -> Optional[RepoResponseDTO]:
        
        if not id or not id.strip():
            return None
        
        try:
            uuid_id = uuid.UUID(id)
        except ValueError:
            return None
        doc = await self.model.find(self.model.id == uuid_id).first_or_none()
        return self.model_mapper.map_document_to_dataclass(doc, RepoResponseDTO)

    async def find_by_user_id_and_html_url(
        self, user_id: str, html_url: str
    ) -> Optional[RepoResponseDTO]:
        doc = await self.model.find(
            self.model.user_id == user_id,
            self.model.html_url == html_url,
        ).first_or_none()
        return self.model_mapper.map_document_to_dataclass(doc, RepoResponseDTO)

    def __find_all_by_user_query(self, user_id: str):
        if not user_id or not user_id.strip():
            raise internal_error(**RepoErrors.MISSING_USER_ID.value)
        return self.model.find(self.model.user_id == user_id)

    async def find_all_by_user_id(self, user_id: str, offset: int, limit: int) -> List[RepoResponseDTO]:
        q = self.__find_all_by_user_query(user_id)
        docs = await q.sort(-self.model.created_at).skip(offset * limit).limit(limit).to_list()
        return self.model_mapper.map_documents_to_dataclasses_list(docs, RepoResponseDTO)

    async def count_by_user_id(self, user_id: str) -> int:
        return await self.__find_all_by_user_query(user_id).count()

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
        try:
            uuid_id = uuid.UUID(id)
        except ValueError:
            return -1

        result = await self.model.find(self.model.id == uuid_id).update(
            Set({
                self.model.status: status,
                self.model.processing_end_time: processing_end_time,
                self.model.total_files: total_files,
                self.model.total_chunks: total_chunks,
                self.model.total_embeddings: total_embeddings,
            })
        )
        return result.matched_count

    async def update_repo_system_reference_by_id(self, id: str, repo_system_reference: str) -> int:
        if (not id or not id.strip()) or (not repo_system_reference or not repo_system_reference.strip()):
            return -1
        try:
            uuid_id = uuid.UUID(id)
        except ValueError:
            return -1

        result = await self.model.find(self.model.id == uuid_id).update(
            Set({self.model.repo_system_reference: repo_system_reference})
        )
        return result.matched_count

    async def find_by_user_and_path(self, user_id: str, relative_path: str) -> Optional[RepoResponseDTO]:
        doc = await self.model.find(
            self.model.user_id == user_id, self.model.relative_path == relative_path
        ).first_or_none()
        return self.model_mapper.map_document_to_dataclass(doc, RepoResponseDTO)

    async def find_by_user_and_alias_name(self, user_id: str, repo_alias_name: str) -> Optional[RepoResponseDTO]:
        doc = await self.model.find(
            self.model.user_id == user_id, self.model.repo_alias_name == repo_alias_name
        ).first_or_none()
        return self.model_mapper.map_document_to_dataclass(doc, RepoResponseDTO)

def get_active_repo_store():
    return BeanieRepoStore()