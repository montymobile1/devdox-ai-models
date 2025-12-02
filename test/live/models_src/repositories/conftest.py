import pytest_asyncio
from tortoise import Tortoise

from models_src.db_inits.beanie_init import documents_list_loc, init_via_uri
from models_src.db_inits.tortoise_init import get_tortoise_config

MONGO_URI = "mongodb://localhost:27017/devdox"

@pytest_asyncio.fixture(scope="function")
async def db_client():
	"""Function-scoped client that connects to session database"""
	# Each test gets its own client in its own event loop
	client, _ = await init_via_uri(MONGO_URI, documents_list=documents_list_loc)
	try:
		yield client
	finally:
		await client.close()

@pytest_asyncio.fixture(scope="function", autouse=True)
async def cleanup_db(db_client):
	"""Clean up the database after each test"""
	for doc_model in documents_list_loc:
		await doc_model.delete_all()

	yield


@pytest_asyncio.fixture(scope="function")
async def postgresql_client():
	"""Function-scoped client that connects to session database"""
	# Each test gets its own client in its own event loop
	
	TORTOISE_ORM = get_tortoise_config(
		db_min_connections=1, db_max_connections=10,
		supabase_rest_api=False, supabase_url=None, supabase_secret_key=None,
		supabase_host="aws-0-eu-central-1.pooler.supabase.com", supabase_port=5432, supabase_user="postgres.ucbaoxkhzoqjmssidrqw", supabase_password="b_hd{0,13}b_hd{0,13}", supabase_db_name="postgres",
		search_path="public",
	)
	
	await Tortoise.init(config=TORTOISE_ORM)
	
	try:
		yield
	finally:
		await Tortoise.close_connections()

@pytest_asyncio.fixture(scope="function", autouse=True)
async def postgresql_db(postgresql_client):
	"""Clean up the database after each test"""
	for app_models in Tortoise.apps.values():
		for model in app_models.values():
			# Skip Tortoise metadata models if any
			if model._meta.abstract:
				continue
			await model.all().delete()

	yield

