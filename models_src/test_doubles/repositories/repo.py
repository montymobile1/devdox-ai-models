import uuid
from dataclasses import asdict
from typing import Any, List, Optional, Tuple

from models_src.dto.repo import RepoRequestDTO, RepoResponseDTO
from models_src.repositories.repo import IRepoStore
from models_src.test_doubles.repositories.bases import FakeBase


class FakeRepoStore(FakeBase, IRepoStore):

    def __init__(self):
        super().__init__()
        self.__data_store: dict[Any, List[RepoResponseDTO]] = {}
        self.total_count = 0

    @property
    def data_store(self):
        return self.__data_store

    def __get_data_store(self, user_id=None):
        if user_id:
            return self.__data_store.get(user_id, [])

        return self.__data_store

    def __set_data_store(self, data: RepoResponseDTO):
        self.__data_store.setdefault(data.user_id, []).append(data)

    def set_fake_data(self, fake_data: List[RepoResponseDTO]):
        for data in fake_data:
            self.__set_data_store(data=data)

        full_total = 0
        for values in self.__data_store.values():
            full_total = full_total + len(values)

        self.total_count = full_total

    async def find_all_by_user_id(
        self, user_id: str, offset: int, limit: int
    ) -> List[RepoResponseDTO]:
        self._before(
            self.find_all_by_user_id, user_id=user_id, offset=offset, limit=limit
        )

        data = self.__get_data_store(user_id=user_id)

        return data[offset : offset + limit]

    async def count_by_user_id(self, user_id: str) -> int:
        self._before(self.count_by_user_id, user_id=user_id)

        data = self.__get_data_store(user_id=user_id)

        return len(data)

    async def save(self, repo_model: RepoRequestDTO) -> RepoResponseDTO:
        self._before(self.save, repo_model=repo_model)

        response = RepoResponseDTO(**asdict(repo_model))
        response.id = uuid.uuid4()

        self.__set_data_store(data=response)

        self.total_count += 1

        return response

    async def get_by_id(self, repo_id: str) -> RepoResponseDTO:

        self._before(self.get_by_id, repo_id=repo_id)

        match = None
        for key, obj_list in self.__get_data_store().items():
            match = next(
                (obj for obj in obj_list if obj.id == uuid.UUID(repo_id)), None
            )
            if match:
                break

        return match

    async def find_by_repo_id(self, repo_id: str) -> Optional[RepoResponseDTO]:
        self._before(self.find_by_repo_id, repo_id=repo_id)

        match = None
        for key, obj_list in self.__get_data_store().items():
            match = next((obj for obj in obj_list if obj.repo_id == repo_id), None)
            if match:
                break

        return match

    async def find_by_id(self, id: str) -> Optional[RepoResponseDTO]:
        self._before(self.find_by_id, id=id)

        match = None
        for key, obj_list in self.__get_data_store().items():
            match = next((obj for obj in obj_list if obj.id == id), None)
            if match:
                break

        return match

    async def update_status_by_repo_id(
        self, repo_id: str, status: str, **kwargs: Any
    ) -> int:
        self._before(
            self.update_status_by_repo_id, repo_id=repo_id, status=status, kwargs=kwargs
        )

        data = self.__get_data_store()

        if (not repo_id or not repo_id.strip()) or (not status or not status.strip()):
            return -1

        updated = 0
        for key, obj_list in data.items():
            match = next((obj for obj in obj_list if obj.repo_id == repo_id), None)
            if match:
                match.status = status
                updated += 1
                break

        return updated

    async def find_by_user_id_and_html_url(
        self, user_id: str, html_url: str
    ) -> Optional[RepoResponseDTO]:
        self._before(
            self.find_by_user_id_and_html_url, user_id=user_id, html_url=html_url
        )
        match = None

        data: List[RepoResponseDTO] = self.__get_data_store(user_id=user_id)

        for obj in data:
            if obj.html_url == html_url:
                match = obj
                return match

        return match

    async def save_context(
        self, repo_id: str, user_id: str, config: dict
    ) -> RepoResponseDTO:
        """
        config: Ignore since it is only applicable to Tortoise ORM
        """

        self._before(self.save_context, repo_id=repo_id, user_id=user_id, config=config)

        response = RepoResponseDTO(repo_id=repo_id, user_id=user_id, status="pending")
        response.id = uuid.uuid4()

        self.__set_data_store(data=response)

        self.total_count += 1

        return response

    async def update_repo_system_reference_by_id(
        self, id: str, repo_system_reference: str
    ) -> int:
        self._before(
            self.update_repo_system_reference_by_id,
            id=id,
            repo_system_reference=repo_system_reference,
        )

        if (
            not id
            or not id.strip()
            or not repo_system_reference
            or not repo_system_reference.strip()
        ):
            return -1

        data = self.__get_data_store()

        updated = 0
        for key, obj_list in data.items():
            match = next((obj for obj in obj_list if obj.id == id), None)
            if match:
                match.repo_system_reference = repo_system_reference
                updated += 1
                break

        return updated
