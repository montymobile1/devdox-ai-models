from models_src.models.beanie_odm.repo_document import Repo


def test_document_str():
	rp = Repo.model_construct(
		user_id="user_id",
		repo_id="repo_id",
		repo_name="repo_name",
		description="description",
		html_url="html_url",
		visibility="public",
		token_id="token_id",
		repo_created_at=None,
		repo_updated_at=None,
		language=["BYTHON"],
		relative_path="relative_path",
		error_message=None,
		repo_alias_name="repo_alias_name",
		repo_user_reference="repo_user_reference",
		repo_system_reference=None,
		repo_author_name="repo_author_name",
		repo_author_email="repo_author_email"
	)
	
	assert str(rp) == rp.repo_name
