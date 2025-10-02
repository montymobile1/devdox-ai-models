# tests/unit/src/models/test_db_utils_unit.py
import sys
import types
import pytest
from unittest.mock import AsyncMock

# ---- Optional safety: make imports succeed even if asyncpg/pgvector aren't installed
if "asyncpg" not in sys.modules:
    asyncpg_stub = types.ModuleType("asyncpg")
    class _Conn: ...
    asyncpg_stub.Connection = _Conn
    sys.modules["asyncpg"] = asyncpg_stub

if "pgvector" not in sys.modules:
    sys.modules["pgvector"] = types.ModuleType("pgvector")
if "pgvector.asyncpg" not in sys.modules:
    pgv_asyncpg_stub = types.ModuleType("pgvector.asyncpg")
    async def _register_vector_stub(conn): return None
    pgv_asyncpg_stub.register_vector = _register_vector_stub
    sys.modules["pgvector.asyncpg"] = pgv_asyncpg_stub

# ---- Now import the module under test
import models_src.models.db as db_mod


class TestInitCloseDb:
    @pytest.mark.asyncio
    async def test_init_db_calls_tortoise_init_and_generate(self, monkeypatch):
        called = {"init": None, "gen": None}

        async def fake_init(*, db_url, modules):
            called["init"] = (db_url, modules)

        async def fake_gen():
            called["gen"] = True

        monkeypatch.setattr(db_mod.Tortoise, "init", fake_init)
        monkeypatch.setattr(db_mod.Tortoise, "generate_schemas", fake_gen)

        await db_mod.init_db("postgres://u:p@h:5432/db", ["models_src.models"])
        assert called["init"] == ("postgres://u:p@h:5432/db", {"models": ["models_src.models"]})
        assert called["gen"] is True

    @pytest.mark.asyncio
    async def test_close_db_calls_tortoise_close_connections(self, monkeypatch):
        called = {"closed": False}

        async def fake_close():
            called["closed"] = True

        monkeypatch.setattr(db_mod.Tortoise, "close_connections", fake_close)
        await db_mod.close_db()
        assert called["closed"] is True


class TestPgVectorConnection:
    class FakePool:
        def __init__(self, conn):
            self.conn = conn
            self.acquire_calls = 0
            self.release_args = None

        async def acquire(self):
            self.acquire_calls += 1
            return self.conn

        async def release(self, conn):
            self.release_args = conn

    class FakeDb:
        def __init__(self, pool):
            self._pool = pool

    @pytest.mark.asyncio
    async def test_enter_registers_and_returns_raw_then_exit_releases(self, monkeypatch):
        # Arrange: fake raw connection, pool, db, and register_vector
        raw = object()
        pool = self.FakePool(raw)
        db = self.FakeDb(pool)

        captured = {"alias": None}
        def fake_get(alias):
            captured["alias"] = alias
            return db

        reg_calls = {"conn": None}
        async def fake_register_vector(conn):
            reg_calls["conn"] = conn

        monkeypatch.setattr(db_mod.connections, "get", fake_get)
        monkeypatch.setattr(db_mod, "register_vector", fake_register_vector)

        cm = db_mod.PgVectorConnection(alias="secondary")
        assert cm.raw is None

        # Act: enter/exit the context
        async with cm as got_raw:
            # Inside __aenter__
            assert got_raw is raw
            assert cm.raw is raw
            assert pool.acquire_calls == 1
            assert reg_calls["conn"] is raw

        # Assert: __aexit__ released and nulled
        assert pool.release_args is raw
        assert cm.raw is None
        assert captured["alias"] == "secondary"

    @pytest.mark.asyncio
    async def test_exit_still_releases_on_exception(self, monkeypatch):
        raw = object()
        pool = self.FakePool(raw)
        db = self.FakeDb(pool)

        monkeypatch.setattr(db_mod.connections, "get", lambda alias: db)
        # we don't care about register_vector here, but keep it async
        monkeypatch.setattr(db_mod, "register_vector", AsyncMock(return_value=None))

        cm = db_mod.PgVectorConnection()
        with pytest.raises(RuntimeError):
            async with cm:
                raise RuntimeError("boom")

        # release must have happened and raw reset
        assert pool.release_args is raw
        assert cm.raw is None
