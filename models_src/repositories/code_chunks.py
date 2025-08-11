import datetime
import uuid
from abc import abstractmethod
from dataclasses import asdict
from typing import List, Optional, Protocol

from models_src.dto.code_chunks import CodeChunksRequestDTO, CodeChunksResponseDTO
from models_src.dto.utils import TortoiseModelMapper
from models_src.models import CodeChunks


class ICodeChunksStore(Protocol):
	
	@abstractmethod
	async def save(self, create_model: CodeChunksRequestDTO) -> CodeChunksResponseDTO: ...
	
	@abstractmethod
	async def find_all_by_repo_id_with_limit(self, repo_id: str, limit: int = 100) -> List[CodeChunksResponseDTO]: ...

class TortoiseICodeChunksStore(ICodeChunksStore):
	
	model=CodeChunks
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
	
	async def save(self, create_model: CodeChunksRequestDTO) -> CodeChunksResponseDTO:
		data = await self.model.create(**asdict(create_model))
		return self.model_mapper.map_model_to_dataclass(data, CodeChunksResponseDTO)
	
	async def find_all_by_repo_id_with_limit(self, repo_id: str, limit: int = 100) -> List[CodeChunksResponseDTO]:
		raw_data = await self.model.filter(repo_id=repo_id).limit(limit).all()
		return self.model_mapper.map_models_to_dataclasses_list(raw_data, CodeChunksResponseDTO)