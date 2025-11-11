from typing import Optional, Dict, Literal
from pydantic import BaseModel, Field, SecretStr
from urllib.parse import quote, urlencode

class MongoConfig(BaseModel):
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

    DB: str = Field(
        default="app",
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

    def build_uri(self) -> str:
        """
        Build a standards-compliant MongoDB URI with optional credentials and query params.
        Ensures username/password are percent-encoded when present.
        """
        # userinfo
        creds = ""
        if self.USERNAME:
            if self.PASSWORD and self.PASSWORD.get_secret_value() != "":
                creds = f"{quote(self.USERNAME)}:{quote(self.PASSWORD.get_secret_value())}@"
            else:
                creds = f"{quote(self.USERNAME)}@"

        # hosts
        hosts = self.HOST
        if self.SCHEME != "mongodb+srv":
            # If single host without an explicit port, append default port
            if "," not in hosts and ":" not in hosts:
                hosts = f"{hosts}:{self.PORT}"

        # query params
        q: Dict[str, str] = dict(self.PARAMS or {})
        if self.AUTH_DB and "authSource" not in q:
            q["authSource"] = self.AUTH_DB
        query = f"?{urlencode(q)}" if q else ""

        return f"{self.SCHEME}://{creds}{hosts}/{self.DB}{query}"
