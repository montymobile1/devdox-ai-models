import datetime
import uuid
from dataclasses import asdict
from typing import Any, Tuple

from models_src.dto.user import UserRequestDTO, UserResponseDTO
from models_src.repositories.user import IUserStore


class FakeUserStore(IUserStore):
    
    def __init__(self):
        self.data_store: dict[Any, UserResponseDTO] = {}
        self.total_count = 0
        self.received_calls = []  # for optional spy behavior
        self.exceptions = {}  # method_name -> exception to raise

    def __utility(self, method, received_calls:Tuple):

        method_name = method.__name__

        if method_name in self.exceptions:
            raise self.exceptions[method_name]

        self.received_calls.append((method_name, ) +  received_calls)

    def __get_data_store(self, user_id=None):

        if user_id:
            return self.data_store.get(user_id)

        return self.data_store

    def __set_data_store(self, data:UserResponseDTO):
        self.data_store.setdefault(data.user_id, data)

    def set_fake_data(self, fake_data: list[UserResponseDTO]):

        for data in fake_data:
            self.__set_data_store(data=data)

        self.total_count = len(self.data_store)

    def set_exception(self, method, exception: Exception):
        method_name = method.__name__
        self.exceptions[method_name] = exception
    
    async def save(self, user_model: UserRequestDTO) -> UserResponseDTO:
        self.__utility(self.save, (user_model,))
        
        result = UserResponseDTO(**asdict(user_model))
        result.id = uuid.uuid4()
        result.created_at = datetime.datetime.now(datetime.timezone.utc)
        
        self.__set_data_store(data=result)
        self.total_count += 1
        
        return result
    
    async def find_by_user_id(self, user_id: str):
        
        self.__utility(self.find_by_user_id, (user_id,))

        if not user_id or not user_id.strip():
            return None

        return self.__get_data_store(user_id=user_id)
    
    async def increment_token_usage(self, user_id: str, tokens_used: int) -> int:
        self.__utility(self.increment_token_usage, (user_id, tokens_used,))
        
        if not user_id or not user_id.strip() or not tokens_used:
            return -1
        
        updated = 0
        
        data:UserResponseDTO = self.__get_data_store(user_id=user_id)
        
        if data:
            data.token_used += tokens_used
            updated+=1
        
        return updated
    
class StubUserStore(IUserStore):

    def __init__(self):
        self.stubbed_outputs = {}
        self.received_calls = []  # for optional spy behavior
        self.exceptions = {}  # method_name -> exception to raise

    async def __stubify(self, method, **kwargs):
        method_name = method.__name__
        self.received_calls.append((method_name, kwargs))
        if method_name in self.exceptions:
            raise self.exceptions[method_name]
        return self.stubbed_outputs[method_name]

    def set_output(self, method, output):
        method_name = method.__name__
        self.stubbed_outputs[method_name] = output

    def set_exception(self, method, exception: Exception):
        method_name = method.__name__
        self.exceptions[method_name] = exception
    
    async def save(self, user_model: UserRequestDTO) -> UserResponseDTO:
        return await self.__stubify(
            self.save, user_model=user_model
        )
    
    async def find_by_user_id(self, user_id):
        return await self.__stubify(
            self.find_by_user_id, user_id=user_id
        )
    
    async def increment_token_usage(self, user_id: str, tokens_used: int) -> int:
        return await self.__stubify(
            self.increment_token_usage, user_id=user_id, tokens_used=tokens_used
        )

def make_fake_user(user_id="user123", email="test@example.com", encryption_salt="xyz"):
    return UserResponseDTO(
        id=uuid.UUID("dd0551f4-2164-4739-bf3f-9ccd1644ca75"),
        user_id=user_id,
        email=email,
        encryption_salt=encryption_salt,
    )
