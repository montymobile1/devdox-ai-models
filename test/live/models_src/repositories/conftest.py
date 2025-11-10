import pytest_asyncio

from models_src.db_inits.beanie_init import documents_list_loc, init_via_uri

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