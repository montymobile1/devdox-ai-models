from typing import Any

import asyncpg
from pgvector.asyncpg import register_vector
from tortoise import connections


def get_database_config(
	db_min_connections, db_max_connections,
	supabase_rest_api, supabase_url, supabase_secret_key, search_path,
	supabase_host, supabase_port, supabase_user, supabase_password, supabase_db_name
) -> dict[str, Any]:
    """
     Returns the appropriate database configuration based on available credentials.
    Uses REST API connection when SUPABASE_REST_API is True, otherwise uses direct PostgreSQL.
    """
    base_credentials = {
        "minsize": db_min_connections,
        "maxsize": db_max_connections,
        "ssl": "require",
    }
    # Check if developer wants to use RESTAPI
    if supabase_rest_api:

        # Extract database connection info from Supabase URL
        # Supabase URL format: https://your-project.supabase.co
        if not supabase_url.startswith(
            "https://"
        ) or not supabase_url.endswith(".supabase.co"):
            raise ValueError(f"Invalid Supabase URL format: {supabase_url}")

        project_id = supabase_url.replace("https://", "").replace(
            ".supabase.co", ""
        )
        if not project_id:
            raise ValueError("Unable to extract project ID from Supabase URL")
        credentials = {
            **base_credentials,
            "host": project_id,  # Use project_id directly as host
            "port": 5432,
            "user": "postgres",
            "password": supabase_secret_key,
            "database": "postgres",
            "server_settings": {"search_path": search_path},
        }

    # Method 2: Supabase postgress sql
    else:
        credentials = {
            **base_credentials,
            "host": supabase_host,
            "port": supabase_port,
            "user": supabase_user,
            "password": supabase_password,
            "database": supabase_db_name,
            "server_settings": {"search_path": search_path},
        }

    return {"engine": "tortoise.backends.asyncpg", "credentials": credentials}


def get_tortoise_config(
	db_min_connections, db_max_connections,
	supabase_rest_api, supabase_url, supabase_secret_key, search_path,
	supabase_host, supabase_port, supabase_user, supabase_password, supabase_db_name
):
    
    db_config = get_database_config(
	    db_min_connections=db_min_connections, db_max_connections=db_max_connections,
	    supabase_rest_api=supabase_rest_api, supabase_url=supabase_url, supabase_secret_key=supabase_secret_key, search_path=search_path,
	    supabase_host=supabase_host, supabase_port=supabase_port, supabase_user=supabase_user, supabase_password=supabase_password, supabase_db_name=supabase_db_name
    )
    
    # Add server_settings to the credentials
    db_config["credentials"]["server_settings"] = {"search_path": search_path}

    return {
        "connections": {"default": db_config},
        "apps": {
            "models": {
                "models": [
                    "models_src.models",
                    "aerich.models",  # Required for aerich migrations
                ],
                "default_connection": "default",
            }
        },
        "use_tz": False,
        "timezone": "UTC",
    }

from tortoise import Tortoise


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
