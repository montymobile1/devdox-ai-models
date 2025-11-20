import uuid

import pytest

from models_src import ApiLogResponseDTO, InMemoryApiLogBackend
from test.conftest import _make_api_log_request


@pytest.mark.asyncio
class TestInMemoryApiLogBackend:
	
	inmemory_store = InMemoryApiLogBackend
	
	async def test_save(self):
		
		store = self.inmemory_store()
		
		# Arrange
		req_full_with_dict_req_res = _make_api_log_request(
			request_body= {
				"name": "Jane Doe",
				"email": "jane.doe@example.com",
				"isActive": True
			},
			response_body={
				"id": 1,
				"name": "Jane Doe",
				"email": "jane.doe@example.com",
				"isActive": True
			}
		)
		
		req_full_with_list_req_res = _make_api_log_request(
			request_body= ["x", "y", "z"],
			response_body= ["a", "b", "c"],
		)
		
		req_full_with_only_required = _make_api_log_request()
		
		
		# Act
		saved_full_with_dict_req_res = await store.save(req_full_with_dict_req_res)
		saved_full_with_list_req_res = await store.save(req_full_with_list_req_res)
		saved_full_with_only_required = await store.save(req_full_with_only_required)
		
		# ASSERT
		assert isinstance(saved_full_with_dict_req_res, ApiLogResponseDTO)
		assert isinstance(saved_full_with_list_req_res, ApiLogResponseDTO)
		assert isinstance(saved_full_with_only_required, ApiLogResponseDTO)
		
		assert saved_full_with_dict_req_res.id is not None
		assert saved_full_with_list_req_res.id is not None
		assert saved_full_with_only_required.id is not None
		
		assert isinstance(saved_full_with_dict_req_res.id, uuid.UUID)
		assert isinstance(saved_full_with_list_req_res.id, uuid.UUID)
		assert isinstance(saved_full_with_only_required.id, uuid.UUID)
		
		assert saved_full_with_dict_req_res.operation_id == req_full_with_dict_req_res.operation_id
		assert saved_full_with_list_req_res.operation_id == req_full_with_list_req_res.operation_id
		assert saved_full_with_only_required.operation_id == req_full_with_only_required.operation_id
		
		assert saved_full_with_dict_req_res.path == req_full_with_dict_req_res.path
		assert saved_full_with_list_req_res.path == req_full_with_list_req_res.path
		assert saved_full_with_only_required.path == req_full_with_only_required.path
		
		assert saved_full_with_dict_req_res.method == req_full_with_dict_req_res.method
		assert saved_full_with_list_req_res.method == req_full_with_list_req_res.method
		assert saved_full_with_only_required.method == req_full_with_only_required.method
		
		assert saved_full_with_dict_req_res.user_id == req_full_with_dict_req_res.user_id
		assert saved_full_with_list_req_res.user_id == req_full_with_list_req_res.user_id
		assert saved_full_with_only_required.user_id == req_full_with_only_required.user_id
		
		assert saved_full_with_dict_req_res.request_received_at.date() == req_full_with_dict_req_res.request_received_at.date()
		assert saved_full_with_list_req_res.request_received_at.date() == req_full_with_list_req_res.request_received_at.date()
		assert saved_full_with_only_required.request_received_at.date() == req_full_with_only_required.request_received_at.date()
		
		assert saved_full_with_dict_req_res.process_time_ms == req_full_with_dict_req_res.process_time_ms
		assert saved_full_with_list_req_res.process_time_ms == req_full_with_list_req_res.process_time_ms
		assert saved_full_with_only_required.process_time_ms == req_full_with_only_required.process_time_ms
		
		assert saved_full_with_dict_req_res.request_body == req_full_with_dict_req_res.request_body
		assert isinstance(saved_full_with_dict_req_res.request_body, dict)
		assert saved_full_with_list_req_res.request_body == req_full_with_list_req_res.request_body
		assert isinstance(saved_full_with_list_req_res.request_body, list)
		assert saved_full_with_only_required.request_body == req_full_with_only_required.request_body
		
		assert saved_full_with_dict_req_res.response_body == req_full_with_dict_req_res.response_body
		assert isinstance(saved_full_with_dict_req_res.response_body, dict)
		assert saved_full_with_list_req_res.response_body == req_full_with_list_req_res.response_body
		assert isinstance(saved_full_with_list_req_res.response_body, list)
		assert saved_full_with_only_required.response_body == req_full_with_only_required.response_body
		
		assert saved_full_with_dict_req_res.created_at
		assert saved_full_with_dict_req_res.updated_at
		
		assert saved_full_with_list_req_res.created_at
		assert saved_full_with_list_req_res.updated_at
		
		assert saved_full_with_only_required.created_at
		assert saved_full_with_only_required.updated_at
		
		assert len(store.get_data_store(user_id=req_full_with_dict_req_res.user_id)) == 3
		assert store.total_count == 3
		