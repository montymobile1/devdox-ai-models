import datetime
from abc import abstractmethod
from dataclasses import asdict
from typing import Optional, Protocol

from models_src.dto.queue_job_claim_registry import QueueProcessingRegistryRequestDTO, \
	QueueProcessingRegistryResponseDTO
from models_src.dto.utils import TortoiseModelMapper
from models_src.models import QRegistryStat, QueueProcessingRegistry


class IQueueProcessingRegistryStore(Protocol):
	
	@abstractmethod
	async def save(self, create_model: QueueProcessingRegistryRequestDTO) -> QueueProcessingRegistryResponseDTO: ...
	
	@abstractmethod
	async def update_status_or_message_id_by_id(self, id: str, status: QRegistryStat, message_id: Optional[str] = None) -> int: ...
	
	@abstractmethod
	async def update_step_by_id(self, id: str, step: str) -> int: ...
	
	@abstractmethod
	async def update_status_and_step_by_id(self, id: str, status: QRegistryStat, step: str) -> int: ...


class TortoiseQueueProcessingRegistryStore(IQueueProcessingRegistryStore):
	
	model = QueueProcessingRegistry
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
	
	async def __internal_update_by_id(self, id:str, **kwargs):
		return await self.model.filter(id=id).update(
			updated_at=datetime.datetime.now(datetime.timezone.utc),
			**kwargs
		)
	
	async def save(self, create_model:QueueProcessingRegistryRequestDTO) -> QueueProcessingRegistryResponseDTO:
		raw_data = await self.model.create(
			**asdict(create_model)
		)
		return self.model_mapper.map_model_to_dataclass(raw_data, QueueProcessingRegistryResponseDTO)
	
	async def update_status_or_message_id_by_id(self, id: str, status:QRegistryStat, message_id:Optional[str]=None) -> int:
		if (not id or not id.strip()) or not status:
			return -1
		
		values_to_update_dict:dict = {
			"status": status
		}
		
		if message_id:
			values_to_update_dict["message_id"] = message_id
		
		return await self.__internal_update_by_id(id, **values_to_update_dict)
	
	async def update_step_by_id(self, id: str, step: str) -> int:
		if (not id or not id.strip()) or not (not step or not step.strip()):
			return -1
		
		return await self.__internal_update_by_id(id, step=step)
	
	async def update_status_and_step_by_id(self, id: str, status: QRegistryStat, step: str) -> int:
		if (not id or not id.strip()) or not status or not (not step or not step.strip()):
			return -1
		
		return await self.__internal_update_by_id(id, status=status, step=step)