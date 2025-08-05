from dataclasses import asdict
from typing import Any, List, Tuple
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
            return self.data_store.get(user_id)

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

    def set_exception(self, method_name: str, exception: Exception):
        self.exceptions[method_name] = exception

    async def query_for_existing_hashes(self, hash_key: str) -> bool:
        self.__utility(self.query_for_existing_hashes, (hash_key, ))
        return hash_key in self.existing_hash_set

    async def save_api_key(self, create_model: APIKeyRequestDTO) -> APIKeyResponseDTO:
        self.__utility(self.query_for_existing_hashes, (create_model,))

        response = APIKeyResponseDTO(**asdict(create_model))
        response.id = uuid4()

        self.__set_data_store(response)
        self.total_count += 1

        return response

    async def set_inactive_by_user_id_and_api_key_id(self, user_id, api_key_id) -> int:
        self.__utility(self.set_inactive_by_user_id_and_api_key_id, (user_id,api_key_id,))

        if not user_id or not user_id.strip() or not api_key_id:
            return -1

        updated = 0
        
        data:list = self.__get_data_store(user_id=user_id)
        
        for index, value in enumerate(data):
            if value.id == api_key_id and value.is_active:
                value.is_active = False
                updated += 1
        return updated

    async def get_all_api_keys(self, user_id) -> List[APIKeyResponseDTO]:
        self.__utility(
            self.get_all_api_keys,
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
