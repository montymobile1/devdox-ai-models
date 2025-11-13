import uuid
import pytest
from unittest.mock import MagicMock, AsyncMock

from models_src.exceptions.utils import GitLabelErrors

from models_src.exceptions.base_exceptions import DevDoxModelsException
from tortoise.exceptions import IntegrityError
from models_src.dto.git_label import GitLabelRequestDTO, GitLabelResponseDTO
from models_src.repositories.git_label import TortoiseGitLabelStore
import models_src.repositories.git_label as repo_mod  # for patching GitLabel used directly in one method
from test.unit.common_test_tools.model_factories import make_gitlabel
from test.unit.common_test_tools.qs_chain import make_qs_chain


class TestTortoiseFindGitHostingsByIds:
    @pytest.mark.asyncio
    async def test_empty_input_returns_empty_list(self, monkeypatch):
        """Empty input → empty list; no DB calls."""
        store = TortoiseGitLabelStore()
        model = MagicMock()
        monkeypatch.setattr(store, "model", model)
        assert await store.find_git_hostings_by_ids([]) == []
        model.filter.assert_not_called()

    @pytest.mark.asyncio
    async def test_filters_by_ids_and_calls_values(self, monkeypatch):
        """Filter id__in then .values('id','git_hosting')."""
        store = TortoiseGitLabelStore()
        out_rows = [{"id": uuid.uuid4(), "git_hosting": "github"}]
        qs = make_qs_chain(result_for_values=out_rows)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        ids = [uuid.uuid4(), uuid.uuid4()]
        out = await store.find_git_hostings_by_ids(ids)
        assert out == out_rows

        model.filter.assert_called_once_with(id__in=ids)
        qs.values.assert_awaited_once_with("id", "git_hosting")


class TestTortoiseFindByTokenIdAndUser:
    @pytest.mark.asyncio
    async def test_blank_inputs_return_none(self, monkeypatch):
        """Blank token_id or user_id → None, no DB calls."""
        store = TortoiseGitLabelStore()
        model = MagicMock()
        monkeypatch.setattr(store, "model", model)
        assert await store.find_by_token_id_and_user("", "u") is None
        assert await store.find_by_token_id_and_user("tok", "") is None
        model.filter.assert_not_called()

    @pytest.mark.asyncio
    async def test_happy_path_filters_then_first_then_maps(self, monkeypatch):
        """Filter(id=..., user_id=...), first() → DTO."""
        store = TortoiseGitLabelStore()
        row = make_gitlabel(user_id="u1")
        qs = make_qs_chain(result_for_first=row)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        dto = await store.find_by_token_id_and_user("abc", "u1")
        assert isinstance(dto, GitLabelResponseDTO)
        model.filter.assert_called_once_with(id="abc", user_id="u1")
        qs.first.assert_awaited_once()


class TestTortoiseFindAllByUserId:
    @pytest.mark.asyncio
    async def test_blank_user_raises(self):
        """Blank user_id → repo raises its internal error."""
        store = TortoiseGitLabelStore()
        with pytest.raises(Exception):
            await store.find_all_by_user_id(0, 10, "")

    @pytest.mark.asyncio
    async def test_orders_desc_pages_and_maps(self, monkeypatch):
        """Builds query, optional git_hosting filter, order desc, paginate, map."""
        store = TortoiseGitLabelStore()
        rows = [make_gitlabel(user_id="u", label="b"), make_gitlabel(user_id="u", label="a")]
        qs = make_qs_chain(result_for_all=rows)
        model = MagicMock()
        model.filter.return_value = qs  # initial .filter(user_id=...)
        monkeypatch.setattr(store, "model", model)

        out = await store.find_all_by_user_id(offset=2, limit=5, user_id="u")
        assert all(isinstance(x, GitLabelResponseDTO) for x in out)

        model.filter.assert_called_once_with(user_id="u")
        qs.order_by.assert_called_once_with("-created_at")
        qs.offset.assert_called_once_with(2 * 5)
        qs.limit.assert_called_once_with(5)
        qs.all.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_with_git_hosting_adds_filter(self, monkeypatch):
        """If git_hosting is provided, the query adds filter(git_hosting=...)."""
        store = TortoiseGitLabelStore()
        rows = [make_gitlabel(user_id="u", git_hosting="github")]
        qs = make_qs_chain(result_for_all=rows)
        # We want to see a second .filter on the qs
        qs.filter = MagicMock(return_value=qs)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        await store.find_all_by_user_id(offset=0, limit=10, user_id="u", git_hosting="github")

        model.filter.assert_called_once_with(user_id="u")
        qs.filter.assert_called_once_with(git_hosting="github")


