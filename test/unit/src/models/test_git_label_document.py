from models_src.models.git_label_document import GitLabel


def test_document_str():
	rp = GitLabel.model_construct(
		id="id",
		user_id="user_id",
		label="label",
		git_hosting="git_hosting",
	)
	
	assert str(rp) == f"GitLabel(id={rp.id}, user_id={rp.user_id}, label={rp.label}, git_hosting={rp.git_hosting})"

def test_document_repr():
	rp = GitLabel.model_construct(
		id="id",
		user_id="user_id",
		label="label",
		git_hosting="git_hosting",
	)
	
	assert str(rp) == f"GitLabel(id={rp.id}, user_id={rp.user_id}, label={rp.label}, git_hosting={rp.git_hosting})"
	assert str(rp) == repr(rp)