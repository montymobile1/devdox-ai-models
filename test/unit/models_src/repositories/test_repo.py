import datetime
import uuid

import pytest
from beanie.exceptions import DocumentNotFound
from pymongo.errors import DuplicateKeyError

from models_src.dto.repo import RepoResponseDTO
from models_src.exceptions.base_exceptions import DevDoxModelsException
from models_src.exceptions.local_exception import InMemoryNotFound
from models_src.exceptions.utils import RepoErrors
from models_src.repositories.repo import (
    InMemoryRepoBackend,
    RepoStore,
)
from models_src.models.repo_enums import StatusTypes
from test.conftest import _make_repo_request


@pytest.mark.asyncio
class TestInMemoryRepoBackend:
    inmemory_store = InMemoryRepoBackend

    async def test_save_and_get_by_id(self):
        store = self.inmemory_store()

        req = _make_repo_request(
            user_id="mem-user-1",
            repo_id="mem-repo-1",
            repo_name="mem-repo",
            html_url="https://g.com/mem-repo",
            repo_alias_name="mem-alias",
        )

        saved = await store.save(req)

        assert isinstance(saved, RepoResponseDTO)
        assert isinstance(saved.id, uuid.UUID)
        assert saved.user_id == req.user_id
        assert saved.repo_id == req.repo_id

        fetched = await store.get_by_id(str(saved.id))
        assert fetched is not None
        assert fetched.id == saved.id
    
    async def test_get_by_id_not_found_returns_exception(self):
        store = self.inmemory_store()
        
        with pytest.raises(InMemoryNotFound):
            await store.get_by_id("b0908783-6b99-45ca-8d2b-acb369945374")
    
    async def test_find_by_repo_id_and_repo_id_user_id_and_find_by_id(self):
        store = self.inmemory_store()
        user_id = "mem-user-2"

        saved = await store.save(
            _make_repo_request(
                user_id=user_id,
                repo_id="mem-rid",
                repo_name="mem-rid-repo",
                html_url="https://g.com/mem-rid",
                repo_alias_name="alias-mem-rid",
            )
        )

        by_repo_id = await store.find_by_repo_id("mem-rid")
        assert by_repo_id is not None
        assert by_repo_id.id == saved.id

        by_repo_and_user = await store.find_by_repo_id_user_id("mem-rid", user_id)
        assert by_repo_and_user is not None
        assert by_repo_and_user.id == saved.id

        by_id = await store.find_by_id(str(saved.id))
        assert by_id is not None
        assert by_id.id == saved.id

    async def test_find_all_by_user_id_and_count(self):
        store = self.inmemory_store()
        user_id = "mem-user-3"

        await store.save(
            _make_repo_request(
                user_id=user_id,
                repo_id="r1",
                repo_name="r1",
                html_url="https://g.com/r1",
                repo_alias_name="a1",
            )
        )
        await store.save(
            _make_repo_request(
                user_id=user_id,
                repo_id="r2",
                repo_name="r2",
                html_url="https://g.com/r2",
                repo_alias_name="a2",
            )
        )
        await store.save(
            _make_repo_request(
                user_id="other-user",
                repo_id="rother",
                repo_name="rother",
                html_url="https://g.com/rother",
                repo_alias_name="ao",
            )
        )

        all_for_user = await store.find_all_by_user_id(user_id=user_id, offset=0, limit=10)
        assert len(all_for_user) == 2

        page = await store.find_all_by_user_id(user_id=user_id, offset=1, limit=1)
        assert len(page) == 1

        count = await store.count_by_user_id(user_id=user_id)
        assert count == 2

    async def test_update_analysis_metadata_by_id(self):
        store = self.inmemory_store()
        user_id = "mem-user-4"

        saved = await store.save(
            _make_repo_request(
                user_id=user_id,
                repo_id="meta-id",
                repo_name="meta-id",
                html_url="https://g.com/meta-id",
                repo_alias_name="meta-alias",
            )
        )

        end_time = datetime.datetime.now(datetime.timezone.utc)
        updated = await store.update_analysis_metadata_by_id(
            id=str(saved.id),
            status=StatusTypes.COMPLETED,
            processing_end_time=end_time,
            total_files=5,
            total_chunks=10,
            total_embeddings=15,
        )
        assert updated == 1

        refreshed = await store.get_by_id(str(saved.id))
        assert refreshed is not None
        assert refreshed.status == StatusTypes.COMPLETED
        assert refreshed.processing_end_time == end_time
        assert refreshed.total_files == 5
        assert refreshed.total_chunks == 10
        assert refreshed.total_embeddings == 15

    async def test_find_by_user_id_and_html_url(self):
        store = self.inmemory_store()
        user_id = "mem-user-5"

        saved = await store.save(
            _make_repo_request(
                user_id=user_id,
                repo_id="url-id",
                repo_name="url-id",
                html_url="https://g.com/url-id",
                repo_alias_name="url-alias",
            )
        )

        found = await store.find_by_user_id_and_html_url(
            user_id=user_id,
            html_url="https://g.com/url-id",
        )
        assert found is not None
        assert found.id == saved.id

    async def test_save_context_creates_pending_repo(self):
        store = self.inmemory_store()
        user_id = "mem-user-6"
        repo_id = "ctx-repo"

        saved = await store.save_context(
            repo_id=repo_id,
            user_id=user_id,
            config={"ignored": True},
        )

        assert isinstance(saved, RepoResponseDTO)
        assert saved.user_id == user_id
        assert saved.repo_id == repo_id
        assert saved.status == "pending"

    async def test_update_repo_system_reference_by_id(self):
        store = self.inmemory_store()

        saved = await store.save(
            _make_repo_request(
                user_id="mem-user-7",
                repo_id="sys-ref",
                repo_name="sys-ref",
                html_url="https://g.com/sys-ref",
                repo_alias_name="sys-ref-alias",
            )
        )

        updated = await store.update_repo_system_reference_by_id(
            id=str(saved.id),
            repo_system_reference="sys-ref-123",
        )
        assert updated == 1

        refreshed = await store.get_by_id(str(saved.id))
        assert refreshed is not None
        assert refreshed.repo_system_reference == "sys-ref-123"

    async def test_find_by_user_and_path_and_alias_name(self):
        store = self.inmemory_store()
        user_id = "mem-user-8"

        saved = await store.save(
            _make_repo_request(
                user_id=user_id,
                repo_id="p1",
                repo_name="p1",
                html_url="https://g.com/p1",
                repo_alias_name="alias-p1",
            )
        )
        # manually patch some extra fields
        saved.relative_path = "/users/u/p1"
        saved.repo_alias_name = "alias-p1"

        result_path = await store.find_by_user_and_path(user_id=user_id, relative_path="/users/u/p1")
        assert result_path is not None
        assert result_path.id == saved.id

        result_alias = await store.find_by_user_and_alias_name(
            user_id=user_id,
            repo_alias_name="alias-p1",
        )
        assert result_alias is not None
        assert result_alias.id == saved.id


