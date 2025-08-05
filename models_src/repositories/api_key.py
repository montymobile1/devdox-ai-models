from typing import Protocol

from models_src.dto.utils import TortoiseModelMapper
from models_src.models import APIKEY


class IApiKeyStore(Protocol):
    pass

class TortoiseApiKeyStore(IApiKeyStore):
    
    model=APIKEY
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