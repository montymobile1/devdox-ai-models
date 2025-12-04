import datetime
import uuid
from abc import abstractmethod
from dataclasses import asdict
from typing import Any, Collection, Dict, List, Optional, Protocol, Union
from uuid import UUID

from beanie.odm.operators.find.comparison import In
from pymongo.errors import DuplicateKeyError
from tortoise.exceptions import IntegrityError

from models_src.dto.git_label import GitLabelRequestDTO, GitLabelResponseDTO
from models_src.dto.utils import BeanieModelMapper, TortoiseModelMapper
from models_src.exceptions.utils import GitLabelErrors, internal_error
from models_src.models.tortoise_orm.git_label import GitLabel
from models_src.models.beanie_odm.git_label_document import GitLabel as GitLabelDocument, GitLabelProjection

# --------------------------------------------------
# Specification
# --------------------------------------------------

class ILabelStore(Protocol):

    @abstractmethod
    async def save(self, label_model: GitLabelRequestDTO) -> GitLabelResponseDTO: ...

    @abstractmethod
    async def find_git_hostings_by_ids(
        self, token_ids: Collection[Union[str, UUID]]
    ) -> List[Dict]: ...

    @abstractmethod
    async def find_by_token_id_and_user(
        self, token_id: str, user_id: str
    ) -> GitLabelResponseDTO | None: ...

    @abstractmethod
    async def find_by_id_and_user_id_and_git_hosting(
        self, id: str, user_id: str, git_hosting: str
    ) -> Optional[GitLabelResponseDTO]: ...

    @abstractmethod
    async def find_all_by_user_id(
        self, offset, limit, user_id, git_hosting: Optional[str] = None
    ) -> list[GitLabelResponseDTO]: ...
    
    @abstractmethod
    async def count_by_user_id(
            self, user_id, git_hosting: Optional[str] = None
    ) -> int: ...
    
    @abstractmethod
    async def find_all_by_user_id_and_label(
        self, offset, limit, user_id, label: str
    ) -> list[GitLabelResponseDTO]: ...

    @abstractmethod
    async def count_by_user_id_and_label(self, user_id, label: str) -> int: ...

    @abstractmethod
    async def delete_by_id_and_user_id(
        self, label_id: uuid.UUID, user_id: str
    ) -> int: ...

# --------------------------------------------------
# Base Store
# --------------------------------------------------

class GitLabelStore(ILabelStore):
    
    def __init__(self, storage_backend:ILabelStore):
        self._storage_backend = storage_backend
    
    async def save(self, label_model: GitLabelRequestDTO) -> GitLabelResponseDTO:
        try:
            return await self._storage_backend.save(label_model=label_model)
        except (DuplicateKeyError, IntegrityError) as e:
            # unique compound index violation
            raise internal_error(**GitLabelErrors.GIT_LABEL_ALREADY_EXISTS.value) from e
    
    async def find_git_hostings_by_ids(
            self, token_ids: Collection[Union[str, UUID]]
    ) -> List[Dict]:
        if not token_ids:
            return []
        
        return await self._storage_backend.find_git_hostings_by_ids(token_ids=token_ids)
    
    
    async def find_by_token_id_and_user(
            self, token_id: str, user_id: str
    ) -> GitLabelResponseDTO | None:
        if not token_id or not token_id.strip() or not user_id or not user_id.strip():
            return None
        
        try:
            UUID(token_id)
        except ValueError:
            return None
        
        return await self._storage_backend.find_by_token_id_and_user(token_id=token_id, user_id=user_id)
    
    async def find_by_id_and_user_id_and_git_hosting(
            self, id: str, user_id: str, git_hosting: str
    ) -> Optional[GitLabelResponseDTO]:
        if not id or not id.strip() or not user_id or not user_id.strip() or not git_hosting or not git_hosting.strip():
            return None
        
        try:
            UUID(id)
        except ValueError:
            return None
        
        return await self._storage_backend.find_by_id_and_user_id_and_git_hosting(
            id=id, user_id=user_id, git_hosting=git_hosting
        )
    
    async def find_all_by_user_id(
            self, offset, limit, user_id, git_hosting: Optional[str] = None
    ) -> list[GitLabelResponseDTO]:
        
        if not user_id or not user_id.strip():
            raise internal_error(**GitLabelErrors.MISSING_USER_ID.value)
        
        return await self._storage_backend.find_all_by_user_id(offset=offset, limit=limit, user_id=user_id, git_hosting=git_hosting)
    
    async def count_by_user_id(self, user_id, git_hosting: Optional[str] = None) -> int:
        if not user_id or not user_id.strip():
            raise internal_error(**GitLabelErrors.MISSING_USER_ID.value)
        return await self._storage_backend.count_by_user_id(user_id=user_id, git_hosting=git_hosting)
    
    async def find_all_by_user_id_and_label(
            self, offset, limit, user_id, label: str
    ) -> list[GitLabelResponseDTO]:
        if not user_id:
            raise internal_error(**GitLabelErrors.MISSING_USER_ID.value)
        
        if not label or not label.strip():
            raise internal_error(**GitLabelErrors.MISSING_LABEL.value)
        
        return await self._storage_backend.find_all_by_user_id_and_label(
            offset=offset, limit=limit, user_id=user_id, label=label
        )
    
    async def count_by_user_id_and_label(self, user_id, label: str) -> int:
        if not user_id:
            raise internal_error(**GitLabelErrors.MISSING_USER_ID.value)
        
        if not label or not label.strip():
            raise internal_error(**GitLabelErrors.MISSING_LABEL.value)
        
        return await self._storage_backend.count_by_user_id_and_label(user_id=user_id, label=label)
    
    async def delete_by_id_and_user_id(self, label_id: uuid.UUID, user_id: str) -> int:
        if not label_id or not user_id or not user_id.strip():
            return -1
        # accept strings too (tests sometimes pass str)
        try:
            UUID(str(label_id))
        except ValueError:
            return -1
        
        return await self._storage_backend.delete_by_id_and_user_id(label_id=label_id, user_id=user_id)

