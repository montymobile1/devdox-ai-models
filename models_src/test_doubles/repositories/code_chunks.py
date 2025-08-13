import datetime
from dataclasses import asdict
from typing import List
from uuid import uuid4

from models_src.dto.code_chunks import CodeChunksRequestDTO, CodeChunksResponseDTO
from models_src.repositories.code_chunks import ICodeChunksStore
from models_src.test_doubles.repositories.bases import FakeBase, StubPlanMixin


class FakeCodeChunksStore(FakeBase, ICodeChunksStore):
    
    def __init__(self):
        super().__init__()
        self.data_store: List[CodeChunksResponseDTO] = []
        self.total_count = 0
    
    def __get_data_store(self):
        return self.data_store
    
    def __set_data_store(self, data:List[CodeChunksResponseDTO]):
        self.data_store = data
        self.total_count = len(self.data_store)
    
    def set_fake_data(self, fake_data: list[CodeChunksResponseDTO]):
        self.data_store.extend(fake_data)
        self.total_count = len(self.data_store)

    async def save(self, create_model: CodeChunksRequestDTO) -> CodeChunksResponseDTO:
        
        self._before(self.save, create_model=create_model)
        
        response = CodeChunksResponseDTO(**asdict(create_model))
        response.id = uuid4()
        response.created_at = datetime.datetime.now(datetime.timezone.utc)
        
        self.data_store.append(response)
        self.total_count=len(self.data_store)
        
        return response
    
    async def find_all_by_repo_id_with_limit(self, repo_id: str, limit: int = 100) -> List[CodeChunksResponseDTO]:
        self._before(self.find_all_by_repo_id_with_limit, repo_id=repo_id,limit=limit)
        
        data = self.__get_data_store()
        
        final_result = []
        index_limit_counter = 1
        for index, result in enumerate(data):
            if index_limit_counter > limit:
                break
            
            if result.repo_id == repo_id:
                final_result.append(result)
                index_limit_counter += 1
        
        return final_result
    

class StubCodeChunksStore(StubPlanMixin, ICodeChunksStore):
    def __init__(self):
        super().__init__()
    
    async def save(self, create_model: CodeChunksRequestDTO) -> CodeChunksResponseDTO:
        return await self._stub(
            self.save, create_model=create_model
        )
    
    async def find_all_by_repo_id_with_limit(self, repo_id: str, limit: int = 100) -> List[CodeChunksResponseDTO]:
        return await self._stub(
	        self.find_all_by_repo_id_with_limit, repo_id=repo_id, limit=limit
        )