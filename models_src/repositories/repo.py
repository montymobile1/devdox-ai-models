import datetime
import uuid
from abc import abstractmethod
from dataclasses import asdict
from typing import Any, List, Optional, Protocol

from beanie.exceptions import DocumentNotFound
from beanie.odm.operators.update.general import Set
from pymongo.errors import DuplicateKeyError
from tortoise.exceptions import DoesNotExist, IntegrityError

from models_src.dto.repo import RepoRequestDTO, RepoResponseDTO
from models_src.dto.utils import BeanieModelMapper, TortoiseModelMapper
from models_src.exceptions import exception_constants
from models_src.exceptions.local_exception import InMemoryNotFound
from models_src.exceptions.utils import internal_error, RepoErrors
from models_src.models.common.repo_enums import StatusTypes
from models_src.models.tortoise_orm.repo import Repo
from models_src.models.beanie_odm.repo_document import Repo as RepoDocument

# --------------------------------------------------
# Specification
# --------------------------------------------------

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

# --------------------------------------------------
# Base Store
# --------------------------------------------------

class RepoStore(IRepoStore):
    
    def __init__(self, storage_backend:IRepoStore):
        self._storage_backend = storage_backend
    
    async def save(self, repo_model: RepoRequestDTO) -> RepoResponseDTO:
        try:
            return await self._storage_backend.save(repo_model=repo_model)
        except (DuplicateKeyError, IntegrityError) as e:
            raise internal_error(**RepoErrors.REPOSITORY_ALREADY_EXIST.value) from e
    
    async def save_context(self, repo_id: str, user_id: str, config: dict) -> RepoResponseDTO:
        """
        Beanie doc has no `config` field and several required fields,
        so we update an existing repo’s status to 'pending' (context kick-off).
        """
        if (not repo_id or not repo_id.strip()) or (not user_id or not user_id.strip()):
            raise internal_error(**RepoErrors.REPOSITORY_DOESNT_EXIST.value)
        
        return await self._storage_backend.save_context(repo_id=repo_id, user_id=user_id, config=config)
    
    async def get_by_id(self, repo_id: str) -> RepoResponseDTO:
        
        if not repo_id or not repo_id.strip():
            raise internal_error(**RepoErrors.REPOSITORY_DOESNT_EXIST.value)
        try:
            uuid.UUID(repo_id)
        except ValueError as e:
            raise internal_error(**RepoErrors.REPOSITORY_DOESNT_EXIST.value) from e
        
        try:
            return await self._storage_backend.get_by_id(repo_id=repo_id)
        except (DoesNotExist, DocumentNotFound, InMemoryNotFound) as e:
            raise internal_error(**RepoErrors.REPOSITORY_DOESNT_EXIST.value) from e
    
    async def find_by_repo_id(self, repo_id: str) -> Optional[RepoResponseDTO]:
        return await self._storage_backend.find_by_repo_id(repo_id=repo_id)
    
    async def find_by_repo_id_user_id(self, repo_id: str, user_id: str) -> Optional[RepoResponseDTO]:
        data = await self._storage_backend.find_by_repo_id_user_id(repo_id=repo_id, user_id=user_id)
        if not data:
            raise internal_error(**RepoErrors.REPOSITORY_DOESNT_EXIST.value)
        
        return data
    
    async def find_by_id(self, id: str) -> Optional[RepoResponseDTO]:
        
        if not id or not id.strip():
            return None
        
        try:
            uuid.UUID(id)
        except ValueError:
            return None
        
        return await self._storage_backend.find_by_id(id=id)
    
    async def find_by_user_id_and_html_url(
            self, user_id: str, html_url: str
    ) -> Optional[RepoResponseDTO]:
        return await self._storage_backend.find_by_user_id_and_html_url(user_id=user_id, html_url=html_url)
    
    
    async def find_all_by_user_id(self, user_id: str, offset: int, limit: int) -> List[RepoResponseDTO]:
        if not user_id or not user_id.strip():
            raise internal_error(**RepoErrors.MISSING_USER_ID.value)
        
        return await self._storage_backend.find_all_by_user_id(user_id=user_id, offset=offset, limit=limit)
    
    async def count_by_user_id(self, user_id: str) -> int:
        if not user_id or not user_id.strip():
            raise internal_error(**RepoErrors.MISSING_USER_ID.value)
        
        return await self._storage_backend.count_by_user_id(user_id=user_id)
    
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
            uuid.UUID(id)
        except ValueError:
            return -1
        
        return await self._storage_backend.update_analysis_metadata_by_id(
            id=id,
            status=status,
            processing_end_time=processing_end_time,
            total_files=total_files,
            total_chunks=total_chunks,
            total_embeddings=total_embeddings
        )
    
    async def update_repo_system_reference_by_id(self, id: str, repo_system_reference: str) -> int:
        if (not id or not id.strip()) or (not repo_system_reference or not repo_system_reference.strip()):
            return -1
        try:
            uuid.UUID(id)
        except ValueError:
            return -1
        
        return await self._storage_backend.update_repo_system_reference_by_id(
            id=id,
            repo_system_reference=repo_system_reference
        )
    
    async def find_by_user_and_path(self, user_id: str, relative_path: str) -> Optional[RepoResponseDTO]:
        return await self._storage_backend.find_by_user_and_path(user_id=user_id, relative_path=relative_path)
    
    async def find_by_user_and_alias_name(self, user_id: str, repo_alias_name: str) -> Optional[RepoResponseDTO]:
        return await self._storage_backend.find_by_user_and_alias_name(user_id=user_id, repo_alias_name=repo_alias_name)