# --------------------------------------------------
# Storage Backend
# --------------------------------------------------

class TortoiseGitLabelBackend(ILabelStore):

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

    model = GitLabel
    model_mapper = TortoiseModelMapper

    async def find_git_hostings_by_ids(
        self, token_ids: Collection[Union[str, UUID]]
    ) -> List[Dict]:
        
        return await self.model.filter(id__in=token_ids).values("id", "git_hosting")

    async def find_by_token_id_and_user(
        self, token_id: str, user_id: str
    ) -> GitLabelResponseDTO | None:
        model = await self.model.filter(id=token_id, user_id=user_id).first()
        return self.model_mapper.map_model_to_dataclass(model, GitLabelResponseDTO)

    def __find_by_user_id_query(self, user_id, git_hosting: Optional[str] = None):
        query = self.model.filter(user_id=user_id)

        if git_hosting:
            query = query.filter(git_hosting=git_hosting)

        return query

    async def find_all_by_user_id(
        self, offset, limit, user_id, git_hosting: Optional[str] = None
    ) -> list[GitLabelResponseDTO]:
        query = self.__find_by_user_id_query(user_id, git_hosting)

        git_labels = (
            await query.order_by("-created_at")
            .offset(offset * limit)
            .limit(limit)
            .all()
        )

        return self.model_mapper.map_models_to_dataclasses_list(
            git_labels, GitLabelResponseDTO
        )

    async def count_by_user_id(self, user_id, git_hosting: Optional[str] = None) -> int:
        query = self.__find_by_user_id_query(user_id, git_hosting)

        return await query.count()

    def __find_by_user_id_and_label_query(self, user_id, label: str):
        query = self.model.filter(user_id=user_id, label__icontains=label)

        return query

    async def count_by_user_id_and_label(self, user_id, label: str) -> int:

        query = self.__find_by_user_id_and_label_query(user_id, label)
        return await query.count()

    async def find_all_by_user_id_and_label(
        self, offset, limit, user_id, label: str
    ) -> list[GitLabelResponseDTO]:

        query = self.__find_by_user_id_and_label_query(user_id, label)

        git_labels = (
            await query.order_by("-created_at")
            .offset(offset * limit)
            .limit(limit)
            .all()
        )

        return self.model_mapper.map_models_to_dataclasses_list(
            git_labels, GitLabelResponseDTO
        )

    async def save(self, label_model: GitLabelRequestDTO) -> GitLabelResponseDTO:

        model = await self.model.create(**asdict(label_model))

        return self.model_mapper.map_model_to_dataclass(model, GitLabelResponseDTO)


    async def delete_by_id_and_user_id(self, label_id: uuid, user_id: str) -> int:
        """
        .delete returns 0 when No record is found or total number of records deleted.
        """
        number_of_effected_rows = await self.model.filter(
            id=label_id, user_id=user_id
        ).delete()

        return number_of_effected_rows

    async def find_by_id_and_user_id_and_git_hosting(
        self, id: str, user_id: str, git_hosting: str
    ) -> Optional[GitLabelResponseDTO]:
        raw_data = await GitLabel.filter(
            id=id, user_id=user_id, git_hosting=git_hosting
        ).first()

        return self.model_mapper.map_model_to_dataclass(raw_data, GitLabelResponseDTO)

