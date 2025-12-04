# test_load_testing_models.py

import pytest
from pydantic import ValidationError

from models_src.models.queue.testing import LoadLocustPayload, LoadTestRequest, TestingDatabaseType, TestingJobType, \
	TestingPriority, TestingQPayload



def _make_valid_request(**overrides) -> LoadTestRequest:
    base = dict(
        url="https://api.shop.example.com/v1/openapi.json",
        repo_alias_name="my_project",
        auth=True,
        db_type=TestingDatabaseType.EMPTY,
        output_path=None,
        spawn_rate=10,
        run_time="5m",
        host="api.shop.example.com",
        custom_requirement="",
    )
    # IMPORTANT: always override, even if the value is falsy like "" or 0
    base.update(overrides)
    return LoadTestRequest(**base)


# -----------------------------
# db_type validation
# -----------------------------

def test_db_type_default_is_empty_like():
    req = _make_valid_request()
    # default is TestingDatabaseType.EMPTY enum which compares equal to ""
    assert req.db_type == TestingDatabaseType.EMPTY or req.db_type == ""


def test_db_type_accepts_valid_values_and_normalizes():
    cases = [
        ("mongo", "mongo"),
        (" MONGO ", "mongo"),
        ("mongo ", "mongo"),
        ("", ""),
        ("   ", ""),
    ]
    for raw, expected in cases:
        req = _make_valid_request(db_type=raw)
        assert req.db_type == expected


def test_db_type_rejects_invalid_value():
    with pytest.raises(ValidationError) as exc_info:
        _make_valid_request(db_type="postgres")
    errors = exc_info.value.errors()
    assert any("Invalid database type" in err["msg"] for err in errors)


# -----------------------------
# url validation
# -----------------------------

def test_url_adds_https_if_missing_and_strips_whitespace():
    req = _make_valid_request(url="  api.shop.example.com/v1/openapi.json  ")
    assert req.url == "https://api.shop.example.com/v1/openapi.json"


def test_url_preserves_valid_http_and_https():
    url_http = "http://api.shop.example.com/v1/openapi.json"
    url_https = "https://api.shop.example.com/v1/openapi.json"

    req_http = _make_valid_request(url=url_http)
    req_https = _make_valid_request(url=url_https)

    assert req_http.url == url_http
    assert req_https.url == url_https


def test_url_rejects_empty_and_invalid_formats():
    """
    - Empty string should raise ValidationError (min_length / URL validator)
    - Whitespace-only should hit the 'URL cannot be empty' validator
    """
    base_kwargs = dict(
        repo_alias_name="my_project",
        auth=True,
        db_type=TestingDatabaseType.EMPTY,
        output_path=None,
        spawn_rate=10,
        run_time="5m",
        host="api.shop.example.com",
        custom_requirement="",
    )

    # Completely empty string → should NOT validate
    with pytest.raises(ValidationError):
        LoadTestRequest(url="", **base_kwargs)

    # Whitespace-only → should trigger our custom "URL cannot be empty" message
    with pytest.raises(ValidationError) as exc_info:
        LoadTestRequest(url="   ", **base_kwargs)

    errors = exc_info.value.errors()
    assert any("URL cannot be empty" in err["msg"] for err in errors)


# -----------------------------
# repo_alias_name validation
# -----------------------------

def test_repo_alias_name_validation_happy_path():
    req = _make_valid_request(repo_alias_name="my_repo-123")
    assert req.repo_alias_name == "my_repo-123"


def test_repo_alias_name_rejects_blank():
    for bad in ["", "   "]:
        with pytest.raises(ValidationError) as exc_info:
            _make_valid_request(repo_alias_name=bad)
        assert any("Repository alias name cannot be empty" in err["msg"] for err in exc_info.value.errors())


def test_repo_alias_name_rejects_invalid_characters_and_reserved():
    # Must start with a letter and only contain allowed chars
    with pytest.raises(ValidationError) as exc_info:
        _make_valid_request(repo_alias_name="1invalid")
    assert any("Repository alias must start with a letter" in err["msg"] for err in exc_info.value.errors())

    with pytest.raises(ValidationError) as exc_info:
        _make_valid_request(repo_alias_name="my.project")
    assert any("Repository alias must start with a letter" in err["msg"] for err in exc_info.value.errors())

    # Reserved names
    for reserved in ["test", "Test", "ADMIN"]:
        with pytest.raises(ValidationError) as exc_info:
            _make_valid_request(repo_alias_name=reserved)
        assert any("is a reserved name, please choose another" in err["msg"] for err in exc_info.value.errors())


# -----------------------------
# output_path validation
# -----------------------------

