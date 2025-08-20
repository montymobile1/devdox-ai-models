import pytest

from models_src.dto.git_label import GitLabelRequestDTO, GitLabelResponseDTO
from models_src.dto.repo import GitHosting
from models_src.test_doubles.repositories.git_label import (
    FakeGitLabelStore,
    make_fake_git_label,
)

@pytest.mark.asyncio
class TestFakeGitLabelStore:
    async def test_save_adds_to_store(self):
        store = FakeGitLabelStore()
        request = GitLabelRequestDTO(
            user_id="u1",
            label="main",
            git_hosting=GitHosting.GITHUB.value,
            username="alice",
            token_value="t1",
            masked_token="****t1",
        )

        result = await store.save(request)

        assert result.user_id == request.user_id
        assert store.total_count == 1
        assert len(store._FakeGitLabelStore__get_data_store("u1")) == 1

    async def test_find_by_token_id_and_user_matches(self):
        store = FakeGitLabelStore()
        label = make_fake_git_label(user_id="u1")
        store.set_fake_data([label])

        found = await store.find_by_token_id_and_user(str(label.id), "u1")

        assert found == label

    async def test_find_by_token_id_and_user_none(self):
        store = FakeGitLabelStore()
        found = await store.find_by_token_id_and_user("not-there", "u1")
        assert found is None

    async def test_find_git_hostings_by_ids_returns_matching(self):
        store = FakeGitLabelStore()
        label1 = make_fake_git_label(user_id="u1")
        label2 = make_fake_git_label(user_id="u1")
        store.set_fake_data([label1, label2])

        results = await store.find_git_hostings_by_ids([str(label1.id), str(label2.id)])

        assert len(results) == 2
        assert {r["id"] for r in results} == {label1.id, label2.id}

    async def test_find_all_by_user_id_respects_limit(self):
        store = FakeGitLabelStore()
        labels = [make_fake_git_label(user_id="u1") for _ in range(10)]
        store.set_fake_data(labels)

        results = await store.find_all_by_user_id(0, 5, "u1")

        assert len(results) == 5

    async def test_find_all_by_user_id_and_label_filters(self):
        store = FakeGitLabelStore()
        match = make_fake_git_label(user_id="u1", label="target")
        other = make_fake_git_label(user_id="u1", label="other")
        store.set_fake_data([match, other])

        results = await store.find_all_by_user_id_and_label(0, 10, "u1", "target")

        assert results == [match]

    async def test_count_by_user_id_filters_git_hosting(self):
        store = FakeGitLabelStore()
        match = make_fake_git_label(user_id="u1", git_hosting="github")
        other = make_fake_git_label(user_id="u1", git_hosting="gitlab")
        store.set_fake_data([match, other])

        count = await store.count_by_user_id("u1", git_hosting="github")

        assert count == 1

    async def test_delete_by_id_and_user_id_removes_correct(self):
        store = FakeGitLabelStore()
        label = make_fake_git_label(user_id="u1")
        store.set_fake_data([label])

        result = await store.delete_by_id_and_user_id(label.id, "u1")

        assert result == 1
        assert store.total_count == 0

    async def test_find_by_id_and_user_id_and_git_hosting_matches(self):
        store = FakeGitLabelStore()
        label = make_fake_git_label(user_id="u1", git_hosting="github")
        store.set_fake_data([label])

        result = await store.find_by_id_and_user_id_and_git_hosting(
            str(label.id), "u1", "github"
        )

        assert result == label
