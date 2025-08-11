import datetime
from dataclasses import asdict
from typing import List, Tuple
from uuid import uuid4

from models_src.dto.code_chunks import CodeChunksRequestDTO, CodeChunksResponseDTO
from models_src.repositories.code_chunks import ICodeChunksStore


class FakeCodeChunksStore(ICodeChunksStore):
    
    def __init__(self):
        self.data_store: List[CodeChunksResponseDTO] = []
        self.total_count = 0
        self.received_calls = []
        self.exceptions = {}
    
    def __utility(self, method, received_calls:Tuple):
        
        method_name = method.__name__
        
        if method_name in self.exceptions:
            raise self.exceptions[method_name]
        
        self.received_calls.append((method_name, ) +  received_calls)
    
    def __get_data_store(self):
        return self.data_store
    
    def __set_data_store(self, data:List[CodeChunksResponseDTO]):
        self.data_store = data
        self.total_count = len(self.data_store)
    
    def set_fake_data(self, fake_data: list[CodeChunksResponseDTO]):
        self.data_store.extend(fake_data)
        self.total_count = len(self.data_store)
    
    def set_exception(self, method, exception: Exception):
        method_name = method.__name__
        self.exceptions[method_name] = exception
    
    async def save(self, create_model: CodeChunksRequestDTO) -> CodeChunksResponseDTO:
        
        self.__utility(self.save, (create_model,))
        
        response = CodeChunksResponseDTO(**asdict(create_model))
        response.id = uuid4()
        response.created_at = datetime.datetime.now(datetime.timezone.utc)
        
        self.data_store.append(response)
        self.total_count=len(self.data_store)
        
        return response
    
    async def find_all_by_repo_id_with_limit(self, repo_id: str, limit: int = 100) -> List[CodeChunksResponseDTO]:
        self.__utility(self.find_all_by_repo_id_with_limit, (repo_id,limit,))
        
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
    

class StubCodeChunksStore(ICodeChunksStore):
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
    
    async def save(self, create_model: CodeChunksRequestDTO) -> CodeChunksResponseDTO:
        return await self.__stubify(
            self.save, create_model=create_model
        )
    
    async def find_all_by_repo_id_with_limit(self, repo_id: str, limit: int = 100) -> List[CodeChunksResponseDTO]:
        return await self.__stubify(
	        self.find_all_by_repo_id_with_limit, repo_id=repo_id, limit=limit
        )