@pytest.mark.asyncio
class TestRepoStoreValidation:
    repo_store = RepoStore

    async def test_save_duplicate_key_error_wrapped_as_internal_error(self):
        class FakeBackend:
            async def save(self, repo_model):
                raise DuplicateKeyError("duplicate repo")

        store = self.repo_store(storage_backend=FakeBackend())
        req = _make_repo_request()

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.save(repo_model=req)

        exc = exc_info.value
        err = RepoErrors.REPOSITORY_ALREADY_EXIST.value
        assert exc.error_type == err["error_type"]
        assert exc.user_message == err["log_message"]
        assert exc.log_message == err["log_message"]
        assert exc.log_level == "error"

    @pytest.mark.parametrize(
        "repo_id, user_id",
        [
            (None, "user"),
            ("", "user"),
            (" ", "user"),
            ("\t", "user"),
            ("rid", None),
            ("rid", ""),
            ("rid", " "),
            ("rid", "\t"),
        ],
    )
    async def test_save_context_invalid_args_raises_repo_not_exist(
        self,
        repo_id,
        user_id,
    ):
        store = self.repo_store(storage_backend=None)

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.save_context(repo_id=repo_id, user_id=user_id, config={})

        exc = exc_info.value
        err = RepoErrors.REPOSITORY_DOESNT_EXIST.value
        assert exc.error_type == err["error_type"]
        assert exc.user_message == err["log_message"]

    @pytest.mark.parametrize(
        "repo_id",
        [None, "", " ", "\t", "not-a-uuid"],
    )
    async def test_get_by_id_invalid_repo_id_raises_repo_not_exist(self, repo_id):
        store = self.repo_store(storage_backend=None)

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.get_by_id(repo_id=repo_id)

        exc = exc_info.value
        err = RepoErrors.REPOSITORY_DOESNT_EXIST.value
        assert exc.error_type == err["error_type"]
        assert exc.user_message == err["log_message"]

    async def test_get_by_id_backend_not_found_raises_repo_not_exist(self):
        class FakeBackend:
            async def get_by_id(self, repo_id: str):
                raise DocumentNotFound("not found")

        store = self.repo_store(storage_backend=FakeBackend())
        valid_id = str(uuid.uuid4())

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.get_by_id(repo_id=valid_id)

        exc = exc_info.value
        err = RepoErrors.REPOSITORY_DOESNT_EXIST.value
        assert exc.error_type == err["error_type"]
        assert exc.user_message == err["log_message"]

    async def test_find_by_repo_id_user_id_not_found_raises_repo_not_exist(self):
        class FakeBackend:
            async def find_by_repo_id_user_id(self, repo_id: str, user_id: str):
                return None

        store = self.repo_store(storage_backend=FakeBackend())

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.find_by_repo_id_user_id(repo_id="rid", user_id="uid")

        exc = exc_info.value
        err = RepoErrors.REPOSITORY_DOESNT_EXIST.value
        assert exc.error_type == err["error_type"]
        assert exc.user_message == err["log_message"]

    @pytest.mark.parametrize(
        "id_value",
        [None, "", " ", "\t", "not-a-uuid"],
    )
    async def test_find_by_id_invalid_id_returns_none(self, id_value):
        store = self.repo_store(storage_backend=None)

        result = await store.find_by_id(id=id_value)
        assert result is None

    @pytest.mark.parametrize("user_id", [None, "", " ", "\t"])
    async def test_find_all_by_user_id_invalid_user_id_raises_missing_user(
        self,
        user_id,
    ):
        store = self.repo_store(storage_backend=None)

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.find_all_by_user_id(user_id=user_id, offset=0, limit=10)

        exc = exc_info.value
        err = RepoErrors.MISSING_USER_ID.value
        assert exc.error_type == err["error_type"]
        assert exc.user_message == err["log_message"]

    @pytest.mark.parametrize("user_id", [None, "", " ", "\t"])
    async def test_count_by_user_id_invalid_user_id_raises_missing_user(
        self,
        user_id,
    ):
        store = self.repo_store(storage_backend=None)

        with pytest.raises(DevDoxModelsException) as exc_info:
            await store.count_by_user_id(user_id=user_id)

        exc = exc_info.value
        err = RepoErrors.MISSING_USER_ID.value
        assert exc.error_type == err["error_type"]
        assert exc.user_message == err["log_message"]

    @pytest.mark.parametrize(
        "id_value, status, expected",
        [
            (None, "completed", -1),
            ("", "completed", -1),
            (" ", "completed", -1),
            ("\t", "completed", -1),
            ("not-a-uuid", "completed", -1),
            (str(uuid.uuid4()), None, -1),
            (str(uuid.uuid4()), "", -1),
            (str(uuid.uuid4()), " ", -1),
            (str(uuid.uuid4()), "\t", -1),
        ],
    )
    async def test_update_analysis_metadata_by_id_invalid_args_return_minus_one(
        self,
        id_value,
        status,
        expected,
    ):
        store = self.repo_store(storage_backend=None)

        result = await store.update_analysis_metadata_by_id(
            id=id_value,
            status=status,
            processing_end_time=datetime.datetime.now(datetime.timezone.utc),
            total_files=1,
            total_chunks=1,
            total_embeddings=1,
        )
        assert result == expected

    @pytest.mark.parametrize(
        "id_value, repo_system_reference, expected",
        [
            (None, "ref", -1),
            ("", "ref", -1),
            (" ", "ref", -1),
            ("\t", "ref", -1),
            ("not-a-uuid", "ref", -1),
            (str(uuid.uuid4()), None, -1),
            (str(uuid.uuid4()), "", -1),
            (str(uuid.uuid4()), " ", -1),
            (str(uuid.uuid4()), "\t", -1),
        ],
    )
    async def test_update_repo_system_reference_by_id_invalid_args_return_minus_one(
        self,
        id_value,
        repo_system_reference,
        expected,
    ):
        store = self.repo_store(storage_backend=None)

        result = await store.update_repo_system_reference_by_id(
            id=id_value,
            repo_system_reference=repo_system_reference,
        )
        assert result == expected
