import logging
import uuid

import pytest
from bson import UuidRepresentation

from models_src.db_inits.beanie_init import init_via_uri
from models_src.models.beanie_odm.api_key_document import APIKEY

logger = logging.getLogger(__name__)

MONGO_URI = "mongodb://localhost:27017/devdox"


@pytest.mark.asyncio
async def test_connect_to_db():
    client = db = None
    try:
        # 1) init beanie + get handles
        client, db = await init_via_uri(MONGO_URI)

        # 2) DB is reachable
        pong = await db.command("ping")
        assert "ok" in pong and pong["ok"] == 1.0

        # 3) DB name inferred from URI path
        assert db.name == "devdox"

        # 4) UUID representation is enforced
        assert db.codec_options.uuid_representation == UuidRepresentation.STANDARD

        # 5) Insert a Beanie doc, then read it back
        created = await APIKEY(
            user_id="u1",
            api_key="secret",
            masked_api_key="***ret",
            is_active=True,
        ).insert()

        assert isinstance(created.id, uuid.UUID)

        fetched = await APIKEY.get(created.id)
        assert fetched is not None
        assert fetched.user_id == "u1"

        # 6) Collection exists and raw doc decodes to uuid.UUID under our codec
        coll_name = APIKEY.Settings.name  # "api_key" per your model
        names = await db.list_collection_names()
        assert coll_name in names

        raw = await db[coll_name].find_one({"_id": created.id})
        assert raw is not None
        assert isinstance(raw["_id"], uuid.UUID)  # decoded with STANDARD codec
    finally:
        if client is not None and db is not None:
            await client.drop_database(db.name)
            await client.close()