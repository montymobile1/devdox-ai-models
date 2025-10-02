import pytest

@pytest.fixture
def no_model_io(monkeypatch):
    from models_src.models import APIKEY, GitLabel, QueueProcessingRegistry, Repo, User

    async def _noop(self, *a, **k):  # instance async no-op
        return None

    for cls in (APIKEY, GitLabel, QueueProcessingRegistry, Repo, User):
        monkeypatch.setattr(cls, "save", _noop, raising=False)
        monkeypatch.setattr(cls, "delete", _noop, raising=False)
        monkeypatch.setattr(cls, "fetch_related", _noop, raising=False)
        monkeypatch.setattr(cls, "refresh_from_db", _noop, raising=False)

    yield

@pytest.fixture
def forbid_db(monkeypatch):
    """
    Fail fast if any code attempts to get a DB connection.
    Helps keep unit tests honest (no accidental I/O).
    """
    from tortoise import connections
    def _boom(*a, **k):
        raise AssertionError("DB access attempted in a unit test")
    monkeypatch.setattr(connections, "get", _boom)
    yield

@pytest.fixture
def freeze_repo_time(monkeypatch):
    """
    Freeze datetime.now(tz=UTC) inside the API repo module so we can assert
    exact timestamps (used by update_last_used_by_id).
    """
    import datetime as _dt
    import models_src.repositories.api_key as repo_mod

    fixed = _dt.datetime(2030, 1, 2, 3, 4, 5, tzinfo=_dt.timezone.utc)

    class _FrozenDatetimeModule:
        timezone = _dt.timezone
        class datetime(_dt.datetime):
            @classmethod
            def now(cls, tz=None):
                # repo calls datetime.datetime.now(datetime.timezone.utc)
                return fixed

    # Patch the module-level 'datetime' that the repo imported
    monkeypatch.setattr(repo_mod, "datetime", _FrozenDatetimeModule)

    return fixed