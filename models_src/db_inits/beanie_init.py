from beanie import init_beanie
from pymongo import AsyncMongoClient
from bson.codec_options import CodecOptions, UuidRepresentation
from urllib.parse import quote, urlencode

from models_src.configs.mongo_config import MongoConfig
from models_src.models.beanie_odm.api_key_document import APIKEY
from models_src.models.beanie_odm.api_log_document import ApiLog
from models_src.models.beanie_odm.code_chunks_document import CodeChunks
from models_src.models.beanie_odm.git_label_document import GitLabel
from models_src.models.beanie_odm.queue_job_claim_registry_document import QueueProcessingRegistry
from models_src.models.beanie_odm.repo_document import Repo
from models_src.models.beanie_odm.user_document import User

STANDARDIZED_UUID_CODEC = UuidRepresentation.STANDARD

def get_standard_uuid_codec():
    """
    We store Mongo `_id` as real UUID objects (binary), not strings.
    
    Problem:
      MongoDB drivers historically wrote UUIDs using different binary encodings
      (“representations”: pythonLegacy, javaLegacy, csharpLegacy, etc.). If one
      service writes with one representation and another reads/queries with a
      different one, the *same* logical UUID becomes different bytes. Effects:
        - find() by _id fails for existing documents
        - unique indexes allow duplicates
        - cross-language lookups and references break
    
    Decision:
      Force RFC-4122 / BSON subtype 4 via `UuidRepresentation.STANDARD` so all
      services encode/decode UUIDs identically.
    
    Scope:
      Apply this at DB acquisition level. Every service touching this DB must
      use the same setting.
    
    Constraints (DO NOT):
      Changing representation later does not rewrite already stored data in mongoDB. Mixing
      representations in the same field creates non-equal values for equal UUIDs
    
    Alternative:
      If we ever define IDs as strings instead of UUID objects in Beanie Document, this setting is
      unnecessary (strings bypass representation issues)
    """
    return CodecOptions(uuid_representation=STANDARDIZED_UUID_CODEC)

documents_list_loc = [
    ApiLog, APIKEY, CodeChunks, GitLabel, QueueProcessingRegistry, Repo, User
]

async def init_via_uri(mongo_uri: str, documents_list=None):
    if documents_list is None:
        documents_list = documents_list_loc
    
    client = AsyncMongoClient(mongo_uri)

    codec = get_standard_uuid_codec()
    db = client.get_default_database(codec_options=codec)
    
    await init_beanie(
        database=db,
        document_models=documents_list
    )
    return client, db

def build_uri(mongo_conf: MongoConfig) -> str:
    """
    Build a standards-compliant MongoDB URI with optional credentials and query params.
    Ensures username/password are percent-encoded when present.
    """
    # userinfo
    creds = ""
    if mongo_conf.USERNAME:
        if mongo_conf.PASSWORD and mongo_conf.PASSWORD.get_secret_value() != "":
            creds = f"{quote(mongo_conf.USERNAME)}:{quote(mongo_conf.PASSWORD.get_secret_value())}@"
        else:
            creds = f"{quote(mongo_conf.USERNAME)}@"
    
    # hosts
    hosts = mongo_conf.HOST
    if mongo_conf.SCHEME != "mongodb+srv":
        # If single host without an explicit port, append default port
        if "," not in hosts and ":" not in hosts:
            hosts = f"{hosts}:{mongo_conf.PORT}"
    
    # query params
    q: dict[str, str] = dict(mongo_conf.PARAMS or {})
    if mongo_conf.AUTH_DB and "authSource" not in q:
        q["authSource"] = mongo_conf.AUTH_DB
    query = f"?{urlencode(q)}" if q else ""
    
    db_name = ""
    if mongo_conf.DB:
        db_name = mongo_conf.DB
    
    return f"{mongo_conf.SCHEME}://{creds}{hosts}/{db_name}{query}"