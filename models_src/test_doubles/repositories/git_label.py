import datetime
import uuid
from typing import Any, List, Tuple
from models_src.dto.git_label import GitLabelResponseDTO
from models_src.repositories.git_label import ILabelStore

class FakeGitLabelStore(ILabelStore):
    def __init__(self):
        self.data_store: dict[Any, List[GitLabelResponseDTO]] = {}
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
            return self.data_store.get(user_id, [])

        return self.data_store
    
    def __set_data_store(self, data:GitLabelResponseDTO):
        self.data_store.setdefault(data.user_id, []).append(data)
    
    def set_fake_data(self, fake_data: List[GitLabelResponseDTO]):
        for data in fake_data:
            self.__set_data_store(data)

        full_total = 0
        for values in self.data_store.values():
            full_total = full_total + len(values)

        self.total_count = full_total

    def set_exception(self, method_name: str, exception: Exception):
        self.exceptions[method_name] = exception

def make_fake_git_label(**overrides) -> GitLabelResponseDTO:
    now = datetime.datetime.now()
    return GitLabelResponseDTO(
        id=overrides.get("id", uuid.uuid4()),
        user_id=overrides.get("user_id", "fake-user"),
        label=overrides.get("label", "fake-label"),
        git_hosting=overrides.get("git_hosting", "github"),
        username=overrides.get("username", "fakeuser"),
        token_value=overrides.get("token_value", "real-token"),
        masked_token=overrides.get("masked_token", "****1234"),
        created_at=overrides.get("created_at", now),
        updated_at=overrides.get("updated_at", now),
    )
