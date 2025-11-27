import pytest
from pydantic import ValidationError

from models_src.exceptions.exception_constants import EMBEDDINGS_INVALID_SIZE
from models_src.models.beanie_odm.code_chunks_document import CodeChunks, EMBED_DIM


def test_code_chunks_embedding_validation():
	
	incorrect_dem_size = EMBED_DIM - 10
	
	with pytest.raises(ValidationError) as p:
		CodeChunks(
		    user_id="user_id",
			repo_id="repo_id",
			content="content",
			file_name="file_name",
			file_path="file_path",
			file_size=100,
			commit_number="commit_number",
			embedding=[0.0] * incorrect_dem_size
		)
	
	assert EMBEDDINGS_INVALID_SIZE.format(EMBED_DIM=EMBED_DIM, ARRAY_LENGTH=incorrect_dem_size) in str(p)

def test_document_str():
	rp = CodeChunks.model_construct(
		    user_id="user_id",
			repo_id="repo_id",
			content="content",
			file_name="file_name",
			file_path="file_path",
			file_size=100,
			commit_number="commit_number",
			embedding=[0.0] * EMBED_DIM
		)
	
	assert str(rp) == f"CodeChunks(id={rp.id}, user_id={rp.user_id}, repo_id={rp.repo_id})"

def test_document_repr():
	rp = CodeChunks.model_construct(
		user_id="user_id",
		repo_id="repo_id",
		content="content",
		file_name="file_name",
		file_path="file_path",
		file_size=100,
		commit_number="commit_number",
		embedding=[0.0] * EMBED_DIM
	)
	
	assert str(rp) == f"CodeChunks(id={rp.id}, user_id={rp.user_id}, repo_id={rp.repo_id})"
	assert str(rp) == repr(rp)