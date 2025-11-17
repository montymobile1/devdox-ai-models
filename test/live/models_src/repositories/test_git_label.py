# tests/test_beanie_git_label_backend.py

import datetime
import uuid
from typing import List

import pytest

from models_src.dto.git_label import GitLabelResponseDTO
from models_src.dto.repo import GitHosting
from models_src.repositories.git_label import BeanieGitLabelBackend
from test.conftest import _make_git_label_request


@pytest.mark.asyncio
class TestBeanieGitLabelBackend:
    beanie_store = BeanieGitLabelBackend

    async def test_save_and_find_by_token_id_and_user(self, db_client):
        store = self.beanie_store()

        # Arrange
        req = _make_git_label_request(
            user_id="beanie-user-1",
            label="prod-github",
            git_hosting=GitHosting.GITHUB,
            username="octocat",
            token_value="token-1",
            masked_token="****1",
        )

        # Act
        saved = await store.save(req)

        # Assert saved DTO
        assert isinstance(saved, GitLabelResponseDTO)
        assert isinstance(saved.id, uuid.UUID)
        assert saved.user_id == req.user_id
        assert saved.label == req.label
        assert saved.git_hosting == req.git_hosting.value if hasattr(req.git_hosting, "value") else req.git_hosting
        assert saved.username == req.username
        assert saved.masked_token == req.masked_token
        assert isinstance(saved.created_at, datetime.datetime)

        # And we can fetch it by token_id + user_id
        fetched = await store.find_by_token_id_and_user(
            token_id=str(saved.id),
            user_id=req.user_id,
        )
        assert fetched is not None
        assert fetched.id == saved.id

    async def test_find_by_id_and_user_id_and_git_hosting(self, db_client):
        store = self.beanie_store()
        user_id = "beanie-user-2"

        saved = await store.save(
            _make_git_label_request(
                user_id=user_id,
                label="staging-github",
                git_hosting=GitHosting.GITHUB,
                username="staging-user",
                token_value="token-2",
                masked_token="****2",
            )
        )

        # Correct combo
        found = await store.find_by_id_and_user_id_and_git_hosting(
            id=str(saved.id),
            user_id=user_id,
            git_hosting=saved.git_hosting,
        )
        assert found is not None
        assert found.id == saved.id

        # Wrong git_hosting → None
        found_wrong_host = await store.find_by_id_and_user_id_and_git_hosting(
            id=str(saved.id),
            user_id=user_id,
            git_hosting="gitlab",
        )
        assert found_wrong_host is None

        # Wrong user_id → None
        found_wrong_user = await store.find_by_id_and_user_id_and_git_hosting(
            id=str(saved.id),
            user_id="other-user",
            git_hosting=saved.git_hosting,
        )
        assert found_wrong_user is None

    async def test_find_git_hostings_by_ids_mixed_valid_invalid(self, db_client):
        store = self.beanie_store()

        saved1 = await store.save(
            _make_git_label_request(
                user_id="user-a",
                label="label-a",
                git_hosting=GitHosting.GITHUB,
                username="user-a",
                token_value="token-a",
                masked_token="****a",
            )
        )
        saved2 = await store.save(
            _make_git_label_request(
                user_id="user-b",
                label="label-b",
                git_hosting=GitHosting.GITLAB,
                username="user-b",
                token_value="token-b",
                masked_token="****b",
            )
        )

        token_ids = [
            str(saved1.id),
            saved2.id,
            "not-a-uuid",
        ]

        results = await store.find_git_hostings_by_ids(token_ids=token_ids)

        assert len(results) == 2
        ids = {r["id"] for r in results}
        hosts = {r["git_hosting"] for r in results}
        assert ids == {saved1.id, saved2.id}
        assert "github" in hosts or GitHosting.GITHUB.value in hosts
        assert "gitlab" in hosts or GitHosting.GITLAB.value in hosts

    async def test_find_all_by_user_id_and_count_pagination_and_host_filter(self, db_client):
        store = self.beanie_store()
        user_id = "user-pagination"

        saved_gh_1 = await store.save(
            _make_git_label_request(
                user_id=user_id,
                label="prod-github-1",
                git_hosting=GitHosting.GITHUB,
                username="user1",
                token_value="t1",
                masked_token="****t1",
            )
        )
        saved_gh_2 = await store.save(
            _make_git_label_request(
                user_id=user_id,
                label="prod-github-2",
                git_hosting=GitHosting.GITHUB,
                username="user2",
                token_value="t2",
                masked_token="****t2",
            )
        )
        saved_gl_1 = await store.save(
            _make_git_label_request(
                user_id=user_id,
                label="prod-gitlab-1",
                git_hosting=GitHosting.GITLAB,
                username="user3",
                token_value="t3",
                masked_token="****t3",
            )
        )
        # Other user
        await store.save(
            _make_git_label_request(
                user_id="other-user",
                label="other",
                git_hosting=GitHosting.GITHUB,
                username="other",
                token_value="tX",
                masked_token="****x",
            )
        )

        # Count all for user
        total = await store.count_by_user_id(user_id=user_id)
        assert total == 3

        # Count only GitHub for user
        total_gh = await store.count_by_user_id(
            user_id=user_id,
            git_hosting="github",
        )
        assert total_gh == 2

        # Pagination: offset=0, limit=2 -> newest 2
        page0 = await store.find_all_by_user_id(
            offset=0,
            limit=2,
            user_id=user_id,
        )
        assert len(page0) == 2

        # Pagination: offset=1, limit=2 -> remaining 1
        page1 = await store.find_all_by_user_id(
            offset=1,
            limit=2,
            user_id=user_id,
        )
        assert len(page1) == 1

        ids = {lbl.id for lbl in page0 + page1}
        assert ids == {saved_gh_1.id, saved_gh_2.id, saved_gl_1.id}

    async def test_find_all_and_count_by_user_id_and_label_case_insensitive_contains(self, db_client):
        store = self.beanie_store()
        user_id = "user-label-search"

        await store.save(
            _make_git_label_request(
                user_id=user_id,
                label="prod-github",
                git_hosting=GitHosting.GITHUB,
                username="u1",
                token_value="t1",
                masked_token="****1",
            )
        )
        await store.save(
            _make_git_label_request(
                user_id=user_id,
                label="Prod-Gitlab",
                git_hosting=GitHosting.GITLAB,
                username="u2",
                token_value="t2",
                masked_token="****2",
            )
        )
        await store.save(
            _make_git_label_request(
                user_id=user_id,
                label="dev-github",
                git_hosting=GitHosting.GITHUB,
                username="u3",
                token_value="t3",
                masked_token="****3",
            )
        )

        # label search = "prod" (case-insensitive substring)
        count = await store.count_by_user_id_and_label(
            user_id=user_id,
            label="prod",
        )
        assert count == 2

        labels = await store.find_all_by_user_id_and_label(
            offset=0,
            limit=10,
            user_id=user_id,
            label="prod",
        )
        assert len(labels) == 2
        label_names = {l.label for l in labels}
        assert "prod-github" in label_names
        assert "Prod-Gitlab" in label_names

    async def test_delete_by_id_and_user_id(self, db_client):
        store = self.beanie_store()
        user_id = "user-delete"

        saved1 = await store.save(
            _make_git_label_request(
                user_id=user_id,
                label="delete-me-1",
                git_hosting=GitHosting.GITHUB,
                username="u",
                token_value="t1",
                masked_token="****1",
            )
        )
        saved2 = await store.save(
            _make_git_label_request(
                user_id=user_id,
                label="keep-me",
                git_hosting=GitHosting.GITHUB,
                username="u",
                token_value="t2",
                masked_token="****2",
            )
        )

        # First delete
        deleted_count = await store.delete_by_id_and_user_id(
            label_id=saved1.id,
            user_id=user_id,
        )
        assert deleted_count == 1

        remaining = await store.count_by_user_id(user_id=user_id)
        assert remaining == 1

        # Deleting again should return 0
        deleted_again = await store.delete_by_id_and_user_id(
            label_id=saved1.id,
            user_id=user_id,
        )
        assert deleted_again == 0
