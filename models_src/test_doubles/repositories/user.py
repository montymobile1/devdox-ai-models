import uuid
from typing import Any, Tuple

from models_src.dto.user import UserResponseDTO
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

    async def find_by_user_id(self, user_id: str):

        self.__utility(self.find_by_user_id, (user_id,))

        return self.__get_data_store(user_id=user_id)

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

    async def find_by_user_id(self, user_id):
        return await self.__stubify(
            self.find_by_user_id, user_id=user_id
        )

def make_fake_user(user_id="user123", email="test@example.com", encryption_salt="xyz"):
    return UserResponseDTO(
        id=uuid.UUID("dd0551f4-2164-4739-bf3f-9ccd1644ca75"),
        user_id=user_id,
        email=email,
        encryption_salt=encryption_salt,
    )