class TestTortoiseCountByUserId:
    @pytest.mark.asyncio
    async def test_blank_user_raises(self):
        """Blank user_id → repo raises its internal error."""
        store = TortoiseGitLabelStore()
        with pytest.raises(Exception):
            await store.count_by_user_id("")

    @pytest.mark.asyncio
    async def test_counts_after_optional_hosting_filter(self, monkeypatch):
        """Normal path: filter by user, optional hosting, then count()."""
        store = TortoiseGitLabelStore()
        qs = make_qs_chain(count_value=7)
        qs.filter = MagicMock(return_value=qs)  # allow a second filter when hosting provided
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        n1 = await store.count_by_user_id("u1")
        assert n1 == 7
        model.filter.assert_called_with(user_id="u1")
        qs.count.assert_awaited()

        n2 = await store.count_by_user_id("u1", git_hosting="github")
        assert n2 == 7
        qs.filter.assert_called_with(git_hosting="github")


class TestTortoiseFindAllByUserIdAndLabel:
    @pytest.mark.asyncio
    async def test_blank_user_raises(self):
        """Blank user_id → internal error."""
        store = TortoiseGitLabelStore()
        with pytest.raises(Exception):
            await store.find_all_by_user_id_and_label(0, 10, "", "abc")

    @pytest.mark.asyncio
    async def test_blank_label_raises(self):
        """Blank label → internal error."""
        store = TortoiseGitLabelStore()
        with pytest.raises(Exception):
            await store.find_all_by_user_id_and_label(0, 10, "u", "  ")

    @pytest.mark.asyncio
    async def test_filters_by_user_and_label_icontains_then_pages_and_maps(self, monkeypatch):
        """Filter(user_id=..., label__icontains=...), order desc, paginate, map."""
        store = TortoiseGitLabelStore()
        rows = [make_gitlabel(user_id="u", label="abc"), make_gitlabel(user_id="u", label="abcd")]
        qs = make_qs_chain(result_for_all=rows)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        out = await store.find_all_by_user_id_and_label(1, 2, "u", "ab")
        assert all(isinstance(x, GitLabelResponseDTO) for x in out)

        model.filter.assert_called_once_with(user_id="u", label__icontains="ab")
        qs.order_by.assert_called_once_with("-created_at")
        qs.offset.assert_called_once_with(1 * 2)
        qs.limit.assert_called_once_with(2)
        qs.all.assert_awaited_once()


class TestTortoiseCountByUserIdAndLabel:
    @pytest.mark.asyncio
    async def test_blank_user_raises(self):
        """Blank user_id → internal error."""
        store = TortoiseGitLabelStore()
        with pytest.raises(Exception):
            await store.count_by_user_id_and_label("", "x")

    @pytest.mark.asyncio
    async def test_blank_label_raises(self):
        """Blank label → internal error."""
        store = TortoiseGitLabelStore()
        with pytest.raises(Exception):
            await store.count_by_user_id_and_label("u", "")

    @pytest.mark.asyncio
    async def test_counts_after_label_icontains_filter(self, monkeypatch):
        """Filter(user_id=..., label__icontains=...), then count()."""
        store = TortoiseGitLabelStore()
        qs = make_qs_chain(count_value=4)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        n = await store.count_by_user_id_and_label("u", "lab")
        assert n == 4
        model.filter.assert_called_once_with(user_id="u", label__icontains="lab")
        qs.count.assert_awaited_once()


class TestTortoiseSave:
    @pytest.mark.asyncio
    async def test_success_maps_instance(self, no_tortoise_model_io, forbid_tortoise_db, monkeypatch):
        """Create returns a real model instance; repo maps to DTO."""
        store = TortoiseGitLabelStore()
        model = MagicMock()
        model.create = AsyncMock(return_value=make_gitlabel(user_id="u", label="L"))
        monkeypatch.setattr(store, "model", model)

        req = GitLabelRequestDTO(
            user_id="u", label="L", git_hosting="github", username="alice",
            token_value="tok", masked_token="*ok",
        )
        dto = await store.save(req)
        assert isinstance(dto, GitLabelResponseDTO)
        model.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_integrity_error_is_translated(self, monkeypatch):
        """Unique constraint violation → internal error is raised."""
        store = TortoiseGitLabelStore()
        model = MagicMock()
        model.create = AsyncMock(side_effect=IntegrityError("duplicate"))
        monkeypatch.setattr(store, "model", model)

        req = GitLabelRequestDTO(
            user_id="u", label="L", git_hosting="github", username="alice",
            token_value="tok", masked_token="*ok",
        )
        with pytest.raises(Exception):
            await store.save(req)


