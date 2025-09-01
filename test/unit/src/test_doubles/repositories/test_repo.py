import uuid
import datetime

import pytest

from models_src.dto.repo import RepoRequestDTO, RepoResponseDTO
from models_src.test_doubles.repositories.repo import FakeRepoStore, StubRepoStore


def make_repo_response(**overrides) -> RepoResponseDTO:
    now = datetime.datetime.now(datetime.timezone.utc)
    return RepoResponseDTO(
        id=overrides.get("id", uuid.uuid4()),
        user_id=overrides.get("user_id", "u1"),
        repo_id=overrides.get("repo_id", "rid-1"),
        repo_name=overrides.get("repo_name", "repo"),
        html_url=overrides.get("html_url", "https://example/repo"),
        repo_alias_name=overrides.get("repo_alias_name", "alias"),
        description=overrides.get("description"),
        default_branch=overrides.get("default_branch", "main"),
        forks_count=overrides.get("forks_count", 0),
        stargazers_count=overrides.get("stargazers_count", 0),
        is_private=overrides.get("is_private", False),
        visibility=overrides.get("visibility"),
        token_id=overrides.get("token_id"),
        created_at=overrides.get("created_at", now),
        updated_at=overrides.get("updated_at", now),
        repo_created_at=overrides.get("repo_created_at"),
        repo_updated_at=overrides.get("repo_updated_at"),
        language=overrides.get("language", []),
        size=overrides.get("size"),
        relative_path=overrides.get("relative_path"),
        total_files=overrides.get("total_files", 0),
        total_chunks=overrides.get("total_chunks", 0),
        processing_start_time=overrides.get("processing_start_time"),
        processing_end_time=overrides.get("processing_end_time"),
        error_message=overrides.get("error_message"),
        last_commit=overrides.get("last_commit", ""),
        status=overrides.get("status", "pending"),
        repo_user_reference=overrides.get("repo_user_reference"),
        repo_system_reference=overrides.get("repo_system_reference"),
    )

