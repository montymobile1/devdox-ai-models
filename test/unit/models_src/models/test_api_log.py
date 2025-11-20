import datetime

from models_src.models.api_log_document import ApiLog


def test_document_str():
	rp = ApiLog.model_construct(
		id="id",
		user_id= "user-1",
		operation_id= "api_operation_id",
		path= "/some/api",
		method= "POST",
		request_received_at= datetime.datetime.now(datetime.timezone.utc),
		process_time_ms= 1,
		request_body= {"x": "x", "y": "y"},
		response_body= {"x": "x", "y": "y"},
	)
	
	assert str(rp) == f"ApiLog(id={rp.id}, user_id={rp.user_id}, method={rp.method}, path={rp.path})"


def test_document_repr():
	rp = ApiLog.model_construct(
		id="id",
		user_id= "user-1",
		operation_id= "api_operation_id",
		path= "/some/api",
		method= "POST",
		request_received_at= datetime.datetime.now(datetime.timezone.utc),
		process_time_ms= 1,
		request_body= {"x": "x", "y": "y"},
		response_body= {"x": "x", "y": "y"},
	)
	
	assert str(rp) == f"ApiLog(id={rp.id}, user_id={rp.user_id}, method={rp.method}, path={rp.path})"
	assert str(rp) == repr(rp)