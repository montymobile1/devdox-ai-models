from tortoise import Tortoise
from typing import Dict, Any, Optional, List
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration helper compatible with existing microservice patterns."""

    @staticmethod
    def supabase_config(
        project_id: str,
        password: str,
        database: str = "postgres",
        user: str = "postgres",
        port: int = 5432,
        search_path: str = "public",
        min_connections: int = 1,
        max_connections: int = 10,
        ssl: str = "require",
    ) -> Dict[str, Any]:
        """Generate Supabase PostgreSQL configuration."""
        return {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "host": project_id,
                "port": port,
                "user": user,
                "password": password,
                "database": database,
                "minsize": min_connections,
                "maxsize": max_connections,
                "ssl": ssl,
                "server_settings": {"search_path": search_path},
            },
        }

    @staticmethod
    def postgres_config(
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        search_path: str = "public",
        min_connections: int = 1,
        max_connections: int = 10,
        ssl: str = "require",
    ) -> Dict[str, Any]:
        """Generate PostgreSQL configuration."""
        return {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "host": host,
                "port": port,
                "user": user,
                "password": password,
                "database": database,
                "minsize": min_connections,
                "maxsize": max_connections,
                "ssl": ssl,
                "server_settings": {"search_path": search_path},
            },
        }


def get_tortoise_config(
    db_config: Dict[str, Any],
    app_models: Optional[List[str]] = None,
    include_aerich: bool = True,
    use_tz: bool = False,
    timezone: str = "UTC",
) -> Dict[str, Any]:
    """
    Generate Tortoise ORM configuration compatible with existing microservice setup.

    Args:
        db_config: Database configuration from DatabaseConfig methods
        app_models: List of model modules (e.g., ["app.models", "other.models"])
        include_aerich: Whether to include aerich.models for migrations
        use_tz: Whether to use timezone-aware datetimes
        timezone: Default timezone

    Returns:
        Complete Tortoise ORM configuration
    """
    models = ["tortoise_models.models"]

    if app_models:
        models.extend(app_models)

    if include_aerich:
        models.append("aerich.models")

    return {
        "connections": {"default": db_config},
        "apps": {
            "models": {
                "models": models,
                "default_connection": "default",
            }
        },
        "use_tz": use_tz,
        "timezone": timezone,
    }


async def init_tortoise(config: Dict[str, Any]) -> None:
    """Initialize Tortoise ORM with configuration."""
    try:
        await Tortoise.init(config=config)
        logger.info("Tortoise ORM initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Tortoise ORM: {e}")
        raise


async def close_tortoise() -> None:
    """Close Tortoise ORM connections."""
    try:
        await Tortoise.close_connections()
        logger.info("Tortoise ORM connections closed")
    except Exception as e:
        logger.error(f"Error closing Tortoise ORM connections: {e}")
