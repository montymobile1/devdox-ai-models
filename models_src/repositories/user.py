import datetime
import uuid
from abc import abstractmethod
from dataclasses import asdict
from typing import Any, Optional, Protocol

from beanie.exceptions import DocumentNotFound
from beanie.odm.operators.update.general import Inc, Set
from models_src.exceptions import exception_constants
from pymongo.errors import DuplicateKeyError
from tortoise.exceptions import DoesNotExist, IntegrityError
from tortoise.expressions import F

from models_src.exceptions.utils import internal_error, UserErrors
from models_src.dto.user import UserRequestDTO, UserResponseDTO
from models_src.dto.utils import BeanieModelMapper, TortoiseModelMapper
from models_src.exceptions.local_exception import InMemoryDuplicate, InMemoryNotFound, RecordNotFound
from models_src.models.tortoise_orm.user import User
from models_src.models.beanie_odm.user_document import User as UserDocument, UserSimpleProjection


# --------------------------------------------------
# Specification
# --------------------------------------------------

class IUserStore(Protocol):

    @abstractmethod
    async def find_by_user_id(self, user_id: str) -> Optional[UserResponseDTO]: ...
    
    @abstractmethod
    async def get_encryption_salt(self, user_id: str) -> str | None: ...
    
    @abstractmethod
    async def save(self, user_model: UserRequestDTO) -> UserResponseDTO: ...

    @abstractmethod
    async def increment_token_usage(self, user_id: str, tokens_used: int) -> int: ...
    
    @abstractmethod
    async def exists_by_user_id(self, user_id: str) -> bool: ...

# --------------------------------------------------
# Base Store
# --------------------------------------------------

class UserStore(IUserStore):
    
    def __init__(self, storage_backend:IUserStore):
        self._storage_backend = storage_backend
    
    async def save(self, user_model: UserRequestDTO) -> UserResponseDTO:
        try:
            return await self._storage_backend.save(user_model=user_model)
        except (DuplicateKeyError, IntegrityError, InMemoryDuplicate) as e:
            raise internal_error(**UserErrors.USER_ALREADY_EXIST.value) from e
    
    async def find_by_user_id(self, user_id: str) -> Optional[UserResponseDTO]:
        if not user_id or not user_id.strip():
            return None
        
        return await self._storage_backend.find_by_user_id(user_id=user_id)
    
    async def increment_token_usage(self, user_id: str, tokens_used: int) -> int:
        
        if (not user_id or not user_id.strip()) or not tokens_used:
            return -1
        
        return await self._storage_backend.increment_token_usage(user_id=user_id, tokens_used=tokens_used)
    
    async def exists_by_user_id(self, user_id: str) -> bool:
        if not user_id or not user_id.strip():
            return False
        
        return await self._storage_backend.exists_by_user_id(user_id=user_id)
    
    async def get_encryption_salt(self, user_id: str) -> str | None:
        if not user_id or not user_id.strip():
            raise RecordNotFound(reason=exception_constants.INVALID_PASSED_FIELDS)
        
        try:
            return await self._storage_backend.get_encryption_salt(user_id=user_id)
        except (DoesNotExist, DocumentNotFound, InMemoryNotFound) as e:
            raise RecordNotFound() from e
    
# --------------------------------------------------
# Storage Backend
# --------------------------------------------------

class TortoiseUserBackend(IUserStore):

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
        model_data = await self.model.filter(user_id=user_id).first()
        mapped_model_to_dto = self.model_mapper.map_model_to_dataclass(
            model_data, UserResponseDTO
        )

        return mapped_model_to_dto
    
    async def get_encryption_salt(self, user_id: str) -> str | None:
        instance = await self.model.get(user_id=user_id)
        return instance.encryption_salt
    
    async def increment_token_usage(self, user_id: str, tokens_used: int) -> int:
        
        now = datetime.datetime.now(datetime.timezone.utc)
        
        return await self.model.filter(user_id=user_id).update(
            token_used=F("token_used") + tokens_used,
            updated_at=now,
        )
    
    async def exists_by_user_id(self, user_id: str) -> bool:
        return await self.model.filter(user_id=user_id).exists()

class BeanieUserBackend(IUserStore):
    model = UserDocument
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

    async def save(self, user_model: UserRequestDTO) -> UserResponseDTO:
        doc = self.model(**asdict(user_model))
        data = await doc.create()
        return self.model_mapper.map_document_to_dataclass(data, UserResponseDTO)

    async def find_by_user_id(self, user_id: str) -> Optional[UserResponseDTO]:
        doc = await self.model.find(self.model.user_id == user_id).first_or_none()
        return self.model_mapper.map_document_to_dataclass(doc, UserResponseDTO)

    async def increment_token_usage(self, user_id: str, tokens_used: int) -> int:
        
        now = datetime.datetime.now(datetime.timezone.utc)
        
        result = await self.model.find(self.model.user_id == user_id).update(
            Inc({self.model.token_used: tokens_used}),
            Set({self.model.updated_at: now})
        )
        return result.matched_count
    
    async def exists_by_user_id(self, user_id: str) -> bool:
        return await self.model.find(self.model.user_id == user_id).exists()
    
    async def get_encryption_salt(self, user_id: str) -> str | None:
        enc_salt = await self.model.find_one(self.model.user_id == user_id).project(UserSimpleProjection)
        
        if not enc_salt:
            raise DocumentNotFound(exception_constants.RECORD_NOT_FOUND)
        
        return enc_salt.encryption_salt
    
class InMemoryUserBackend(IUserStore):
    
    store_cls = UserStore
    
    def __init__(self):
        self.__data_store: dict[Any, UserResponseDTO] = {}
        self.total_count = 0
    
    @property
    def data_store(self):
        return self.__data_store

    def get_data_store(self, user_id=None):
        
        if user_id:
            return self.__data_store.get(user_id)
        
        return self.__data_store
    
    def add_record(self, data: UserResponseDTO):
        if data.user_id in self.__data_store:
            # mirror DB uniqueness behavior in memory
            raise InMemoryDuplicate(reason="user_id_unique")
        self.__data_store[data.user_id] = data
    
    def set_data_store(self, fake_data: list[UserResponseDTO]):
        
        for data in fake_data:
            self.add_record(data=data)
        
        self.total_count = len(self.__data_store)
    
    async def save(self, user_model: UserRequestDTO) -> UserResponseDTO:
        result = UserResponseDTO(**asdict(user_model))
        result.id = uuid.uuid4()
        now = datetime.datetime.now(datetime.timezone.utc)
        result.created_at = now
        result.updated_at = now
        
        self.add_record(data=result)
        self.total_count += 1
        
        return result
    
    async def find_by_user_id(self, user_id: str):
        return self.get_data_store(user_id=user_id)
    
    async def increment_token_usage(self, user_id: str, tokens_used: int) -> int:
        updated = 0
        
        data: UserResponseDTO = self.get_data_store(user_id=user_id)
        
        if data:
            data.token_used += tokens_used
            data.updated_at = datetime.datetime.now(datetime.timezone.utc)
            updated += 1
        
        return updated
    
    async def exists_by_user_id(self, user_id: str) -> bool:
        res = self.get_data_store(user_id=user_id)
        
        return True if res else False
    
    async def get_encryption_salt(self, user_id: str) -> str | None:
        res = self.get_data_store(user_id=user_id)
        
        if not res:
            raise InMemoryNotFound(exception_constants.RECORD_NOT_FOUND)
        
        return res.encryption_salt
    
    
# --------------------------------------------------
# Factory
# --------------------------------------------------

def get_active_user_store():
    return UserStore(storage_backend=BeanieUserBackend())