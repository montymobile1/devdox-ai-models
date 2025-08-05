from typing import Collection, Dict, List, Optional, Protocol, Union
from uuid import UUID

from models_src.dto.git_label import GitLabelResponseDTO
from models_src.dto.utils import TortoiseModelMapper
from models_src.exceptions.utils import GitLabelErrors, internal_error
from models_src.models import GitLabel

class ILabelStore(Protocol):
    pass


class TortoiseGitLabelStore(ILabelStore):
    
    model = GitLabel
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