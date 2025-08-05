from typing import Any, List, Tuple

from models_src.dto.repo import RepoResponseDTO
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