class TestTortoiseDeleteByIdAndUserId:
    @pytest.mark.asyncio
    async def test_blank_inputs_return_minus1(self, monkeypatch):
        """Blank id or blank user → -1 and no DB calls."""
        store = TortoiseGitLabelStore()
        model = MagicMock()
        monkeypatch.setattr(store, "model", model)

        assert await store.delete_by_id_and_user_id(None, "u") == -1  # type: ignore[arg-type]
        assert await store.delete_by_id_and_user_id(uuid.uuid4(), "") == -1
        model.filter.assert_not_called()

    @pytest.mark.asyncio
    async def test_filter_then_delete_returns_count(self, monkeypatch):
        """Filter(id=..., user_id=...), then delete(), returning rows affected."""
        store = TortoiseGitLabelStore()
        qs = make_qs_chain(delete_value=2)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        n = await store.delete_by_id_and_user_id(uuid.uuid4(), "u")
        assert n == 2
        model.filter.assert_called_once()
        qs.delete.assert_awaited_once()


class TestTortoiseFindByIdAndUserIdAndGitHosting:
    @pytest.mark.asyncio
    async def test_filters_on_class_and_maps(self, monkeypatch):
        """
        This method uses the GitLabel class directly (not store.model),
        so we patch the class-reference inside the repo module.
        """
        store = TortoiseGitLabelStore()

        row = make_gitlabel(user_id="u", git_hosting="github")
        qs = make_qs_chain(result_for_first=row)

        # Replace the GitLabel symbol used inside the repo module
        fake_class = MagicMock()
        fake_class.filter.return_value = qs
        monkeypatch.setattr(repo_mod, "GitLabel", fake_class)

        dto = await store.find_by_id_and_user_id_and_git_hosting("id1", "u", "github")
        assert isinstance(dto, GitLabelResponseDTO)

        fake_class.filter.assert_called_once_with(id="id1", user_id="u", git_hosting="github")
        qs.first.assert_awaited_once()

