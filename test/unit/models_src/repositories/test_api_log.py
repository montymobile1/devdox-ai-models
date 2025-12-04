import pytest
import pytest_asyncio

from models_src.repositories.api_log import InMemoryApiLogBackend

from test.live.models_src.repositories.test_api_log import TestApiLogBackend


@pytest.mark.asyncio
class TestInMemoryApiKeyBackend(TestApiLogBackend):
	__test__ = True
	
	@pytest_asyncio.fixture
	async def repo(self):
		return InMemoryApiLogBackend()