@pytest.mark.asyncio
class TestFakeRepoStore:

    async def test_set_fake_data_and_count(self):
        store = FakeRepoStore()
        a = make_repo_response(user_id="u1")
        b = make_repo_response(user_id="u1")
        c = make_repo_response(user_id="u2")
        store.set_fake_data([a, b, c])

        assert store.total_count == 3
        assert len(store.data_store["u1"]) == 2
        assert len(store.data_store["u2"]) == 1

    async def test_save_inserts_and_sets_id(self):
        store = FakeRepoStore()
        req = RepoRequestDTO(
            user_id="u1",
            repo_id="rid-1",
            repo_name="repo",
            html_url="https://example/repo",
            repo_alias_name="alias",
        )

        res = await store.save(req)

        assert isinstance(res.id, uuid.UUID)
        assert store.total_count == 1
        assert res in store.data_store["u1"]

    async def test_find_all_by_user_id_returns_multiple_within_limit(self):
        store = FakeRepoStore()
        items = [make_repo_response(user_id="u1", repo_id=f"rid-{i}") for i in range(5)]
        store.set_fake_data(items)

        res = await store.find_all_by_user_id("u1", offset=0, limit=10)
        assert len(res) == 5  # ensure list methods return ALL applicable items when limit allows

        res2 = await store.find_all_by_user_id("u1", offset=1, limit=2)
        assert len(res2) == 2
        assert res2 == items[1:3]

    async def test_count_by_user_id_counts_all(self):
        store = FakeRepoStore()
        store.set_fake_data([make_repo_response(user_id="u1") for _ in range(3)])
        assert await store.count_by_user_id("u1") == 3

    async def test_get_by_id_with_string_uuid_succeeds(self):
        store = FakeRepoStore()
        a = make_repo_response(user_id="u1")
        store.set_fake_data([a])

        # Fake expects str(UUID) and converts internally
        found = await store.get_by_id(str(a.id))
        assert found is a

    async def test_find_by_repo_id_returns_match_or_none(self):
        store = FakeRepoStore()
        a = make_repo_response(user_id="u1", repo_id="rid-x")
        b = make_repo_response(user_id="u2", repo_id="rid-y")
        store.set_fake_data([a, b])

        m1 = await store.find_by_repo_id("rid-x")
        m2 = await store.find_by_repo_id("missing")

        assert m1 is a
        assert m2 is None

    async def test_find_by_id_accepts_string_uuid_and_returns_item(self):
        store = FakeRepoStore()
        a = make_repo_response(user_id="u1")
        store.set_fake_data([a])

        # Intention: APIs often pass id as str; ensure the fake supports it
        found = await store.find_by_id(str(a.id))
        # Note: current implementation compares UUID to str and will return None, causing this test to fail
        # This test guards the intent so future fixes align with real-world usage.
        assert found is a

    async def test_find_by_user_id_and_html_url_first_match(self):
        store = FakeRepoStore()
        a = make_repo_response(user_id="u1", html_url="https://h/repo1")
        b = make_repo_response(user_id="u1", html_url="https://h/repo2")
        store.set_fake_data([a, b])

        found = await store.find_by_user_id_and_html_url("u1", "https://h/repo2")
        assert found is b

    async def test_update_analysis_metadata_by_id_and_returns_codes(self):
        store = FakeRepoStore()
        
        a = make_repo_response(id=uuid.uuid4(), user_id="u1", repo_id="rid-1", status="pending")
        store.set_fake_data([a])
        
        analysis_metadata = {
            "processing_end_time": datetime.datetime.now(datetime.UTC),
            "total_files": 1,
            "total_chunks": 1,
            "total_embeddings": 1
        }
        
        # invalid inputs
        assert (await store.update_analysis_metadata_by_id("", "s", **analysis_metadata)) == -1
        assert (await store.update_analysis_metadata_by_id(str(a.id), "", **analysis_metadata)) == -1

        # not found
        assert (await store.update_analysis_metadata_by_id("missing", "done", **analysis_metadata)) == 0

        # success
        updated = await store.update_analysis_metadata_by_id(str(a.id), "completed", **analysis_metadata)
        assert updated == 1
        assert a.status == "completed"

    async def test_save_context_creates_pending_and_id(self):
        store = FakeRepoStore()
        res = await store.save_context(repo_id="rid-ctx", user_id="u1", config={"x": 1})
        assert res.status == "pending"
        assert isinstance(res.id, uuid.UUID)
        assert res in store.data_store["u1"]

    async def test_update_repo_system_reference_by_id_validations_and_update(self):
        store = FakeRepoStore()
        a = make_repo_response(user_id="u1")
        store.set_fake_data([a])

        # validations
        assert (await store.update_repo_system_reference_by_id("", "note")) == -1
        assert (await store.update_repo_system_reference_by_id(str(a.id), "")) == -1

        # not found
        assert (await store.update_repo_system_reference_by_id(str(uuid.uuid4()), "ref")) == 0

        # success
        updated = await store.update_repo_system_reference_by_id(str(a.id), "sys-ref")
        assert updated == 1
        assert a.repo_system_reference == "sys-ref"

    async def test_find_by_user_and_path(self):
        store = FakeRepoStore()
        a = make_repo_response(user_id="u1")
        b = make_repo_response(user_id="u1", relative_path="rid-1")
        c = make_repo_response(user_id="u1", relative_path="xyz")
        d = make_repo_response(user_id="u2")

        store.set_fake_data([a,b,c,d])

        result = await store.find_by_user_and_path(user_id=b.user_id, relative_path=b.relative_path)

        assert result == b


