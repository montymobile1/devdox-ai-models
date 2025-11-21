from pydantic import SecretStr

from models_src.configs.mongo_config import MongoConfig
from models_src.db_inits.beanie_init import build_uri

ConfClass = MongoConfig

class TestMongoConfigBuildURI:
	
	def test_defaults_no_auth_no_params(self):
		config = ConfClass(_env_file=None)
		expected = "mongodb://localhost:27017/"
		assert build_uri(mongo_conf=config) == expected
	
	def test_single_host_with_credentials(self):
		config = ConfClass(
			_env_file=None,
			USERNAME="alice",
			PASSWORD=SecretStr("s3cr3t"),
		)
		expected = "mongodb://alice:s3cr3t@localhost:27017/"
		assert build_uri(mongo_conf=config) == expected
	
	def test_single_host_with_username_credentials_only(self):
		config = ConfClass(
			_env_file=None,
			USERNAME="alice"
		)
		expected = "mongodb://alice@localhost:27017/"
		assert build_uri(mongo_conf=config) == expected
	
	def test_credentials_are_percent_encoded(self):
		config = ConfClass(
			_env_file=None,
			USERNAME="user@domain.com",
			PASSWORD=SecretStr("p@ss word"),
		)
		uri = build_uri(mongo_conf=config)
		assert "user%40domain.com:p%40ss%20word@" in uri
	
	def test_auth_db_adds_authSource_if_missing(self):
		config = ConfClass(
			_env_file=None,
			AUTH_DB="admin"
		)
		uri = build_uri(mongo_conf=config)
		assert uri.endswith("?authSource=admin")
	
	def test_auth_db_does_not_override_explicit_param(self):
		config = ConfClass(
			_env_file=None,
			AUTH_DB="ignored",
			PARAMS={"authSource": "explicit"}
		)
		uri = build_uri(mongo_conf=config)
		assert "authSource=explicit" in uri
		assert "authSource=ignored" not in uri
	
	def test_all_query_params_encoded(self):
		config = ConfClass(_env_file=None, PARAMS={"retryWrites": "true", "tls": "true"})
		uri = build_uri(mongo_conf=config)
		assert "retryWrites=true" in uri
		assert "tls=true" in uri
	
	def test_multiple_hosts_respects_port_specification(self):
		config = ConfClass(
			_env_file=None,
			HOST="host1:27017,host2:27018",
			PORT=12345  # Should be ignored
		)
		uri = build_uri(mongo_conf=config)
		assert "host1:27017,host2:27018" in uri
		assert ":12345" not in uri
	
	def test_srv_uri_ignores_port(self):
		config = ConfClass(
			_env_file=None,
			SCHEME="mongodb+srv",
			HOST="cluster.mongodb.net",
			PORT=12345  # Should be ignored
		)
		uri = build_uri(mongo_conf=config)
		assert "mongodb+srv://cluster.mongodb.net/" in uri
		assert ":12345" not in uri
