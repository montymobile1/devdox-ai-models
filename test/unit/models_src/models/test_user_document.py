from models_src.models.user_document import User


def test_document_str():
	rp = User.model_construct(
		first_name="first_name",
		last_name="last_name",
		email="email",
	)
	
	assert str(rp) == f"{rp.first_name} {rp.last_name} ({rp.email})"

def test_document_repr():
	rp = User.model_construct(
		first_name="first_name",
		last_name="last_name",
		email="email",
	)
	
	assert str(rp) == f"{rp.first_name} {rp.last_name} ({rp.email})"
	assert str(rp) == repr(rp)