import pytest
from unittest.mock import MagicMock, AsyncMock

from tortoise.exceptions import DoesNotExist, IntegrityError


from models_src.dto.repo import RepoRequestDTO, RepoResponseDTO
from models_src.repositories.repo import TortoiseRepoStore
import models_src.repositories.repo as repo_mod  # to patch class symbol (Repo) used directly
from test.unit.common_test_tools.model_factories import make_repo
from test.unit.common_test_tools.qs_chain import make_qs_chain


class TestFindAllByUserId:
    @pytest.mark.asyncio
    async def test_orders_desc_pages_and_maps(self, monkeypatch):
        """We ask for a user's repos; it filters, orders newest first, paginates, and returns DTOs."""
        store = TortoiseRepoStore()

        rows = [
            make_repo(user_id="u1", repo_id="r2", repo_name="beta"),
            make_repo(user_id="u1", repo_id="r1", repo_name="alpha"),
        ]
        qs = make_qs_chain(result_for_all=rows)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        out = await store.find_all_by_user_id("u1", offset=2, limit=5)
        assert all(isinstance(x, RepoResponseDTO) for x in out)

        model.filter.assert_called_once_with(user_id="u1")
        qs.order_by.assert_called_once_with("-created_at")
        qs.offset.assert_called_once_with(2 * 5)
        qs.limit.assert_called_once_with(5)
        qs.all.assert_awaited_once()


class TestCountByUserId:
    @pytest.mark.asyncio
    async def test_counts_by_user(self, monkeypatch):
        """Count should just filter by user and call count()."""
        store = TortoiseRepoStore()
        qs = make_qs_chain(count_value=42)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        n = await store.count_by_user_id("u9")
        assert n == 42
        model.filter.assert_called_once_with(user_id="u9")
        qs.count.assert_awaited_once()


class TestSave:
    @pytest.mark.asyncio
    async def test_success_maps_instance(self, monkeypatch):
        """On success we map the created Repo model to a DTO."""
        store = TortoiseRepoStore()
        model = MagicMock()
        model.create = AsyncMock(return_value=make_repo(user_id="u1", repo_id="r1", repo_name="demo"))
        monkeypatch.setattr(store, "model", model)

        req = RepoRequestDTO(
            user_id="u1",
            repo_id="r1",
            repo_name="demo",
            html_url="https://example.com/u1/demo",
            repo_alias_name="alias-demo",
        )
        dto = await store.save(req)
        assert isinstance(dto, RepoResponseDTO)
        assert dto.repo_id == "r1"
        model.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_integrity_error_is_translated(self, monkeypatch):
        """If the (user_id, repo_id) unique pair already exists, we bubble an internal error."""
        store = TortoiseRepoStore()
        model = MagicMock()
        model.create = AsyncMock(side_effect=IntegrityError("duplicate key"))
        monkeypatch.setattr(store, "model", model)

        req = RepoRequestDTO(
            user_id="u1",
            repo_id="r1",
            repo_name="demo",
            html_url="https://example.com/u1/demo",
            repo_alias_name="alias-demo",
        )
        with pytest.raises(Exception):
            await store.save(req)


class TestSaveContext:
    @pytest.mark.asyncio
    async def test_save_context_uses_class_symbol_and_maps(self, monkeypatch):
        """
        save_context calls Repo.create(...) via the class symbol (not store.model).
        We patch the class inside the repo module and return a real model instance.
        """
        store = TortoiseRepoStore()
        fake_class = MagicMock()
        fake_class.create = AsyncMock(return_value=make_repo(user_id="u2", repo_id="RCTX"))
        monkeypatch.setattr(repo_mod, "Repo", fake_class)

        dto = await store.save_context(repo_id="RCTX", user_id="u2", config={"k": "v"})
        assert isinstance(dto, RepoResponseDTO)
        fake_class.create.assert_awaited_once()
        # we don't assert config since DTO doesn't expose it


class TestGetById:
    @pytest.mark.asyncio
    async def test_success_maps_instance(self, monkeypatch):
        """get_by_id should return a DTO when the record exists."""
        store = TortoiseRepoStore()
        model = MagicMock()
        model.get = AsyncMock(return_value=make_repo(repo_id="rX"))
        monkeypatch.setattr(store, "model", model)

        dto = await store.get_by_id("some-id")
        assert isinstance(dto, RepoResponseDTO)
        model.get.assert_awaited_once_with(id="some-id")

    @pytest.mark.asyncio
    async def test_missing_raises_internal_error(self, monkeypatch):
        """If .get() raises DoesNotExist, we raise our internal error."""
        store = TortoiseRepoStore()
        model = MagicMock()
        model.get = AsyncMock(side_effect=DoesNotExist("not found"))
        monkeypatch.setattr(store, "model", model)

        with pytest.raises(Exception):
            await store.get_by_id("missing")


