import uuid
from dataclasses import asdict
from typing import Any, List, Tuple

from models_src.dto.repo import RepoRequestDTO, RepoResponseDTO
from models_src.repositories.repo import IRepoStore


class FakeRepoStore(IRepoStore):

    def __init__(self):
        self.data_store: dict[Any, List[RepoResponseDTO]] = {}
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
            return self.data_store.get(user_id, [])

        return self.data_store
    
    def __set_data_store(self, data:RepoResponseDTO):
        self.data_store.setdefault(data.user_id, []).append(data)
    
    def set_fake_data(self, fake_data: List[RepoResponseDTO]):
        for data in fake_data:
            self.__set_data_store(data=data)

        full_total = 0
        for values in self.data_store.values():
            full_total = full_total + len(values)

        self.total_count = full_total

    def set_exception(self, method_name: str, exception: Exception):
        self.exceptions[method_name] = exception

    async def get_all_by_user(self, user_id: str, offset: int, limit: int) -> List[RepoResponseDTO]:
        self.__utility(self.get_all_by_user, (user_id, offset, limit))

        data= self.__get_data_store(user_id=user_id)

        return data[offset : offset + limit]

    async def count_by_user(self, user_id: str) -> int:
        self.__utility(self.count_by_user, (user_id, ))

        data = self.__get_data_store(user_id=user_id)

        return len(data)

    async def create_new_repo(self, repo_model: RepoRequestDTO) -> RepoResponseDTO:
        self.__utility(self.create_new_repo, (repo_model,))

        response = RepoResponseDTO(**asdict(repo_model))
        response.id = uuid.uuid4()

        self.__set_data_store(data=response)

        self.total_count += 1

        return response

    async def get_by_id(self, repo_id: str) -> RepoResponseDTO:

        self.__utility(self.get_by_id, (repo_id,))

        match = None
        for key, obj_list in self.__get_data_store().items():
            match = next((obj for obj in obj_list if obj.repo_id == repo_id), None)
            if match:
                break

        return match