def test_output_path_defaults_to_none_and_validates_characters():
    # default
    req = _make_valid_request()
    assert req.output_path is None

    # explicit None
    req = _make_valid_request(output_path=None)
    assert req.output_path is None

    # blank => normalized to None
    for val in ["", "   "]:
        req = _make_valid_request(output_path=val)
        assert req.output_path is None

    # valid paths
    req = _make_valid_request(output_path="my-output_01")
    assert req.output_path == "my-output_01"

    # invalid characters (slashes, spaces, dots, etc.)
    for bad in ["bad/path", "bad path", "/leading", "trailing/", "with.dot"]:
        with pytest.raises(ValidationError) as exc_info:
            _make_valid_request(output_path=bad)
        assert any(
            "Output path must contain only letters, numbers, hyphens, and underscores"
            in err["msg"]
            for err in exc_info.value.errors()
        )


# -----------------------------
# run_time validation + helpers
# -----------------------------

def test_run_time_accepts_valid_ranges():
    for value in ["30s", "10s", "3600s", "1m", "60m", "1h", "24h"]:
        req = _make_valid_request(run_time=value)
        assert req.run_time == value


def test_run_time_rejects_out_of_range_seconds_minutes_hours():
    for value, expected_msg in [
        ("5s", "Seconds must be between 10 and 3600"),
        ("4000s", "Seconds must be between 10 and 3600"),
        ("0m", "Minutes must be between 1 and 60"),
        ("61m", "Minutes must be between 1 and 60"),
        ("0h", "Hours must be between 1 and 24"),
        ("25h", "Hours must be between 1 and 24"),
    ]:
        with pytest.raises(ValidationError) as exc_info:
            _make_valid_request(run_time=value)
        assert any(expected_msg in err["msg"] for err in exc_info.value.errors())


def test_run_time_rejects_completely_invalid_values():
    for value in ["", "   ", "abc", "10x"]:
        with pytest.raises(ValidationError):
            _make_valid_request(run_time=value)


def test_get_run_time_seconds_converts_units_and_has_fallback():
    req = _make_valid_request(run_time="30s")
    assert req.get_run_time_seconds() == 30

    req = _make_valid_request(run_time="5m")
    assert req.get_run_time_seconds() == 5 * 60

    req = _make_valid_request(run_time="2h")
    assert req.get_run_time_seconds() == 2 * 3600

    # Fallback when pattern doesn't match (simulate post-validation mutation)
    req = _make_valid_request()
    req.run_time = "not-a-duration"
    assert req.get_run_time_seconds() == 300


# -----------------------------
# spawn_rate validation
# -----------------------------

def test_spawn_rate_respects_bounds():
    for value in [1, 500, 1000]:
        req = _make_valid_request(spawn_rate=value)
        assert req.spawn_rate == value

    for bad in [0, -1, 1001]:
        with pytest.raises(ValidationError) as exc_info:
            _make_valid_request(spawn_rate=bad)
        # We don't care whether it's ge or le, only that it's rejected somehow
        assert exc_info.value.errors()


# -----------------------------
# host validation
# -----------------------------

def test_host_normalization_and_validation():
    # Basic normalization + lowercasing
    req = _make_valid_request(host=" Api.Shop.EXAMPLE.com/ ")
    assert req.host == "api.shop.example.com"

    # Strip protocol
    req = _make_valid_request(host="https://Api.Example.com/")
    assert req.host == "api.example.com"

    # Localhost / IPs are allowed as-is
    for host in ["localhost", "127.0.0.1", "0.0.0.0"]:
        req = _make_valid_request(host=host)
        assert req.host == host

    # Invalid characters
    for bad in ["invalid_host!", "space host", "bad*host"]:
        with pytest.raises(ValidationError) as exc_info:
            _make_valid_request(host=bad)
        assert any("Invalid host format" in err["msg"] for err in exc_info.value.errors())

    # Domain must have valid TLD when dot is present
    with pytest.raises(ValidationError) as exc_info:
        _make_valid_request(host="example.c")
    assert any("Invalid top-level domain" in err["msg"] for err in exc_info.value.errors())

    with pytest.raises(ValidationError) as exc_info:
        _make_valid_request(host="example.")
    assert any("Invalid host format" in err["msg"] for err in exc_info.value.errors())

    # Single-label hosts without dot are allowed (e.g. "example")
    req = _make_valid_request(host="example")
    assert req.host == "example"


# -----------------------------
# custom_requirement validation
# -----------------------------

