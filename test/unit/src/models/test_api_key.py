from models_src.models.api_key_document import APIKEY


def test_document_str():
	rp = APIKEY.model_construct(
		id="id",
		user_id="user_id",
		masked_api_key="masked_api_key",
	)
	
	assert str(rp) == f"APIKEY(id={rp.id}, user_id={rp.user_id}, masked_api_key={rp.masked_api_key})"


def test_document_repr():
	rp = APIKEY.model_construct(
		id="id",
		user_id="user_id",
		masked_api_key="masked_api_key",
	)
	
	assert str(rp) == f"APIKEY(id={rp.id}, user_id={rp.user_id}, masked_api_key={rp.masked_api_key})"
	assert str(rp) == repr(rp)