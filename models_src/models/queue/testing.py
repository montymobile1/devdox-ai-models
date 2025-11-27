import re
from enum import Enum, IntEnum, StrEnum
from urllib.parse import urlparse
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

testing_queue_name: str = "testing"

class TestingJobType(StrEnum):
    LOAD_LOCUST = "load_locust"

class TestingPriority(IntEnum):
    LEVEL_1 = 1

class TestingDatabaseType(str, Enum):
    EMPTY = ""
    MONGO = "mongo"

class LoadTestRequest(BaseModel):
    """Request wrapper for Load tests"""

    url: str = Field(
        ...,
        description="Swagger url of documentation, example='https://api.shop.example.com/v1/openapi.json'",
        min_length=1
    )
    
    repo_alias_name:str = Field(
	    ...,
	    description="The repository alias name, example='my-project'"
    )
    
    auth: bool = Field(
        ...,
        description="Whether the API requires authentication",
    )
    
    db_type: str = Field(
        default=TestingDatabaseType.EMPTY,
        description="Type of load test to run"
    )

    output_path: str | None = Field(
            default=None,
            description="Custom output path for generated tests. If not provided, uses repo_alias_name + '_test', example='my-project-tests'",
            max_length=200
        )

    spawn_rate: int = Field(
            default=10,
            description="Number of users to spawn per second during load test",
            ge=1,  # Greater than or equal to 1
            le=1000  # Less than or equal to 1000
        )

    run_time: str = Field(
            default="5m",
            description="Duration to run the load test (e.g., '5m', '30s', '2h')",
            pattern=r'^\d+[smh]$'  # Pattern: number followed by s/m/h
        )

    host: str = Field(
            default="localhost",
            description="Target host for load testing (without protocol), example='api.shop.example.com'",
            min_length=1,
            max_length=255
        )
    
    custom_requirement: str = Field(
            default="",
            description="Custom authentication or requirements (empty if none), example='Bearer <token>'",
            max_length=1000
        )

    @field_validator('db_type')
    @classmethod
    def validate_db_type(cls, v: str) -> str:
        """
        Comprehensive db_type validator with normalization
        - Strips whitespace and normalizes case
        - Validates against TestingDatabaseType enum
        - Provides helpful error messages
        """
        if v is None:
            v = ""

        # Normalize input
        normalized = str(v).strip().lower()

        # Create mapping for case-insensitive comparison
        enum_mapping = {db_type.value.lower(): db_type.value for db_type in TestingDatabaseType}

        if normalized not in enum_mapping:
            allowed_display = [f"'{db_type.value}'" if db_type.value else "''" for db_type in TestingDatabaseType]
            raise ValueError(
                f"Invalid database type: {repr(v)}. "
                f"Must be one of: {', '.join(allowed_display)}"
            )

        # Return the canonical form
        return enum_mapping[normalized]

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
            """Validate that URL is properly formatted and accessible"""
            if not v or not v.strip():
                raise ValueError("URL cannot be empty")

            v = v.strip()

            if not v.startswith(('http://', 'https://')):
                v = f'https://{v}'

            # Parse URL to validate format
            try:
                parsed = urlparse(v)
                if not parsed.netloc:
                    raise ValueError("Invalid URL format")
                if parsed.scheme not in ['http', 'https']:
                    raise ValueError("URL must use http or https protocol")
            except Exception as e:
                raise ValueError(f"Invalid URL: {e}")

            # Check for common OpenAPI/Swagger patterns
            openapi_patterns = [
                'openapi.json', 'swagger.json', 'api-docs',
                'docs/json', 'v1/openapi', 'v2/openapi', 'v3/openapi'
            ]

            if not any(pattern in v.lower() for pattern in openapi_patterns):
                # Warning but don't fail - could be a valid custom endpoint
                pass
            return v

    @field_validator('repo_alias_name')
    @classmethod
    def validate_repo_alias_name(cls, v: str) -> str:
            """Validate repository alias name"""
            if not v or not v.strip():
                raise ValueError("Repository alias name cannot be empty")

            v = v.strip()
            # Check for valid identifier pattern
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', v):
                raise ValueError(
                    "Repository alias must start with a letter and contain only "
                    "letters, numbers, hyphens, and underscores"
                )

            # Reserved names check
            reserved_names = {'test', 'tmp', 'temp', 'admin', 'root', 'system'}
            if v.lower() in reserved_names:
                raise ValueError(f"'{v}' is a reserved name, please choose another")
            return v

    @field_validator('output_path')
    @classmethod
    def validate_output_path(cls, v: str | None) -> str | None:
            """Validate and clean output path"""
            if v is None or not v.strip():
                return None

            v = v.strip()

            # Basic path validation
            if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$', v):
                raise ValueError(
                    "Output path must contain only letters, numbers, hyphens, and underscores"
                )

            return v

    @field_validator('run_time')
    @classmethod
    def validate_run_time(cls, v: str) -> str:
            """Validate run time format and reasonable values"""
            if not v or not v.strip():
                raise ValueError("Run time cannot be empty")

            v = v.strip().lower()

            # Extract number and unit
            match = re.match(r'^(\d+)([smh])$', v)
            if not match:
                raise ValueError("Run time must be in format: number + unit (s/m/h). Example: '30s', '5m', '2h'")

            duration, unit = match.groups()
            duration = int(duration)

            # Validate reasonable ranges
            if unit == 's' and (duration < 10 or duration > 3600):  # 10 seconds to 1 hour
                raise ValueError("Seconds must be between 10 and 3600")
            elif unit == 'm' and (duration < 1 or duration > 60):  # 1 to 60 minutes
                raise ValueError("Minutes must be between 1 and 60")
            elif unit == 'h' and (duration < 1 or duration > 24):  # 1 to 24 hours
                raise ValueError("Hours must be between 1 and 24")
            return v

    @field_validator('host')
    @classmethod
    def validate_host(cls, v: str) -> str:
            """Validate host format"""
            if not v or not v.strip():
                raise ValueError("Host cannot be empty")

            v = v.strip().lower()
            # Remove protocol if accidentally included
            v = re.sub(r'^https?://', '', v)
            # Remove trailing slash
            v = v.rstrip('/')
            # Basic hostname validation
            if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$', v):
                raise ValueError("Invalid host format")

            # Check for localhost variations
            if v in ['localhost', '127.0.0.1', '0.0.0.0']:
                return v

            # Validate domain format
            if '.' in v:
                parts = v.split('.')
                if len(parts) < 2:
                    raise ValueError("Host must be a valid domain or IP address")

                # Check TLD
                if len(parts[-1]) < 2:
                    raise ValueError("Invalid top-level domain")

            return v

    @field_validator('custom_requirement')
    @classmethod
    def validate_custom_requirement(cls, v: str) -> str:
            """Clean and validate custom requirement"""
            if v is None:

                return ""

            v = str(v).strip()

            # Security check - don't allow potentially dangerous content
            dangerous_patterns = ['<script', 'javascript:', 'eval(', 'exec(']
            if any(pattern in v.lower() for pattern in dangerous_patterns):
                raise ValueError("Custom requirement contains potentially dangerous content")
            return v



    def get_effective_output_path(self) -> str:
            """Get the effective output path with fallback logic"""
            if self.output_path and self.output_path.strip():
                return self.output_path.strip()
            return f"{self.repo_alias_name}_test"


    def get_run_time_seconds(self) -> int:
            """Convert run_time to seconds for internal use"""
            match = re.match(r'^(\d+)([smh])$', self.run_time.lower())
            if not match:
                return 300  # Default 5 minutes

            duration, unit = match.groups()
            duration = int(duration)

            if unit == 's':
                return duration
            elif unit == 'm':
                return duration * 60
            elif unit == 'h':
                return duration * 3600
            return 300  # Fallback

    def is_https_required(self) -> bool:
            """Check if HTTPS is required based on URL"""
            return self.url.startswith('https://')

    def get_base_url(self) -> str:
            """Extract base URL for testing"""
            protocol = 'https' if self.is_https_required() else 'http'
            return f"{protocol}://{self.host}"


class LoadLocustPayload(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    
    repo_id: str = Field(..., description="The repository id on the hosting platform")
    token_id: str = Field(..., description="The `id` of the git_label")
    config: dict | None = Field(default_factory=dict, description="If you want to pass any extra configurations to the queue engine")
    data: LoadTestRequest = Field(..., description="payload data for the locust test")
    user_id: str = Field(..., description="the id of the user on the authentication platform")
    priority: TestingPriority = Field(..., description="The priority of the job on the queue")
    git_token: str = Field(..., description="The `id` of the git_label")
    git_provider: str = Field(..., description="The `git_provider` of the git_label")
    auth_token: str | None = Field(default=None, description="The encrypted git token extracted from `x-git-token` in the header")
    context_id: str = Field(default_factory=lambda: uuid4().hex, description="A randomly generated code to be able to identify the job")


class TestingQPayload(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    
    job_type: TestingJobType = Field(..., description="The type of the job")
    payload: LoadLocustPayload = Field(..., description="The payload of the job")