import uuid
from abc import abstractmethod
from dataclasses import asdict
from typing import Collection, Dict, List, Optional, Protocol, Union
from uuid import UUID

from tortoise.exceptions import IntegrityError

from models_src.dto.git_label import GitLabelRequestDTO, GitLabelResponseDTO
from models_src.dto.utils import TortoiseModelMapper
from models_src.exceptions.utils import GitLabelErrors, internal_error
from models_src.models import GitLabel


class ILabelStore(Protocol):

    @abstractmethod
    async def save(self, label_model: GitLabelRequestDTO) -> GitLabelResponseDTO: ...

    @abstractmethod
    async def find_git_hostings_by_ids(
        self, token_ids: Collection[Union[str, UUID]]
    ) -> List[Dict]: ...

    @abstractmethod
    async def find_by_token_id_and_user(
        self, token_id: str, user_id: str
    ) -> GitLabelResponseDTO | None: ...

    @abstractmethod
    async def find_by_id_and_user_id_and_git_hosting(
        self, id: str, user_id: str, git_hosting: str
    ) -> Optional[GitLabelResponseDTO]: ...

    @abstractmethod
    async def find_all_by_user_id(
        self, offset, limit, user_id, git_hosting: Optional[str] = None
    ) -> list[GitLabelResponseDTO]: ...

    @abstractmethod
    async def find_all_by_user_id_and_label(
        self, offset, limit, user_id, label: str
    ) -> list[GitLabelResponseDTO]: ...

    @abstractmethod
    async def count_by_user_id(
        self, user_id, git_hosting: Optional[str] = None
    ) -> int: ...

    @abstractmethod
    async def count_by_user_id_and_label(self, user_id, label: str) -> int: ...

    @abstractmethod
    async def delete_by_id_and_user_id(
        self, label_id: uuid.UUID, user_id: str
    ) -> int: ...


class TortoiseGitLabelStore(ILabelStore):

    def __init__(self):
        """
        Have to add this as an empty __init__ to override it, because when using it with Depends(),
        FastAPI dependency mechanism will automatically assume its
        ```
        def __init__(self, *args, **kwargs):
                pass
        ```
        Causing unneeded behavior.
        """
        pass

    model = GitLabel
    model_mapper = TortoiseModelMapper

    async def find_git_hostings_by_ids(
        self, token_ids: Collection[Union[str, UUID]]
    ) -> List[Dict]:
        if not token_ids:
            return []
        return await self.model.filter(id__in=token_ids).values("id", "git_hosting")

    async def find_by_token_id_and_user(
        self, token_id: str, user_id: str
    ) -> GitLabelResponseDTO | None:
        if not token_id or not token_id.strip() or not user_id or not user_id.strip():
            return None

        model = await self.model.filter(id=token_id, user_id=user_id).first()
        return self.model_mapper.map_model_to_dataclass(model, GitLabelResponseDTO)

    def __find_by_user_id_query(self, user_id, git_hosting: Optional[str] = None):
        if not user_id:
            raise internal_error(**GitLabelErrors.MISSING_USER_ID.value)

        query = self.model.filter(user_id=user_id)

        if git_hosting:
            query = query.filter(git_hosting=git_hosting)

        return query

    async def find_all_by_user_id(
        self, offset, limit, user_id, git_hosting: Optional[str] = None
    ) -> list[GitLabelResponseDTO]:
        query = self.__find_by_user_id_query(user_id, git_hosting)

        git_labels = (
            await query.order_by("-created_at")
            .offset(offset * limit)
            .limit(limit)
            .all()
        )

        return self.model_mapper.map_models_to_dataclasses_list(
            git_labels, GitLabelResponseDTO
        )

    async def count_by_user_id(self, user_id, git_hosting: Optional[str] = None) -> int:
        query = self.__find_by_user_id_query(user_id, git_hosting)

        return await query.count()

    def __find_by_user_id_and_label_query(self, user_id, label: str):
        if not user_id:
            raise internal_error(**GitLabelErrors.MISSING_USER_ID.value)

        if not label or not label.strip():
            raise internal_error(**GitLabelErrors.MISSING_LABEL.value)

        query = self.model.filter(user_id=user_id, label__icontains=label)

        return query

    async def count_by_user_id_and_label(self, user_id, label: str) -> int:

        query = self.__find_by_user_id_and_label_query(user_id, label)
        return await query.count()

    async def find_all_by_user_id_and_label(
        self, offset, limit, user_id, label: str
    ) -> list[GitLabelResponseDTO]:

        query = self.__find_by_user_id_and_label_query(user_id, label)

        git_labels = (
            await query.order_by("-created_at")
            .offset(offset * limit)
            .limit(limit)
            .all()
        )

        return self.model_mapper.map_models_to_dataclasses_list(
            git_labels, GitLabelResponseDTO
        )

    async def save(self, label_model: GitLabelRequestDTO) -> GitLabelResponseDTO:

        try:
            model = await self.model.create(**asdict(label_model))

            return self.model_mapper.map_model_to_dataclass(model, GitLabelResponseDTO)

        except IntegrityError as e:
            raise internal_error(**GitLabelErrors.GIT_LABEL_ALREADY_EXISTS.value) from e

    async def delete_by_id_and_user_id(self, label_id: uuid, user_id: str) -> int:
        """
        .delete returns 0 when No record is found or total number of records deleted.
        """
        if not label_id or not user_id or not user_id.strip():
            return -1

        number_of_effected_rows = await self.model.filter(
            id=label_id, user_id=user_id
        ).delete()

        return number_of_effected_rows

    async def find_by_id_and_user_id_and_git_hosting(
        self, id: str, user_id: str, git_hosting: str
    ) -> Optional[GitLabelResponseDTO]:
        raw_data = await GitLabel.filter(
            id=id, user_id=user_id, git_hosting=git_hosting
        ).first()

        return self.model_mapper.map_model_to_dataclass(raw_data, GitLabelResponseDTO)