class BeanieGitLabelBackend(ILabelStore):
    model = GitLabelDocument
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

    async def save(self, label_model: GitLabelRequestDTO) -> GitLabelResponseDTO:
        doc = self.model(**asdict(label_model))
        saved = await doc.create()
        return self.model_mapper.map_document_to_dataclass(saved, GitLabelResponseDTO)

    async def find_git_hostings_by_ids(
        self, token_ids: Collection[Union[str, UUID]]
    ) -> List[Dict]:
        uuids: List[UUID] = []
        for t in token_ids:
            if isinstance(t, UUID):
                uuids.append(t)
            else:
                try:
                    uuids.append(UUID(str(t)))
                except Exception:
                    # ignore unparseable ids
                    continue

        if not uuids:
            return []

        # project only needed fields
        docs = await self.model.find(In(self.model.id, uuids)).project(GitLabelProjection).to_list()
        
        
        return [{"id": d.id, "git_hosting": d.git_hosting} for d in docs]

    async def find_by_token_id_and_user(
        self, token_id: str, user_id: str
    ) -> GitLabelResponseDTO | None:
        doc = await self.model.find(
            self.model.id == uuid.UUID(token_id), self.model.user_id == user_id
        ).first_or_none()
        return self.model_mapper.map_document_to_dataclass(doc, GitLabelResponseDTO)

    async def find_by_id_and_user_id_and_git_hosting(
        self, id: str, user_id: str, git_hosting: str
    ) -> Optional[GitLabelResponseDTO]:
        doc = await self.model.find(
            self.model.id == uuid.UUID(id),
            self.model.user_id == user_id,
            self.model.git_hosting == git_hosting,
        ).first_or_none()
        return self.model_mapper.map_document_to_dataclass(doc, GitLabelResponseDTO)

    def __find_by_user_id_query(self, user_id: str, git_hosting: Optional[str] = None):
        q = self.model.find(self.model.user_id == user_id)
        if git_hosting:
            q = q.find(self.model.git_hosting == git_hosting)
        return q

    async def find_all_by_user_id(
        self, offset, limit, user_id, git_hosting: Optional[str] = None
    ) -> list[GitLabelResponseDTO]:
        q = self.__find_by_user_id_query(user_id, git_hosting)
        docs = await q.sort(-self.model.created_at).skip(offset * limit).limit(limit).to_list()
        return self.model_mapper.map_documents_to_dataclasses_list(docs, GitLabelResponseDTO)

    async def count_by_user_id(self, user_id, git_hosting: Optional[str] = None) -> int:
        q = self.__find_by_user_id_query(user_id, git_hosting)
        return await q.count()

    def __find_by_user_id_and_label_query(self, user_id: str, label: str):
        # case-insensitive contains
        regex_label_filter = {"$regex": label, "$options": "i"}
        
        return self.model.find(
            {
                "label": regex_label_filter,
                "user_id": user_id,
            }
        )

    async def count_by_user_id_and_label(self, user_id, label: str) -> int:
        q = self.__find_by_user_id_and_label_query(user_id, label)
        return await q.count()

    async def find_all_by_user_id_and_label(
        self, offset, limit, user_id, label: str
    ) -> list[GitLabelResponseDTO]:
        q = self.__find_by_user_id_and_label_query(user_id, label)
        docs = await q.sort(-self.model.created_at).skip(offset * limit).limit(limit).to_list()
        return self.model_mapper.map_documents_to_dataclasses_list(docs, GitLabelResponseDTO)

    async def delete_by_id_and_user_id(self, label_id: uuid.UUID, user_id: str) -> int:
        res = await self.model.find(
            self.model.id == label_id, self.model.user_id == user_id
        ).delete()
        # Beanie returns a DeleteResult (PyMongo) in v2; fall back to 0 if None
        return getattr(res, "deleted_count", 0) if res is not None else 0

