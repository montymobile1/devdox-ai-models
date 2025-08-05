from abc import abstractmethod
from dataclasses import asdict
from typing import List, Protocol

from tortoise.exceptions import DoesNotExist

from models_src.dto.repo import RepoResponseDTO
from models_src.dto.utils import TortoiseModelMapper
from models_src.exceptions.utils import internal_error, RepoErrors
from models_src.models import Repo


class IRepoStore(Protocol):
    pass

class TortoiseRepoStore(IRepoStore):

    model = Repo
    model_mapper = TortoiseModelMapper

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

    pass