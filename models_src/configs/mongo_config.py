from typing import Optional, Dict, Literal
from pydantic import Field, SecretStr

from pydantic_settings import BaseSettings, SettingsConfigDict

class MongoConfig(BaseSettings):
    
    model_config = SettingsConfigDict(
        env_prefix="MONGO_",
        extra="ignore",
        case_sensitive=False,
    )
    
    SCHEME: Literal["mongodb", "mongodb+srv"] = Field(
        default="mongodb",
        description="MongoDB URI scheme. Use 'mongodb+srv' for DNS SRV discovery (Atlas etc.). "
                    "When using '+srv', the 'port' setting is ignored."
    )
    
    HOST: str = Field(
        default="localhost",
        description="Hostname(s) of the server or cluster. "
                    "Single node: 'db.example.com' or 'localhost'. "
                    "Replica set: comma-separated hosts, e.g. 'h1:27017,h2:27017,h3:27017'. "
                    "For SRV: 'cluster0.xxxxx.mongodb.net' (ports not included)."
    )
    
    PORT: int = Field(
        default=27017,
        ge=1, le=65535,
        description="TCP port for classic 'mongodb://' URIs. "
                    "Ignored when scheme='mongodb+srv', or when per-host ports are already present."
    )
    
    DB: Optional[str] = Field(
        default=None,
        description="Database name appended in the URI path (.../<db>). "
                    "Required because the initializer calls get_default_database() for Beanie."
    )
    
    USERNAME: Optional[str] = Field(
        default=None,
        description="Username for authentication (e.g., SCRAM). "
                    "Leave unset for unauthenticated connections."
    )
    
    PASSWORD: Optional[SecretStr] = Field(
        default=None,
        description="Password paired with 'username'. Leave unset if not required. "
                    "Stored as SecretStr to avoid accidental logging."
    )
    
    AUTH_DB: Optional[str] = Field(
        default=None,
        description="Authentication database (maps to URI query 'authSource'). "
                    "If omitted, drivers may default to the target DB or 'admin' depending on server config."
    )
    
    PARAMS: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional URI query params merged into the connection string. "
                    "Examples: {'retryWrites':'true','tls':'true','appName':'micro-a',"
                    "'serverSelectionTimeoutMS':'5000'}. "
                    "'authSource' will be added from auth_db if not explicitly provided here."
    )