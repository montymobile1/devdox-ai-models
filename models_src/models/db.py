import asyncpg
from tortoise import connections, Tortoise
from pgvector.asyncpg import register_vector

async def init_db(db_url: str, models: list[str]):
    await Tortoise.init(db_url=db_url, modules={"models": models})
    await Tortoise.generate_schemas()


async def close_db():
    await Tortoise.close_connections()

# Async context manager to get a Tortoise connection and register pgvector on demand
class PgVectorConnection:
    def __init__(self, alias: str = "default"):
        self.db = connections.get(alias)
        self.raw = None  # type: ignore
    
    async def __aenter__(self) -> asyncpg.Connection:
        # Acquire a raw asyncpg.Connection
        self.raw = await self.db._pool.acquire()
        
        # tell asyncpg how to handle pgvector
        await register_vector(self.raw)
        
        return self.raw
    
    async def __aexit__(self, exc_type, exc, tb):
        await self.db._pool.release(self.raw)
        self.raw = None