class TestBeanieGitLabelStoreValidations:
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "token_ids",
        [
            ([]),
            (None)
        ],
        ids=["Empty token_ids", "None token_ids"]
    )
    async def test_find_git_hostings_by_ids_validation(self, token_ids):
        
        store = repo_mod.BeanieGitLabelStore()
        
        res = await store.find_git_hostings_by_ids(token_ids=token_ids)
        
        assert isinstance(res, list)
        assert len(res) == 0
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("token_id", "user_id"),
        [
            ("", "valid_user_id"),
            (" ", "valid_user_id"),
            (None, "valid_user_id"),
            ("invalid token_id", "valid_user_id"),
            (str(uuid.uuid4()), ""),
            (str(uuid.uuid4()), " "),
            (str(uuid.uuid4()), None)
        ],
        ids=["Empty token_id", "Blank token_id",  "None token_id", "invalid uuid token_id", "Empty user_id", "Blank user_id",  "None user_id"]
    )
    async def test_find_by_token_id_and_user_validation(self, token_id: str, user_id: str):
        
        store = repo_mod.BeanieGitLabelStore()
        
        res = await store.find_by_token_id_and_user(token_id=token_id, user_id=user_id)
        
        assert not res
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("id", "user_id", "git_hosting"),
        [
            ("", "valid_user_id", "valid_git_hosting"),
            (" ", "valid_user_id", "valid_git_hosting"),
            (None, "valid_user_id", "valid_git_hosting"),
            ("invalid_uuid", "valid_user_id", "valid_git_hosting"),
            (str(uuid.uuid4()), "", "valid_git_hosting"),
            (str(uuid.uuid4()), " ", "valid_git_hosting"),
            (str(uuid.uuid4()), None, "valid_git_hosting"),
            (str(uuid.uuid4()), "valid_user_id", ""),
            (str(uuid.uuid4()), "valid_user_id", " "),
            (str(uuid.uuid4()), "valid_user_id", None),
        ],
        ids=[
            "Empty id", "Blank id",  "None id",
            "Invalid UUID id",
            "Empty user_id", "Blank user_id",  "None user_id",
            "Empty git_hosting", "Blank git_hosting",  "None git_hosting",
            ]
    )
    async def test_find_by_id_and_user_id_and_git_hosting_validation(self, id: str, user_id: str, git_hosting: str):
        
        store = repo_mod.BeanieGitLabelStore()
        
        res = await store.find_by_id_and_user_id_and_git_hosting(id=id, user_id=user_id, git_hosting=git_hosting)
        
        assert not res
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "user_id",
        [
            "",
            " ",
            None,
        ],
        ids=[
            "Empty user_id", "Blank user_id",  "None user_id",
        ]
    )
    async def test_find_all_by_user_id_validation(self, user_id: str):
        
        store = repo_mod.BeanieGitLabelStore()
        
        with pytest.raises(DevDoxModelsException) as p:
            await store.find_all_by_user_id(offset=0, limit=10, user_id=user_id)
        
        err = GitLabelErrors.MISSING_USER_ID.value
        
        assert p.value.log_message == err["log_message"]
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "user_id",
        [
            "",
            " ",
            None,
        ],
        ids=[
            "Empty user_id", "Blank user_id",  "None user_id",
        ]
    )
    async def test_count_by_user_id_validation(self, user_id: str):
        
        store = repo_mod.BeanieGitLabelStore()
        
        with pytest.raises(DevDoxModelsException) as p:
            await store.count_by_user_id(user_id=user_id)
        
        err = GitLabelErrors.MISSING_USER_ID.value
        
        assert p.value.log_message == err["log_message"]
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("user_id", "label", "expected_err"),
        [
            ("", "valid label", GitLabelErrors.MISSING_USER_ID),
            (" ", "valid label", GitLabelErrors.MISSING_USER_ID),
            (None, "valid label", GitLabelErrors.MISSING_USER_ID),
            ("valid user_id", "", GitLabelErrors.MISSING_LABEL),
            ("valid user_id", " ", GitLabelErrors.MISSING_LABEL),
            ("valid user_id", None, GitLabelErrors.MISSING_LABEL),
        ],
        ids=[
            "Empty user_id", "Blank user_id",  "None user_id",
            "Empty label", "Blank label",  "None label",
        ]
    )
    async def test_count_by_user_id_and_label_validation(self, user_id: str, label:str, expected_err: GitLabelErrors):
        
        store = repo_mod.BeanieGitLabelStore()
        
        with pytest.raises(DevDoxModelsException) as p:
            await store.count_by_user_id_and_label(user_id=user_id, label=label)
        
        err = expected_err.value
        
        assert p.value.log_message == err["log_message"]
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("user_id", "label", "expected_err"),
        [
            ("", "valid label", GitLabelErrors.MISSING_USER_ID),
            (" ", "valid label", GitLabelErrors.MISSING_USER_ID),
            (None, "valid label", GitLabelErrors.MISSING_USER_ID),
            ("valid user_id", "", GitLabelErrors.MISSING_LABEL),
            ("valid user_id", " ", GitLabelErrors.MISSING_LABEL),
            ("valid user_id", None, GitLabelErrors.MISSING_LABEL),
        ],
        ids=[
            "Empty user_id", "Blank user_id",  "None user_id",
            "Empty label", "Blank label",  "None label",
        ]
    )
    async def test_find_all_by_user_id_and_label_validation(self, user_id: str, label:str, expected_err: GitLabelErrors):
        
        store = repo_mod.BeanieGitLabelStore()
        
        with pytest.raises(DevDoxModelsException) as p:
            await store.find_all_by_user_id_and_label(user_id=user_id, label=label, offset=0, limit=10)
        
        err = expected_err.value
        
        assert p.value.log_message == err["log_message"]
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("label_id", "user_id"),
        [
            (uuid.uuid4(), ""),
            (uuid.uuid4(), " "),
            (uuid.uuid4(), None),
            ("", "valid user_id"),
            (" ", "valid user_id"),
            (None, "valid user_id"),
            ("invalid uuid", "valid user_id"),
        ],
        ids=["Empty user_id", "Blank user_id",  "None user_id",
            "Empty label_id", "Blank label_id",  "None label_id", "Invalid uuid label_id"]
    )
    async def test_delete_by_id_and_user_id_validation(self, label_id: uuid.UUID, user_id: str):
        
        store = repo_mod.BeanieGitLabelStore()
        
        res = await store.delete_by_id_and_user_id(label_id=label_id, user_id=user_id)
        
        assert res == -1