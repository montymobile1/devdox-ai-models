import datetime
import uuid
from dataclasses import asdict
from typing import Any

from models_src.dto.user import UserRequestDTO, UserResponseDTO
from models_src.repositories.user import IUserStore
from models_src.test_doubles.repositories.bases import FakeBase, StubPlanMixin


class FakeUserStore(FakeBase, IUserStore):

    def __init__(self):
        super().__init__()
        self.data_store: dict[Any, UserResponseDTO] = {}
        self.total_count = 0

    def __get_data_store(self, user_id=None):

        if user_id:
            return self.data_store.get(user_id)

        return self.data_store

    def __set_data_store(self, data: UserResponseDTO):
        self.data_store.setdefault(data.user_id, data)

    def set_fake_data(self, fake_data: list[UserResponseDTO]):

        for data in fake_data:
            self.__set_data_store(data=data)

        self.total_count = len(self.data_store)

    async def save(self, user_model: UserRequestDTO) -> UserResponseDTO:
        self._before(self.save, user_model=user_model)

        result = UserResponseDTO(**asdict(user_model))
        result.id = uuid.uuid4()
        result.created_at = datetime.datetime.now(datetime.timezone.utc)

        self.__set_data_store(data=result)
        self.total_count += 1

        return result

    async def find_by_user_id(self, user_id: str):

        self._before(self.find_by_user_id, user_id=user_id)

        if not user_id or not user_id.strip():
            return None

        return self.__get_data_store(user_id=user_id)

    async def increment_token_usage(self, user_id: str, tokens_used: int) -> int:
        self._before(
            self.increment_token_usage, user_id=user_id, tokens_used=tokens_used
        )

        if not user_id or not user_id.strip() or not tokens_used:
            return -1

        updated = 0

        data: UserResponseDTO = self.__get_data_store(user_id=user_id)

        if data:
            data.token_used += tokens_used
            updated += 1

        return updated


class StubUserStore(StubPlanMixin, IUserStore):

    def __init__(self):
        super().__init__()

    async def save(self, user_model: UserRequestDTO) -> UserResponseDTO:
        return await self._stub(self.save, user_model=user_model)

    async def find_by_user_id(self, user_id):
        return await self._stub(self.find_by_user_id, user_id=user_id)

    async def increment_token_usage(self, user_id: str, tokens_used: int) -> int:
        return await self._stub(
            self.increment_token_usage, user_id=user_id, tokens_used=tokens_used
        )


def make_fake_user(user_id="user123", email="test@example.com", encryption_salt="xyz"):
    return UserResponseDTO(
        id=uuid.UUID("dd0551f4-2164-4739-bf3f-9ccd1644ca75"),
        user_id=user_id,
        email=email,
        encryption_salt=encryption_salt,
    )
