from pydantic import SecretStr

from models_src.configs.mongo_config import MongoConfig


class TestMongoConfigBuildURI:

    def test_defaults_no_auth_no_params(self):
        config = MongoConfig()
        expected = "mongodb://localhost:27017/app"
        assert config.build_uri() == expected

    def test_single_host_with_credentials(self):
        config = MongoConfig(
            USERNAME="alice",
            PASSWORD=SecretStr("s3cr3t"),
        )
        expected = "mongodb://alice:s3cr3t@localhost:27017/app"
        assert config.build_uri() == expected
    
    def test_single_host_with_username_credentials_only(self):
        config = MongoConfig(
            USERNAME="alice"
        )
        expected = "mongodb://alice@localhost:27017/app"
        assert config.build_uri() == expected
    
    def test_credentials_are_percent_encoded(self):
        config = MongoConfig(
            USERNAME="user@domain.com",
            PASSWORD=SecretStr("p@ss word"),
        )
        uri = config.build_uri()
        assert "user%40domain.com:p%40ss%20word@" in uri

    def test_auth_db_adds_authSource_if_missing(self):
        config = MongoConfig(AUTH_DB="admin")
        uri = config.build_uri()
        assert uri.endswith("?authSource=admin")

    def test_auth_db_does_not_override_explicit_param(self):
        config = MongoConfig(
            AUTH_DB="ignored",
            PARAMS={"authSource": "explicit"}
        )
        uri = config.build_uri()
        assert "authSource=explicit" in uri
        assert "authSource=ignored" not in uri

    def test_all_query_params_encoded(self):
        config = MongoConfig(PARAMS={"retryWrites": "true", "tls": "true"})
        uri = config.build_uri()
        assert "retryWrites=true" in uri
        assert "tls=true" in uri

    def test_multiple_hosts_respects_port_specification(self):
        config = MongoConfig(
            HOST="host1:27017,host2:27018",
            PORT=12345  # Should be ignored
        )
        uri = config.build_uri()
        assert "host1:27017,host2:27018" in uri
        assert ":12345" not in uri

    def test_srv_uri_ignores_port(self):
        config = MongoConfig(
            SCHEME="mongodb+srv",
            HOST="cluster.mongodb.net",
            PORT=12345  # Should be ignored
        )
        uri = config.build_uri()
        assert "mongodb+srv://cluster.mongodb.net/app" in uri
        assert ":12345" not in uri
