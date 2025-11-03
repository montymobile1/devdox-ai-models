import datetime
import uuid

import pytest

from models_src.dto.api_log import ApiLogRequestDTO, ApiLogResponseDTO
from models_src.test_doubles.repositories.api_log import FakeApiLogStore


def make_fake_api_log(
    *,
    user_id: str = "u1",
    operation_id: str = "op_1",
    path: str = "/v1/demo",
    method: str = "GET",
    request_received_at: datetime.datetime | None = None,
    process_time_ms: int = 123,
    request_body=None,
    response_body=None,
) -> ApiLogResponseDTO:
    """
    Local helper to construct a realistic ApiLogResponseDTO for seeding the fake.
    """
    if request_received_at is None:
        request_received_at = datetime.datetime(2025, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)

    return ApiLogResponseDTO(
        id=uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        user_id=user_id,
        operation_id=operation_id,
        path=path,
        method=method,
        request_received_at=request_received_at,
        process_time_ms=process_time_ms,
        request_body=(request_body if request_body is not None else {"in": "req"}),
        response_body=(response_body if response_body is not None else {"out": "res"}),
    )


@pytest.mark.asyncio
class TestFakeApiLogStore:

    async def test_set_fake_data_populates_store_and_count(self):
        store = FakeApiLogStore()
        a1 = make_fake_api_log(user_id="u1")
        a2 = make_fake_api_log(user_id="u2")

        store.set_fake_data([a1, a2])

        assert store.total_count == 2
        assert store._FakeApiLogStore__get_data_store("u1") is a1
        assert store._FakeApiLogStore__get_data_store("u2") is a2

    async def test_save_assigns_id_created_at_and_inserts(self):
        store = FakeApiLogStore()
        req = ApiLogRequestDTO(
            operation_id="op_create",
            path="/v1/create",
            method="POST",
            user_id="u1",
            request_received_at=datetime.datetime(2025, 1, 2, tzinfo=datetime.timezone.utc),
            process_time_ms=45,
            request_body={"foo": "bar"},
            response_body={"ok": True},
        )

        saved = await store.save(req)

        # fields set by the fake at save-time
        assert isinstance(saved.id, uuid.UUID)
        assert isinstance(saved.created_at, datetime.datetime)

        # echoes of request fields
        assert saved.operation_id == "op_create"
        assert saved.path == "/v1/create"
        assert saved.method == "POST"
        assert saved.user_id == "u1"
        assert saved.request_received_at == datetime.datetime(2025, 1, 2, tzinfo=datetime.timezone.utc)
        assert saved.process_time_ms == 45
        assert saved.request_body == {"foo": "bar"}
        assert saved.response_body == {"ok": True}

        # inserted into the internal mapping
        assert store.total_count == 1
        assert store._FakeApiLogStore__get_data_store("u1") is saved

    async def test_saving_same_user_twice_does_not_duplicate_mapping_and_highlights_count_semantics(self):
        """
        The current Fake uses a dict keyed by user_id and setdefault, so saving the same user twice
        will keep a single mapping but increments total_count twice. This test documents the behavior
        so regressions or desired changes can be made explicitly.
        """
        store = FakeApiLogStore()

        req = ApiLogRequestDTO(
            operation_id="op_x",
            path="/x",
            method="GET",
            user_id="u1",
            request_received_at=datetime.datetime(2025, 1, 3, tzinfo=datetime.timezone.utc),
            process_time_ms=10,
            request_body={"r": 1},
            response_body={"s": 2},
        )

        first = await store.save(req)
        second = await store.save(req)

        # Mapping remains one entry for the user_id key (setdefault keeps the first)
        assert (
            store._FakeApiLogStore__get_data_store("u1") is first
            or store._FakeApiLogStore__get_data_store("u1") is second
        )

        # total_count increments on each save (may diverge from len(dict)); keep as a guardrail for intent
        assert store.total_count == 2
