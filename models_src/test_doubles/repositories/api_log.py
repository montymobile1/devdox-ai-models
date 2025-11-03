import datetime
import uuid
from dataclasses import asdict
from typing import Any

from models_src.dto.api_log import ApiLogRequestDTO, ApiLogResponseDTO
from models_src.repositories.api_log import IApiLogStore
from models_src.test_doubles.repositories.bases import FakeBase, StubPlanMixin


class FakeApiLogStore(FakeBase, IApiLogStore):
	
	def __init__(self):
		super().__init__()
		self.data_store: dict[Any, ApiLogResponseDTO] = {}
		self.total_count = 0
	
	def __get_data_store(self, user_id=None):
		
		if user_id:
			return self.data_store.get(user_id)
		
		return self.data_store
	
	def __set_data_store(self, data: ApiLogResponseDTO):
		self.data_store.setdefault(data.user_id, data)
	
	def set_fake_data(self, fake_data: list[ApiLogResponseDTO]):
		
		for data in fake_data:
			self.__set_data_store(data=data)
		
		self.total_count = len(self.data_store)
	
	async def save(self, user_model: ApiLogRequestDTO) -> ApiLogResponseDTO:
		self._before(self.save, user_model=user_model)
		
		result = ApiLogResponseDTO(**asdict(user_model))
		result.id = uuid.uuid4()
		result.created_at = datetime.datetime.now(datetime.timezone.utc)
		
		self.__set_data_store(data=result)
		self.total_count += 1
		
		return result


class StubUserStore(StubPlanMixin, IApiLogStore):
	
	def __init__(self):
		super().__init__()
	
	async def save(self, user_model: ApiLogRequestDTO) -> ApiLogResponseDTO:
		return await self._stub(self.save, user_model=user_model)
