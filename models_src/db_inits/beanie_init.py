from beanie import init_beanie
from pymongo import AsyncMongoClient
from bson.codec_options import CodecOptions, UuidRepresentation

from models_src.models.api_key_document import APIKEY
from models_src.models.code_chunks_document import CodeChunks
from models_src.models.git_label_document import GitLabel
from models_src.models.queue_job_claim_registry_document import QueueProcessingRegistry
from models_src.models.repo_document import Repo
from models_src.models.user_document import User

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
    APIKEY, CodeChunks, GitLabel, QueueProcessingRegistry, Repo, User
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
