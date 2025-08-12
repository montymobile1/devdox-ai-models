import datetime
import uuid
from dataclasses import asdict
from typing import Any, List, Optional, Tuple
from uuid import uuid4

from models_src.dto.api_key import APIKeyRequestDTO, APIKeyResponseDTO
from models_src.repositories.api_key import IApiKeyStore


class FakeApiKeyStore(IApiKeyStore):
    
    def __init__(self):
        self.data_store: dict[Any, List[APIKeyResponseDTO]] = {}
        self.existing_hash_set = set()
        self.total_count = 0
        self.received_calls = []
        self.exceptions = {}

    def __utility(self, method, received_calls:Tuple):

        method_name = method.__name__

        if method_name in self.exceptions:
            raise self.exceptions[method_name]

        self.received_calls.append((method_name, ) +  received_calls)

    def __get_data_store(self, user_id=None):

        if user_id:
            return self.data_store.get(user_id) or []

        return self.data_store

    def __set_data_store(self, data:APIKeyResponseDTO):
        self.data_store.setdefault(data.user_id, []).append(data)

    def set_fake_data(self, fake_data: list[APIKeyResponseDTO]):
        for data in fake_data:
            self.__set_data_store(data)
            self.existing_hash_set.add(data.api_key)

        full_total = 0
        for values in self.data_store.values():
            full_total = full_total + len(values)

        self.total_count = full_total

    def set_exception(self, method, exception: Exception):
        method_name = method.__name__
        self.exceptions[method_name] = exception

    async def exists_by_hash_key(self, hash_key: str) -> bool:
        self.__utility(self.exists_by_hash_key, (hash_key,))
        return hash_key in self.existing_hash_set

    async def save(self, create_model: APIKeyRequestDTO) -> APIKeyResponseDTO:
        self.__utility(self.exists_by_hash_key, (create_model,))

        response = APIKeyResponseDTO(**asdict(create_model))
        response.id = uuid4()
        response.created_at = datetime.datetime.now(datetime.timezone.utc)
        
        self.__set_data_store(response)
        self.existing_hash_set.add(response.api_key)
        self.total_count += 1

        return response

    async def update_is_active_by_user_id_and_api_key_id(self, user_id, api_key_id, is_active) -> int:
        self.__utility(self.update_is_active_by_user_id_and_api_key_id, (user_id, api_key_id,))

        if not user_id or not user_id.strip() or not api_key_id:
            return -1

        updated = 0
        
        data:list = self.__get_data_store(user_id=user_id)
        
        for index, value in enumerate(data):
            if uuid.UUID(value.api_key) == api_key_id and value.is_active:
                value.is_active = is_active
                updated += 1
        return updated

    async def find_all_by_user_id(self, user_id) -> List[APIKeyResponseDTO]:
        self.__utility(
            self.find_all_by_user_id,
            (
                user_id,
            ),
        )

        if not user_id or not user_id.strip():
            return []
        
        data:list = self.__get_data_store(user_id=user_id)
        
        if not data:
            return []
        
        sorted_data = sorted(
            [
                value
                for value in data
                if value.is_active
            ],
            key=lambda k: k.created_at,
            reverse=True,
        )
        
        return sorted_data
    
    async def find_first_by_api_key_and_is_active(self, api_key: str, is_active=True) -> Optional[APIKeyResponseDTO]:
        self.__utility(
            self.find_first_by_api_key_and_is_active,
            (
                api_key,
                is_active,
            ),
        )
        
        data = self.__get_data_store()
        
        if not data:
            return None
        
        discovered_result = None
        for val in data.values():
            for i in val:
                if i.api_key == api_key and i.is_active == is_active:
                    discovered_result = i
                    break
            
            if discovered_result:
                break
        
        return discovered_result
    
    async def update_last_used_by_id(self, id: str) -> int:
        
        self.__utility(
            self.update_last_used_by_id,
            (
                id,
            ),
        )
        
        
        data = self.__get_data_store()
        updated = 0
        
        if not data:
            return updated
        
        for val in data.values():
            for i in val:
                if i.id == uuid.UUID(id):
                    updated+=1
                    i.last_used = datetime.datetime.now(datetime.timezone.utc)
        
        return updated
    
    async def get_all_by_user_id(self, user_id) -> List[APIKeyResponseDTO]:
        self.__utility(
            self.get_all_by_user_id,
            (
                user_id,
            ),
        )
        
        data = self.__get_data_store(user_id=user_id)
        
        return data