# --------------------------------------------------
# Storage Backend
# --------------------------------------------------

class TortoiseRepoBackend(IRepoStore):
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
        saved_raw_data = await self.model.create(**asdict(repo))
        return self.model_mapper.map_model_to_dataclass(
            saved_raw_data, RepoResponseDTO
        )
        
    
    async def save_context(
            self, repo_id: str, user_id: str, config: dict
    ) -> RepoResponseDTO:
        raw_data = await Repo.create(
            repo_id=repo_id, user_id=user_id, config=config, status="pending"
        )
        return self.model_mapper.map_model_to_dataclass(raw_data, RepoResponseDTO)
    
    async def get_by_id(self, repo_id: str) -> RepoResponseDTO:
        raw_data = await self.model.get(id=repo_id)
        return self.model_mapper.map_model_to_dataclass(raw_data, RepoResponseDTO)
    
    async def find_by_repo_id(self, repo_id: str) -> Optional[RepoResponseDTO]:
        raw_data = await self.model.filter(repo_id=repo_id).first()
        return self.model_mapper.map_model_to_dataclass(raw_data, RepoResponseDTO)
    
    async def find_by_repo_id_user_id(self, repo_id: str, user_id: str) -> Optional[RepoResponseDTO]:
        raw_data = await self.model.filter(repo_id=str(repo_id), user_id=user_id).first()
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

