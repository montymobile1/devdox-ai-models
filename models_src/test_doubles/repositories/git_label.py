import datetime
import uuid
from dataclasses import asdict
from typing import Any, Collection, Dict, List, Optional, Tuple, Union
from uuid import UUID

from models_src.dto.git_label import GitLabelRequestDTO, GitLabelResponseDTO
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

    def set_exception(self, method, exception: Exception):
        method_name = method.__name__
        self.exceptions[method_name] = exception

    async def get_all_git_hosting_only_by_token_id_list(self, token_ids: Collection[Union[str, UUID]]) -> List[Dict]:

        if not token_ids:
            return []

        self.__utility(self.get_all_git_hosting_only_by_token_id_list, (token_ids,))

        match_list = []
        for key, obj_list in self.data_store.items():
            match = next((obj for obj in obj_list if obj.id in token_ids), None)
            if match:
                match_list.append(
                    {
                        "id": match.id,
                        "git_hosting": match.git_hosting
                    }
                )

        return match_list

    async def get_by_token_id_and_user(self, token_id: str, user_id: str) -> GitLabelResponseDTO | None:
        self.__utility(self.get_by_token_id_and_user, (token_id, user_id))

        user_id_data = self.__get_data_store(user_id=user_id)

        result = None
        for record in user_id_data:
            if record.id == token_id:
                result= record
                break

        return result

    async def get_all_by_user_id(self, offset, limit, user_id, git_hosting: Optional[str] = None) -> list[GitLabelResponseDTO]:
        self.__utility(self.get_all_by_user_id, (offset, limit, user_id, git_hosting))
        data = self.__get_data_store(user_id=user_id)
        return data[offset : offset + limit]

    async def count_by_user_id(self, user_id, git_hosting: Optional[str] = None) -> int:
        self.__utility(self.count_by_user_id, (user_id, git_hosting))

        data = self.__get_data_store(user_id=user_id)

        count = len(data) if data else 0

        if git_hosting:
            count = 0
            for record in data:
                if record.git_hosting == git_hosting:
                    count += 1

        return count

    async def get_all_by_user_id_and_label(self, offset, limit, user_id, label: str) -> list[GitLabelResponseDTO]:
        self.__utility(self.get_all_by_user_id_and_label, (offset, limit, user_id, label))

        data = self.__get_data_store(user_id=user_id)

        results = []
        for record in data:
            if record.label == label:
                results.append(record)

        return results[offset : offset + limit]

    async def count_by_user_id_and_label(self, user_id, label: str) -> int:
        self.__utility(self.count_by_user_id_and_label, (user_id, label))

        user_id_data = self.__get_data_store(user_id=user_id)

        if label:
            count = 0
            for record in user_id_data:
                if record.label == label:
                    count += 1

            return count
        else:
            return len(user_id_data) if user_id_data else 0

    async def save(self, label_model: GitLabelRequestDTO) -> GitLabelResponseDTO:

        self.__utility(self.save, (label_model,))

        result = GitLabelResponseDTO(**asdict(label_model))
        result.id = uuid.uuid4()

        self.__set_data_store(data=result)
        self.total_count += 1

        return result

    async def delete_by_id_and_user_id(self, label_id: uuid.UUID, user_id: str) -> int:
        if not label_id or not user_id or not user_id.strip():
            return -1

        self.__utility(self.delete_by_id_and_user_id, (label_id, user_id,))

        data = self.__get_data_store(user_id=user_id)
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
    
    async def find_by_id_and_user_id_and_git_hosting(self, id: str, user_id: str, git_hosting: str) -> Optional[
        GitLabelResponseDTO]:
        
        self.__utility(self.find_by_id_and_user_id_and_git_hosting, (id, user_id, git_hosting, ))
        
        data = self.__get_data_store(user_id=user_id)
        
        match = None
        
        for record in data:
            if record.id == id and record.git_hosting == git_hosting:
                match = record
                break

        return match

class StubGitLabelStore(ILabelStore):

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

    async def save(self, label_model: GitLabelRequestDTO) -> GitLabelResponseDTO:
        pass

    async def get_all_git_hosting_only_by_token_id_list(self, token_ids: Collection[Union[str, UUID]]) -> List[Dict]:
        pass

    async def get_all_by_user_id(self, offset, limit, user_id, git_hosting: Optional[str] = None) -> list[
        GitLabelResponseDTO]:
        pass

    async def get_all_by_user_id_and_label(self, offset, limit, user_id, label: str) -> list[GitLabelResponseDTO]:
        pass

    async def count_by_user_id(self, user_id, git_hosting: Optional[str] = None) -> int:
        pass

    async def count_by_user_id_and_label(self, user_id, label: str) -> int:
        pass

    async def delete_by_id_and_user_id(self, label_id: uuid.UUID, user_id: str) -> int:
        pass

    async def get_by_token_id_and_user(self, token_id, user_id):
        return await self.__stubify(
            self.get_by_token_id_and_user, token_id=token_id, user_id=user_id
        )
    
    async def find_by_id_and_user_id_and_git_hosting(self, id: str, user_id: str, git_hosting: str) -> Optional[
        GitLabelResponseDTO]:
        return await self.__stubify(
            self.find_by_id_and_user_id_and_git_hosting, id=id, user_id=user_id, git_hosting=git_hosting
        )

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