class InMemoryGitLabelBackend(ILabelStore):
    
    store_cls = GitLabelStore
    
    def __init__(self):
        self.__data_store: dict[Any, List[GitLabelResponseDTO]] = {}
        self.total_count = 0
    
    @property
    def data_store(self):
        return self.__data_store
    
    def get_data_store(self, user_id=None):

        if user_id:
            return self.__data_store.get(user_id, [])

        return self.__data_store

    def add_record(self, data: GitLabelResponseDTO):
        self.__data_store.setdefault(data.user_id, []).append(data)

    def set_data_store(self, fake_data: List[GitLabelResponseDTO]):
        for data in fake_data:
            self.add_record(data)

        full_total = 0
        for values in self.__data_store.values():
            full_total = full_total + len(values)

        self.total_count = full_total
    
    async def save(self, label_model: GitLabelRequestDTO) -> GitLabelResponseDTO:
        retrieved_data = self.get_data_store(user_id=label_model.user_id)
        
        found = False
        for record in retrieved_data:
            if (
                    record.git_hosting == label_model.git_hosting
                    and record.masked_token == label_model.masked_token
            ):
                found = True
                break
        
        if found:
            raise DuplicateKeyError("Duplicate key")
        
        now = datetime.datetime.now(datetime.timezone.utc)
        
        result = GitLabelResponseDTO(**asdict(label_model))
        result.id = uuid.uuid4()
        result.created_at = now
        result.updated_at = now
        
        self.add_record(data=result)
        self.total_count += 1
        
        return result
    
    
    async def find_git_hostings_by_ids(
        self, token_ids: Collection[Union[str, UUID]]
    ) -> List[Dict]:
        match_list = []
        
        normalized_ids = {str(t) for t in token_ids}
        
        for key, obj_list in self.__data_store.items():
            matches = [obj for obj in obj_list if str(obj.id) in normalized_ids]
            for match in matches:
                match_list.append({"id": match.id, "git_hosting": match.git_hosting})

        return match_list

    async def find_by_token_id_and_user(
        self, token_id: str, user_id: str
    ) -> GitLabelResponseDTO | None:
        user_id_data = self.get_data_store(user_id=user_id)

        result = None
        for record in user_id_data:
            if str(record.id) == token_id:
                result = record
                break

        return result

    async def find_by_id_and_user_id_and_git_hosting(
        self, id: str, user_id: str, git_hosting: str
    ) -> Optional[GitLabelResponseDTO]:

        data = self.get_data_store(user_id=user_id)

        match = None

        for record in data:
            if str(record.id) == id and record.git_hosting == git_hosting:
                match = record
                break

        return match
    
    
    async def find_all_by_user_id(
            self, offset, limit, user_id, git_hosting: Optional[str] = None
    ) -> list[GitLabelResponseDTO]:
        data = list(self.get_data_store(user_id=user_id) or [])
        
        # optional git_hosting filter – to match Tortoise/Beanie semantics
        if git_hosting:
            data = [r for r in data if r.git_hosting == git_hosting]
        
        # order by created_at DESC (fallback if created_at is None)
        data.sort(
            key=lambda r: r.created_at or datetime.datetime.min,
            reverse=True,
        )
        
        # page index semantics, like .offset(offset * limit)
        start = offset * limit
        end = start + limit
        return data[start:end]
    
    
    async def count_by_user_id(self, user_id, git_hosting: Optional[str] = None) -> int:
        data = self.get_data_store(user_id=user_id) or []
        
        if git_hosting:
            data = [r for r in data if r.git_hosting == git_hosting]
        
        return len(data)
    
    async def find_all_by_user_id_and_label(
            self, offset, limit, user_id, label: str
    ) -> list[GitLabelResponseDTO]:
        data = self.get_data_store(user_id=user_id) or []
        
        needle = label.lower()
        filtered = [
            r for r in data
            if r.label and needle in r.label.lower()
        ]
        
        # order by created_at DESC
        filtered.sort(
            key=lambda r: r.created_at or datetime.datetime.min,
            reverse=True,
        )
        
        start = offset * limit
        end = start + limit
        return filtered[start:end]
    
    
    async def count_by_user_id_and_label(self, user_id, label: str) -> int:
        data = self.get_data_store(user_id=user_id) or []
        
        needle = label.lower()
        filtered = [
            r for r in data
            if r.label and needle in r.label.lower()
        ]
        return len(filtered)

    async def delete_by_id_and_user_id(self, label_id: uuid.UUID, user_id: str) -> int:
        data = self.get_data_store(user_id=user_id)
        initial_count = len(data) if data else 0

        if initial_count == 0:
            return 0

        indexes = []
        for index, item in enumerate(data):
            if item.id == label_id:
                indexes.append(index)
                self.total_count -= 1

        if indexes:
            for index in sorted(indexes, reverse=True):
                data.pop(index)

        return initial_count - len(data)

# --------------------------------------------------
# Factory
# --------------------------------------------------

def get_active_git_label_store():
    return GitLabelStore(storage_backend=BeanieGitLabelBackend())