class BeanieRepoBackend(IRepoStore):
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
        doc = self.model(**asdict(repo_model))
        data = await doc.create()
        return self.model_mapper.map_document_to_dataclass(data, RepoResponseDTO)
    
    async def save_context(self, repo_id: str, user_id: str, config: dict) -> RepoResponseDTO:
        """
        Beanie doc has no `config` field and several required fields,
        so we update an existing repo’s status to 'pending' (context kick-off).
        """
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
        doc = await self.model.get(document_id= uuid.UUID(repo_id))
        
        if not doc:
            raise DocumentNotFound(exception_constants.RECORD_NOT_FOUND)
        
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
        doc = await self.model.find(self.model.id == uuid.UUID(id)).first_or_none()
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

        result = await self.model.find(self.model.id == uuid.UUID(id)).update(
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
        result = await self.model.find(self.model.id == uuid.UUID(id)).update(
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

class InMemoryRepoBackend(IRepoStore):
    
    store_cls = RepoStore
    
    def __init__(self):
        self.__data_store: dict[Any, List[RepoResponseDTO]] = {}
        self.total_count = 0
    
    @property
    def data_store(self):
        return self.__data_store
    
    def get_data_store(self, user_id=None):
        if user_id:
            return self.__data_store.get(user_id, [])
        
        return self.__data_store
    
    def add_record(self, data: RepoResponseDTO):
        self.__data_store.setdefault(data.user_id, []).append(data)
    
    def set_data_store(self, fake_data: List[RepoResponseDTO]):
        for data in fake_data:
            self.add_record(data=data)
        
        full_total = 0
        for values in self.__data_store.values():
            full_total = full_total + len(values)
        
        self.total_count = full_total
    
    async def find_all_by_user_id(
            self, user_id: str, offset: int, limit: int
    ) -> List[RepoResponseDTO]:
        data = self.get_data_store(user_id=user_id)
        
        return data[offset : offset + limit]
    
    async def count_by_user_id(self, user_id: str) -> int:
        data = self.get_data_store(user_id=user_id)
        
        return len(data)
    
    async def save(self, repo_model: RepoRequestDTO) -> RepoResponseDTO:
        response = RepoResponseDTO(**asdict(repo_model))
        response.id = uuid.uuid4()
        
        self.add_record(data=response)
        
        self.total_count += 1
        
        return response
    
    async def get_by_id(self, repo_id: str) -> RepoResponseDTO:
        match = None
        for key, obj_list in self.get_data_store().items():
            match = next(
                (obj for obj in obj_list if obj.id == uuid.UUID(repo_id)), None
            )
            if match:
                break
        
        if not match:
            raise InMemoryNotFound(exception_constants.RECORD_NOT_FOUND)
        
        return match
    
    async def find_by_repo_id(self, repo_id: str) -> Optional[RepoResponseDTO]:

        match = None
        for key, obj_list in self.get_data_store().items():
            match = next((obj for obj in obj_list if obj.repo_id == repo_id), None)
            if match:
                break
        
        return match
    
    async def find_by_repo_id_user_id(self, repo_id: str, user_id: str) -> Optional[RepoResponseDTO]:
        user_repos = self.get_data_store(user_id=user_id)
        
        match = next((obj for obj in user_repos if obj.repo_id == repo_id), None)
        return match
    
    async def find_by_id(self, id: str) -> Optional[RepoResponseDTO]:
        match = None
        for key, obj_list in self.get_data_store().items():
            match = next((obj for obj in obj_list if str(obj.id == id)), None)
            if match:
                break
        
        return match
    
    async def update_analysis_metadata_by_id(
            self,
            id: str,
            status: str,
            processing_end_time: datetime.datetime,
            total_files: int,
            total_chunks: int,
            total_embeddings: int,
    ) -> int:
        data = self.get_data_store()

        updated = 0
        for key, obj_list in data.items():
            match = next((obj for obj in obj_list if str(obj.id) == id), None)
            if match:
                match.status = status
                match.processing_end_time = processing_end_time
                match.total_files = total_files
                match.total_chunks = total_chunks
                match.total_embeddings = total_embeddings
                updated += 1
                break
        
        return updated
    
    async def find_by_user_id_and_html_url(
            self, user_id: str, html_url: str
    ) -> Optional[RepoResponseDTO]:

        match = None
        
        data: List[RepoResponseDTO] = self.get_data_store(user_id=user_id)
        
        for obj in data:
            if obj.html_url == html_url:
                match = obj
                return match
        
        return match
    
    async def save_context(
            self, repo_id: str, user_id: str, config: dict
    ) -> RepoResponseDTO:
        """
        config: Ignore since it is only applicable to Tortoise ORM
        """

        response = RepoResponseDTO(repo_id=repo_id, user_id=user_id, status="pending")
        response.id = uuid.uuid4()
        
        self.add_record(data=response)
        
        self.total_count += 1
        
        return response
    
    async def update_repo_system_reference_by_id(
            self, id: str, repo_system_reference: str
    ) -> int:

        data = self.get_data_store()
        
        updated = 0
        for key, obj_list in data.items():
            match = next((obj for obj in obj_list if str(obj.id) == id), None)
            if match:
                match.repo_system_reference = repo_system_reference
                updated += 1
                break
        
        return updated
    
    async def find_by_user_and_path(self, user_id: str, relative_path: str) -> RepoResponseDTO:
        all_data = self.get_data_store(user_id=user_id)
        
        result = None
        for data in all_data:
            if data.relative_path == relative_path:
                result = data
                break
        
        return result
    
    async def find_by_user_and_alias_name(
            self, user_id: str, repo_alias_name: str
    ) -> RepoResponseDTO:
        all_data = self.get_data_store(user_id=user_id)
        
        result = None
        for data in all_data:
            if hasattr(data, 'repo_alias_name') and data.repo_alias_name == repo_alias_name:
                result = data
                break
        
        return result

# --------------------------------------------------
# Factory
# --------------------------------------------------

def get_active_repo_store():
    return RepoStore(storage_backend=BeanieRepoBackend())