@pytest.mark.asyncio
class TestStubRepoStoreStore:
    async def test_output_mechanism(self) -> None:

        # ARRANGE
        stub = StubRepoStore()

        save = stub.save
        get_by_id = stub.get_by_id
        find_by_repo_id = stub.find_by_repo_id
        find_by_id = stub.find_by_id
        update_analysis_metadata_by_id = stub.update_analysis_metadata_by_id
        find_by_user_id_and_html_url = stub.find_by_user_id_and_html_url
        save_context = stub.save_context
        update_repo_system_reference_by_id = stub.update_repo_system_reference_by_id
        count_by_user_id = stub.count_by_user_id
        find_by_user_and_path = stub.find_by_user_and_path

        generated_response = make_repo_response()

        expected_result = {
            save.__name__: generated_response,
            get_by_id.__name__: generated_response,
            find_by_repo_id.__name__: generated_response,
            find_by_id.__name__: generated_response,
            update_analysis_metadata_by_id.__name__: 1,
            find_by_user_id_and_html_url.__name__: generated_response,
            save_context.__name__: generated_response,
            update_repo_system_reference_by_id.__name__: 1,
            count_by_user_id.__name__: 500,
            find_by_user_and_path.__name__: generated_response
        }

        stub.set_output(save, expected_result.get(save.__name__))
        stub.set_output(get_by_id, expected_result.get(get_by_id.__name__))
        stub.set_output(find_by_repo_id, expected_result.get(find_by_repo_id.__name__))
        stub.set_output(find_by_id, expected_result.get(find_by_id.__name__))
        stub.set_output(update_analysis_metadata_by_id, expected_result.get(update_analysis_metadata_by_id.__name__))
        stub.set_output(find_by_user_id_and_html_url, expected_result.get(find_by_user_id_and_html_url.__name__))
        stub.set_output(save_context, expected_result.get(save_context.__name__))
        stub.set_output(update_repo_system_reference_by_id, expected_result.get(update_repo_system_reference_by_id.__name__))
        stub.set_output(count_by_user_id, expected_result.get(count_by_user_id.__name__))
        stub.set_output(find_by_user_and_path, expected_result.get(find_by_user_and_path.__name__))

        # ACT

        await save(
            RepoRequestDTO(
                user_id=generated_response.user_id,
                repo_id=generated_response.repo_id,
                repo_name=generated_response.repo_name,
                html_url=generated_response.html_url,
                repo_alias_name=generated_response.repo_alias_name,
                description=generated_response.description,
                default_branch=generated_response.default_branch,
                forks_count=generated_response.forks_count,
                stargazers_count=generated_response.stargazers_count,
                is_private=generated_response.is_private,
                visibility=generated_response.visibility,
                token_id=generated_response.token_id,
                repo_created_at=generated_response.repo_created_at,
                repo_updated_at=generated_response.repo_updated_at,
                language=generated_response.language,
                size=generated_response.size,
                relative_path=generated_response.relative_path,
                total_files=generated_response.total_files,
                total_chunks=generated_response.total_chunks,
                processing_start_time=generated_response.processing_start_time,
                processing_end_time=generated_response.processing_end_time,
                error_message=generated_response.error_message,
                last_commit=generated_response.last_commit,
                status=generated_response.status,
                repo_user_reference=generated_response.repo_user_reference,
                repo_system_reference=generated_response.repo_system_reference
            )
        )
        
        analysis_metadata = {
            "processing_end_time": datetime.datetime.now(datetime.UTC),
            "total_files": 1,
            "total_chunks": 1,
            "total_embeddings": 1
        }
        
        await get_by_id(repo_id=generated_response.repo_id)
        await find_by_repo_id(repo_id=generated_response.repo_id)
        await find_by_id(id=str(generated_response.id))
        await update_analysis_metadata_by_id(id=generated_response.repo_id, status=generated_response.status, **analysis_metadata)
        await find_by_user_id_and_html_url(user_id=generated_response.user_id, html_url=generated_response.html_url)
        await save_context(repo_id=generated_response.repo_id, user_id=generated_response.user_id, config={})
        await update_repo_system_reference_by_id(id=str(generated_response.id), repo_system_reference=generated_response.repo_system_reference)
        await count_by_user_id(user_id=generated_response.user_id)
        await find_by_user_and_path(user_id=generated_response.user_id, relative_path=generated_response.relative_path)

        # ASSERT
        assert expected_result == stub._outputs



    async def test_find_by_user_and_alias_name(self):
        store = FakeRepoStore()
        a = make_repo_response(user_id="u1", repo_alias_name="alias1")
        b = make_repo_response(user_id="u1", repo_alias_name="alias2")
        c = make_repo_response(user_id="u2", repo_alias_name="alias1")  # Different user

        store.set_fake_data([a, b, c])

        # Test found case
        result = await store.find_by_user_and_alias_name("u1", "alias1")
        assert result == a

        # Test not found case
        result = await store.find_by_user_and_alias_name("u1", "nonexistent")
        assert result is None

        # Test different user
        result = await store.find_by_user_and_alias_name("u2", "alias1")
        assert result == c

    async def test_find_by_user_and_alias_name_stub(self):
        stub = StubRepoStore()
        expected_response = make_repo_response()

        stub.set_output(stub.find_by_user_and_alias_name, expected_response)

        result = await stub.find_by_user_and_alias_name("u1", "alias1")
        assert result == expected_response

