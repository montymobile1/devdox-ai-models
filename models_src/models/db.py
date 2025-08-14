from tortoise import Tortoise


async def init_db(db_url: str, models: list[str]):
    await Tortoise.init(db_url=db_url, modules={"models": models})
    await Tortoise.generate_schemas()


async def close_db():
    await Tortoise.close_connections()
