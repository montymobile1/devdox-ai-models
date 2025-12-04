import os
from pathlib import Path
from typing import Optional, Literal, Dict

import pytest
from pydantic_settings import BaseSettings, SettingsConfigDict

from models_src.configs.mongo_config import MongoConfig


# ---------------------------------------------
# Fixtures
# ---------------------------------------------

@pytest.fixture(autouse=True)
def _clean_mongo_env(monkeypatch):
    """
    Ensure no real MONGO_* env vars leak into tests.
    """
    for key in list(os.environ.keys()):
        if key.startswith("MONGO_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def tmp_env_file(tmp_path: Path) -> Path:
    """
    Creates a per-test .env file path.
    """
    return tmp_path / ".env.test"


# ---------------------------------------------
# Standalone MongoConfig tests
# ---------------------------------------------

class TestMongoConfigStandalone:
    def test_should_load_defaults_when_no_env(self):
        """MongoConfig() should use pure class defaults if no env present."""
        conf = MongoConfig(_env_file=None)

        assert conf.SCHEME == "mongodb"
        assert conf.HOST == "localhost"
        assert conf.PORT == 27017
        assert conf.DB is None
        assert conf.USERNAME is None
        assert conf.PASSWORD is None
        assert conf.AUTH_DB is None
        assert conf.PARAMS == {}

    def test_should_override_fields_from_prefixed_env_vars(self, monkeypatch):
        """Prefixed env vars (MONGO_*) should override defaults."""
        monkeypatch.setenv("MONGO_SCHEME", "mongodb+srv")
        monkeypatch.setenv("MONGO_HOST", "cluster.example.net")
        monkeypatch.setenv("MONGO_PORT", "12345")
        monkeypatch.setenv("MONGO_DB", "env_db")

        conf = MongoConfig(_env_file=None)

        assert conf.SCHEME == "mongodb+srv"
        assert conf.HOST == "cluster.example.net"
        assert conf.PORT == 12345
        assert conf.DB == "env_db"

    def test_should_load_from_env_file_when_provided(self, tmp_env_file: Path):
        """Passing _env_file should load values from that file."""
        tmp_env_file.write_text(
            "\n".join([
                "MONGO_HOST=filehost",
                "MONGO_DB=file_db",
                "MONGO_PORT=27018",
            ])
        )

        conf = MongoConfig(_env_file=tmp_env_file)

        assert conf.HOST == "filehost"
        assert conf.DB == "file_db"
        assert conf.PORT == 27018

    def test_should_parse_dict_params_from_json_in_env_file(self, tmp_env_file: Path):
        """PARAMS should parse JSON strings into dicts."""
        tmp_env_file.write_text(
            "\n".join([
                "MONGO_PARAMS={\"retryWrites\":\"true\",\"tls\":\"true\"}",
            ])
        )

        conf = MongoConfig(_env_file=tmp_env_file)

        assert conf.PARAMS == {"retryWrites": "true", "tls": "true"}


# ---------------------------------------------
# Mock Pattern-B settings tests
# ---------------------------------------------

class MockSettings(BaseSettings):
    """
    Minimal mock settings to test Pattern-B injection.
    """
    model_config = SettingsConfigDict(extra="ignore", env_file_encoding="utf-8")

    API_ENV: Literal["development", "staging", "production", "test", "local"] = "local"
    SUPABASE_DB: str = "some supabase db"
    SUPABASE_HOST: str = "some supabase host"
    MONGO: Optional[MongoConfig] = None


def load_mock_settings(env_files, mongo_enabled: bool = True) -> MockSettings:
    """
    Pattern-B style loader:
    - both Settings and Mongo read from same env_files
    - Mongo can be disabled (None)
    """
    mongo = MongoConfig(_env_file=env_files) if mongo_enabled else None
    return MockSettings(_env_file=env_files, MONGO=mongo)


class TestMongoConfigInjected:
    def test_should_inject_mongo_when_enabled(self, tmp_env_file: Path):
        """When enabled, MONGO should be a loaded MongoConfig."""
        tmp_env_file.write_text(
            "\n".join([
                "API_ENV=staging",
                "MONGO_HOST=injectedhost",
                "MONGO_DB=injected_db",
            ])
        )

        s = load_mock_settings(tmp_env_file, mongo_enabled=True)

        assert s.MONGO is not None
        assert s.MONGO.HOST == "injectedhost"
        assert s.MONGO.DB == "injected_db"
        assert s.API_ENV == "staging"
        assert s.SUPABASE_DB == "some supabase db"
        assert s.SUPABASE_HOST == "some supabase host"

    def test_should_set_mongo_to_none_when_disabled(self, tmp_env_file: Path):
        """When disabled, MONGO should be None regardless of env."""
        tmp_env_file.write_text(
            "\n".join([
                "MONGO_HOST=should_not_load",
                "MONGO_DB=should_not_load",
            ])
        )

        s = load_mock_settings(tmp_env_file, mongo_enabled=False)

        assert s.MONGO is None