def test_custom_requirement_default_trim_and_security_checks():
    # default
    req = _make_valid_request()
    assert req.custom_requirement == ""

    # trimming
    req = _make_valid_request(custom_requirement="  Bearer TOKEN  ")
    assert req.custom_requirement == "Bearer TOKEN"

    # dangerous patterns
    for dangerous in [
        "<script>alert(1)</script>",
        "javascript:alert(1)",
        "eval('x')",
        "exec('x')",
    ]:
        with pytest.raises(ValidationError) as exc_info:
            _make_valid_request(custom_requirement=dangerous)
        assert any(
            "Custom requirement contains potentially dangerous content" in err["msg"]
            for err in exc_info.value.errors()
        )


# -----------------------------
# Derived helpers on LoadTestRequest
# -----------------------------

def test_get_effective_output_path_uses_fallback_or_explicit_value():
    # No explicit output_path => repo_alias_name + "_test"
    req = _make_valid_request(repo_alias_name="myRepo", output_path=None)
    assert req.get_effective_output_path() == "myRepo_test"

    # Blank output_path also falls back
    req = _make_valid_request(repo_alias_name="anotherRepo", output_path="  ")
    assert req.get_effective_output_path() == "anotherRepo_test"

    # Explicit non-empty path is used (with trimming)
    req = _make_valid_request(output_path="  custom_path  ")
    assert req.get_effective_output_path() == "custom_path"


def test_is_https_required_and_get_base_url_work_together():
    # Explicit https
    req_https = _make_valid_request(
        url="https://api.shop.example.com/v1/openapi.json",
        host="api.shop.example.com",
    )
    assert req_https.is_https_required() is True
    assert req_https.get_base_url() == "https://api.shop.example.com"

    # Explicit http
    req_http = _make_valid_request(
        url="http://api.shop.example.com/v1/openapi.json",
        host="api.shop.example.com",
    )
    assert req_http.is_https_required() is False
    assert req_http.get_base_url() == "http://api.shop.example.com"

    # No scheme => validator adds https
    req_no_scheme = _make_valid_request(
        url="api.shop.example.com/v1/openapi.json",
        host="api.shop.example.com",
    )
    assert req_no_scheme.is_https_required() is True
    assert req_no_scheme.get_base_url() == "https://api.shop.example.com"


# ============================================================
#           LoadLocustPayload + TestingQPayload
# ============================================================

def _make_valid_payload(**overrides) -> LoadLocustPayload:
    base_data = _make_valid_request()
    base = {
        "repo_id": "repo-123",
        "token_id": "token-456",
        "data": base_data,
        "user_id": "user-789",
        "priority": TestingPriority.LEVEL_1,
        "git_token": "git-token-1",
        "git_provider": "github",
    }
    base.update(overrides)
    return LoadLocustPayload(**base)


def test_load_locust_payload_defaults_and_config():
    payload1 = _make_valid_payload()
    payload2 = _make_valid_payload()

    # default config is an empty dict, and each instance gets its own copy
    assert payload1.config == {}
    assert payload2.config == {}
    assert payload1.config is not payload2.config

    # custom config is respected
    payload3 = _make_valid_payload(config={"extra": True})
    assert payload3.config == {"extra": True}


def test_load_locust_payload_priority_accepts_enum_and_int_and_dumps_as_value():
    payload_enum = _make_valid_payload(priority=TestingPriority.LEVEL_1)
    payload_int = _make_valid_payload(priority=1)

    # In-memory value becomes the enum's underlying value (int)
    assert payload_enum.priority == TestingPriority.LEVEL_1.value == 1
    assert payload_int.priority == TestingPriority.LEVEL_1.value == 1

    dump_enum = payload_enum.model_dump()
    dump_int = payload_int.model_dump()

    assert dump_enum["priority"] == 1
    assert dump_int["priority"] == 1


def test_load_locust_payload_context_id_is_generated_as_hex_string():
    payload_a = _make_valid_payload()
    payload_b = _make_valid_payload()

    assert isinstance(payload_a.context_id, str)
    assert isinstance(payload_b.context_id, str)
    assert len(payload_a.context_id) == 32
    assert len(payload_b.context_id) == 32
    assert payload_a.context_id != payload_b.context_id
    # hex-only
    assert all(ch in "0123456789abcdef" for ch in payload_a.context_id)
    assert all(ch in "0123456789abcdef" for ch in payload_b.context_id)


def test_testing_q_payload_uses_enum_values_for_job_type_and_priority():
    payload = _make_valid_payload()
    job = TestingQPayload(job_type=TestingJobType.LOAD_LOCUST, payload=payload)

    # In-memory value is the enum's underlying value (because of use_enum_values)
    assert job.job_type == TestingJobType.LOAD_LOCUST.value == "load_locust"

    dump = job.model_dump()
    assert dump["job_type"] == "load_locust"
    assert dump["payload"]["priority"] == 1

    # It should also accept the raw string value
    job2 = TestingQPayload(job_type="load_locust", payload=payload)
    assert job2.job_type == "load_locust"