class TestFindByRepoId:
    @pytest.mark.asyncio
    async def test_maps_when_found(self, monkeypatch):
        """filter(repo_id=...).first() is mapped to DTO."""
        store = TortoiseRepoStore()
        qs = make_qs_chain(result_for_first=make_repo(repo_id="abc"))
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        dto = await store.find_by_repo_id("abc")
        assert isinstance(dto, RepoResponseDTO)
        model.filter.assert_called_once_with(repo_id="abc")
        qs.first.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_missing(self, monkeypatch):
        """If first() returns None, we return None."""
        store = TortoiseRepoStore()
        qs = make_qs_chain(result_for_first=None)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        dto = await store.find_by_repo_id("nope")
        assert dto is None
        model.filter.assert_called_once_with(repo_id="nope")
        qs.first.assert_awaited_once()


class TestFindById_UsingClassSymbol:
    @pytest.mark.asyncio
    async def test_uses_class_filter_and_maps(self, monkeypatch):
        """Method calls Repo.filter(...).first() via class symbol; patch it."""
        store = TortoiseRepoStore()
        fake_class = MagicMock()
        fake_class.filter.return_value = make_qs_chain(result_for_first=make_repo(repo_id="ID1"))
        monkeypatch.setattr(repo_mod, "Repo", fake_class)

        dto = await store.find_by_id("ID1")
        assert isinstance(dto, RepoResponseDTO)
        fake_class.filter.assert_called_once_with(id="ID1")


class TestFindByUserIdAndHtmlUrl:
    @pytest.mark.asyncio
    async def test_filters_then_first_and_maps(self, monkeypatch):
        """Filter by (user_id, html_url), then first()."""
        store = TortoiseRepoStore()
        qs = make_qs_chain(result_for_first=make_repo(user_id="u", html_url="https://x/y"))
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        dto = await store.find_by_user_id_and_html_url("u", "https://x/y")
        assert isinstance(dto, RepoResponseDTO)
        model.filter.assert_called_once_with(user_id="u", html_url="https://x/y")
        qs.first.assert_awaited_once()


class TestUpdateAnalysisMetadataById:
    @pytest.mark.asyncio
    async def test_bad_inputs_return_minus1(self):
        """Blank id or blank status -> -1."""
        store = TortoiseRepoStore()
        ts = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        assert await store.update_analysis_metadata_by_id("", "ok", ts, 1, 1, 1) == -1
        assert await store.update_analysis_metadata_by_id("id", "   ", ts, 1, 1, 1) == -1

    @pytest.mark.asyncio
    async def test_updates_expected_fields(self, monkeypatch):
        """filter(id=...).update(status, processing_end_time, totals...)."""
        store = TortoiseRepoStore()
        ts = __import__("datetime").datetime(2030, 1, 1, tzinfo=__import__("datetime").timezone.utc)

        qs = make_qs_chain(update_value=3)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        changed = await store.update_analysis_metadata_by_id(
            id="RID",
            status="completed",
            processing_end_time=ts,
            total_files=10,
            total_chunks=20,
            total_embeddings=30,
        )
        assert changed == 3

        model.filter.assert_called_once_with(id="RID")
        qs.update.assert_awaited_once_with(
            status="completed",
            processing_end_time=ts,
            total_files=10,
            total_chunks=20,
            total_embeddings=30,
        )


class TestUpdateRepoSystemReferenceById:
    @pytest.mark.asyncio
    async def test_bad_inputs_return_minus1(self):
        """Blank id or blank reference -> -1."""
        store = TortoiseRepoStore()
        assert await store.update_repo_system_reference_by_id("", "note") == -1
        assert await store.update_repo_system_reference_by_id("id", "   ") == -1

    @pytest.mark.asyncio
    async def test_updates_reference(self, monkeypatch):
        """filter(id=...).update(repo_system_reference=...)."""
        store = TortoiseRepoStore()
        qs = make_qs_chain(update_value=1)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        changed = await store.update_repo_system_reference_by_id("RID", "auto-note")
        assert changed == 1

        model.filter.assert_called_once_with(id="RID")
        qs.update.assert_awaited_once_with(repo_system_reference="auto-note")


class TestFindByUserAndPath:
    @pytest.mark.asyncio
    async def test_class_symbol_filter_first_maps(self, monkeypatch):
        """find_by_user_and_path uses Repo.filter(...) via class symbol."""
        store = TortoiseRepoStore()
        fake_class = MagicMock()
        fake_class.filter.return_value = make_qs_chain(result_for_first=make_repo(user_id="u", relative_path="/x/y"))
        monkeypatch.setattr(repo_mod, "Repo", fake_class)

        dto = await store.find_by_user_and_path("u", "/x/y")
        assert isinstance(dto, RepoResponseDTO)
        fake_class.filter.assert_called_once_with(user_id="u", relative_path="/x/y")


class TestFindByUserAndAliasName:
    @pytest.mark.asyncio
    async def test_class_symbol_filter_first_maps(self, monkeypatch):
        """find_by_user_and_alias_name uses Repo.filter(...) via class symbol."""
        store = TortoiseRepoStore()
        fake_class = MagicMock()
        fake_class.filter.return_value = make_qs_chain(result_for_first=make_repo(user_id="u", repo_alias_name="alias"))
        monkeypatch.setattr(repo_mod, "Repo", fake_class)

        dto = await store.find_by_user_and_alias_name("u", "alias")
        assert isinstance(dto, RepoResponseDTO)
        fake_class.filter.assert_called_once_with(user_id="u", repo_alias_name="alias")
