import uuid
import pytest
import pytest_asyncio

from models_src.dto.git_label import GitLabelRequestDTO, GitLabelResponseDTO
from models_src.dto.repo import GitHosting
from models_src.repositories.git_label import BeanieGitLabelBackend, ILabelStore, InMemoryGitLabelBackend, \
    TortoiseGitLabelBackend
from test.conftest import _make_git_label_request

class TestGitLabelBackend:
    __test__ = False
    
    @pytest_asyncio.fixture
    async def repo(self) -> ILabelStore:
        """
		Concrete subclasses must override this to return
		the appropriate repo instance (Mongo or Postgres).
		"""
        raise NotImplementedError
    
    def _build_request(
        self,
        *,
        user_id: str = "user-1",
        label: str = "default-label",
        git_hosting: GitHosting = GitHosting.GITHUB,
        username_suffix: str = "1",
    ) -> GitLabelRequestDTO:
        """
        Start from the generic factory and then override fields we care about,
        so we don't depend on the exact signature of _make_git_label_request().
        """
        req: GitLabelRequestDTO = _make_git_label_request()

        req.user_id = user_id
        req.label = label
        req.git_hosting = git_hosting
        req.username = f"{user_id}-user-{username_suffix}"
        req.token_value = f"token-{username_suffix}"
        req.masked_token = f"****-{username_suffix}"

        return req

    async def _create_label(
        self,
        repo: ILabelStore,
        *,
        user_id: str = "user-1",
        label: str = "default-label",
        git_hosting: GitHosting = GitHosting.GITHUB,
        username_suffix: str = "1",
    ) -> GitLabelResponseDTO:
        req = self._build_request(
            user_id=user_id,
            label=label,
            git_hosting=git_hosting,
            username_suffix=username_suffix,
        )
        return await repo.save(req)
    
    async def test_save_sets_id_and_timestamps(self, repo: ILabelStore):
        req = self._build_request(user_id="u1", label="L1")
        saved = await repo.save(req)
        
        assert isinstance(saved.id, uuid.UUID)
        assert saved.user_id == "u1"
        assert saved.label == "L1"
        assert saved.created_at is not None
        assert saved.updated_at is not None
    
    async def test_find_by_token_id_and_user_returns_matching_row(self, repo: ILabelStore):
        req = self._build_request(user_id="u2", label="L2")
        saved = await repo.save(req)
        
        fetched = await repo.find_by_token_id_and_user(
            token_id=str(saved.id),
            user_id="u2",
        )
        
        assert fetched is not None
        assert fetched.id == saved.id
        assert fetched.user_id == "u2"
    
    async def test_find_all_by_user_id_respects_paging_and_created_at_desc(
            self, repo: ILabelStore
    ):
        user_id = "u-paging"
        created = []
        for i in range(5):
            created.append(
                await repo.save(
                    self._build_request(user_id=user_id, label=f"L-{i}", username_suffix=str(i))
                )
            )
        
        expected = sorted(created, key=lambda r: r.created_at, reverse=True)
        
        page0 = await repo.find_all_by_user_id(offset=0, limit=2, user_id=user_id)
        page1 = await repo.find_all_by_user_id(offset=1, limit=2, user_id=user_id)
        
        assert [r.id for r in page0] == [r.id for r in expected[:2]]
        assert [r.id for r in page1] == [r.id for r in expected[2:4]]
    
    async def test_count_by_user_id_counts_rows_for_user(self, repo: ILabelStore):
        user_id = "u-count"
        
        # setup via save
        for i in range(3):
            await repo.save(
                self._build_request(user_id=user_id, label=f"L-{i}", username_suffix=str(i))
            )
        
        count = await repo.count_by_user_id(user_id=user_id)
        assert count == 3
    
    async def test_find_all_by_user_id_and_label_case_insensitive_contains(
            self, repo: ILabelStore
    ):
        user_id = "u-label-find"
        await repo.save(self._build_request(user_id=user_id, label="Personal GitHub Token", username_suffix="1"))
        await repo.save(self._build_request(user_id=user_id, label="Work github token", username_suffix="2"))
        await repo.save(self._build_request(user_id=user_id, label="Some other label", username_suffix="3"))
        
        results = await repo.find_all_by_user_id_and_label(
            offset=0, limit=10, user_id=user_id, label="github token"
        )
        
        labels = {r.label for r in results}
        assert labels == {"Personal GitHub Token", "Work github token"}
    
    async def test_count_by_user_id_and_label_case_insensitive_contains(
            self, repo: ILabelStore
    ):
        user_id = "u-label-count"
        await repo.save(self._build_request(user_id=user_id, label="Personal GitHub Token", username_suffix="1"))
        await repo.save(self._build_request(user_id=user_id, label="Work github token", username_suffix="2"))
        await repo.save(self._build_request(user_id=user_id, label="Some other label", username_suffix="3"))
        
        count = await repo.count_by_user_id_and_label(
            user_id=user_id, label="GITHUB TOKEN"
        )
        assert count == 2
    
    async def test_delete_by_id_and_user_id_returns_1_when_deleted(self, repo: ILabelStore):
        saved = await repo.save(self._build_request(user_id="u-del1", label="Delete me", username_suffix="1"))
        deleted = await repo.delete_by_id_and_user_id(label_id=saved.id, user_id="u-del1")
        assert deleted == 1
    
    async def test_delete_by_id_and_user_id_returns_0_when_no_match(self, repo: ILabelStore):
        # never saved
        random_id = uuid.uuid4()
        deleted = await repo.delete_by_id_and_user_id(label_id=random_id, user_id="u-del2")
        assert deleted == 0
    
    
@pytest.mark.asyncio
class TestTortoiseGitLabelBackend(TestGitLabelBackend):
    __test__ = True
    
    @pytest_asyncio.fixture
    async def repo(self, postgresql_client):
        return TortoiseGitLabelBackend()

@pytest.mark.asyncio
class TestBeanieGitLabelBackend(TestGitLabelBackend):
    __test__ = True
    
    @pytest_asyncio.fixture
    async def repo(self, db_client):
        return BeanieGitLabelBackend()

@pytest.mark.asyncio
class TestInMemoryGitLabelBackend(TestGitLabelBackend):
    __test__ = True
    
    @pytest_asyncio.fixture
    async def repo(self):
        return InMemoryGitLabelBackend()