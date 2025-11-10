import datetime
import uuid
from typing import List

import pytest

from models_src.models.code_chunks_document import CodeChunks, EMBED_DIM
from models_src.dto.code_chunks import CodeChunksRequestDTO
from models_src.repositories.code_chunks import BeanieCodeChunksStore


###############################################################################
# Fixtures & helpers
###############################################################################

def _embed(n: int = EMBED_DIM) -> List[float]:
    return [0.0] * n


def mk_req(
    *,
    user_id: str = "u1",
    repo_id: str = "r1",
    content: str = "hello",
    file_name: str = "README.md",
    file_path: str = "/README.md",
    file_size: int = 10,
    commit_number: str = "c1",
    embedding: List[float] | None = None,
) -> CodeChunksRequestDTO:
    return CodeChunksRequestDTO(
        user_id=user_id,
        repo_id=repo_id,
        content=content,
        file_name=file_name,
        file_path=file_path,
        file_size=file_size,
        commit_number=commit_number,
        embedding=embedding,
    )


def mk_doc(
    *,
    user_id: str = "u1",
    repo_id: str = "r1",
    content: str = "hello",
    file_name: str = "README.md",
    file_path: str = "/README.md",
    file_size: int = 10,
    commit_number: str = "c1",
    embedding: List[float] | None = None,
    created_at: datetime.datetime | None = None,
    updated_at: datetime.datetime | None = None,
) -> CodeChunks:
    now = datetime.datetime.now(datetime.timezone.utc)
    return CodeChunks(
        id=uuid.uuid4(),
        user_id=user_id,
        repo_id=repo_id,
        content=content,
        file_name=file_name,
        file_path=file_path,
        file_size=file_size,
        commit_number=commit_number,
        embedding=embedding,
        created_at=created_at or now,
        updated_at=updated_at or now,
    )


@pytest.fixture
def repo() -> BeanieCodeChunksStore:
    return BeanieCodeChunksStore()

###############################################################################
# save
###############################################################################

@pytest.mark.asyncio
async def test_save_persists_and_returns_dto(repo, db_client):
    dto = await repo.save(mk_req(embedding=_embed()))
    assert dto is not None
    assert dto.user_id == "u1"
    assert dto.repo_id == "r1"
    assert dto.file_name == "README.md"
    assert dto.created_at is not None

    # sanity: exists in DB
    found = await CodeChunks.find(CodeChunks.id == dto.id).first_or_none()
    assert found is not None
    assert found.content == "hello"


@pytest.mark.asyncio
async def test_save_rejects_wrong_embedding_length(repo, db_client):
    with pytest.raises(Exception):
        await repo.save(mk_req(embedding=_embed(5)))  # wrong length


@pytest.mark.asyncio
async def test_save_allows_missing_embedding(repo, db_client):
    dto = await repo.save(mk_req(embedding=None))
    assert dto.embedding is None

###############################################################################
# bulk_save
###############################################################################

@pytest.mark.asyncio
async def test_bulk_save_persists_multiple_and_returns_dtos(repo, db_client):
    payload = [
        mk_req(repo_id="rB", file_name=f"f{i}.txt", embedding=_embed())
        for i in range(3)
    ]
    out = await repo.bulk_save(payload)
    assert len(out) == 3
    # stored?
    count = await CodeChunks.find(CodeChunks.repo_id == "rB").count()
    assert count == 3


@pytest.mark.asyncio
async def test_bulk_save_empty_list_returns_empty(repo, db_client):
    out = await repo.bulk_save([])
    assert out == []


@pytest.mark.asyncio
async def test_bulk_save_rejects_invalid_one_of_many(repo, db_client):
    # one invalid (bad embedding) among valids should raise
    bad = mk_req(repo_id="rC", file_name="bad.txt", embedding=_embed(2))
    good1 = mk_req(repo_id="rC", file_name="ok1.txt", embedding=_embed())
    good2 = mk_req(repo_id="rC", file_name="ok2.txt", embedding=_embed())
    with pytest.raises(Exception):
        await repo.bulk_save([good1, bad, good2])

###############################################################################
# find_all_by_repo_id_with_limit
###############################################################################

@pytest.mark.asyncio
async def test_find_all_by_repo_id_with_limit_sorts_newest_first_and_limits(repo, db_client):
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    docs = [
        mk_doc(repo_id="r2", created_at=now + datetime.timedelta(seconds=i), updated_at=now + datetime.timedelta(seconds=i))
        for i in range(5)
    ]
    await CodeChunks.insert_many(docs)

    items = await repo.find_all_by_repo_id_with_limit("r2", limit=3)
    assert len(items) == 3
    # newest first
    created = [it.created_at for it in items]
    assert created == sorted(created, reverse=True)


@pytest.mark.asyncio
async def test_find_all_by_repo_id_with_limit_returns_empty_when_no_match(repo, db_client):
    out = await repo.find_all_by_repo_id_with_limit("does-not-exist", limit=5)
    assert out == []


@pytest.mark.asyncio
async def test_find_all_by_repo_id_with_limit_handles_bad_limit(repo, db_client):
    out = await repo.find_all_by_repo_id_with_limit("rX", limit=0)
    assert out == []

###############################################################################
# get_repo_file_chunks
###############################################################################

@pytest.mark.asyncio
async def test_get_repo_file_chunks_filters_by_user_repo_and_filename_icontains_and_returns_content_desc(repo, db_client):
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)

    # matching user/repo, mixed-case names, different timestamps
    d1 = mk_doc(user_id="U1", repo_id="R1", file_name="Readme.md", content="A",
                created_at=now + datetime.timedelta(seconds=1))
    d2 = mk_doc(user_id="U1", repo_id="R1", file_name="README.txt", content="B",
                created_at=now + datetime.timedelta(seconds=2))
    # different user/repo: should be ignored
    d3 = mk_doc(user_id="U2", repo_id="R1", file_name="readme.md", content="X")
    d4 = mk_doc(user_id="U1", repo_id="R2", file_name="readme.md", content="Y")

    await CodeChunks.insert_many([d1, d2, d3, d4])

    rows = await repo.get_repo_file_chunks(user_id="U1", repo_id="R1", file_name="readme")
    assert [r["content"] for r in rows] == ["B", "A"]  # newest first
    # Only content keys present
    assert set(rows[0].keys()) == {"content"}


@pytest.mark.asyncio
async def test_get_repo_file_chunks_returns_empty_for_missing_inputs(repo, db_client):
    assert await repo.get_repo_file_chunks(user_id="", repo_id="R1", file_name="x") == []
    assert await repo.get_repo_file_chunks(user_id="U1", repo_id="", file_name="x") == []
    assert await repo.get_repo_file_chunks(user_id="U1", repo_id="R1", file_name="") == []


@pytest.mark.asyncio
async def test_get_repo_file_chunks_returns_empty_on_internal_error(monkeypatch, repo, db_client):
    
    class Boom:
        @staticmethod
        def find(*args, **kwargs):
            raise RuntimeError("boom")

    # Patch this instance's model to raise
    monkeypatch.setattr(repo, "model", Boom)

    rows = await repo.get_repo_file_chunks(user_id="U1", repo_id="R1", file_name="x")
    assert rows == []

###############################################################################
# get_user_repo_chunks_multi
###############################################################################

def _zeros(n: int = EMBED_DIM) -> List[float]:
    return [0.0] * n

def _embed_xy(x: float, y: float, n: int = EMBED_DIM) -> List[float]:
    """Vector with first 2 dims = (x, y), rest zeros."""
    v = [0.0] * n
    v[0] = float(x)
    v[1] = float(y)
    return v

def _unit_e(i: int, n: int = EMBED_DIM) -> List[float]:
    """Standard basis vector e_i."""
    v = [0.0] * n
    v[i] = 1.0
    return v

def _mk_embed_doc(
    *,
    user_id: str = "UQ",
    repo_id: str = "RQ",
    content: str = "c",
    file_name: str = "f.txt",
    file_path: str = "/f.txt",
    file_size: int = 1,
    commit_number: str = "c1",
    embedding: List[float] | None = None,
    created_at: datetime.datetime | None = None,
):
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    return CodeChunks(
        id=uuid.uuid4(),
        user_id=user_id,
        repo_id=repo_id,
        content=content,
        file_name=file_name,
        file_path=file_path,
        file_size=file_size,
        commit_number=commit_number,
        embedding=embedding,
        created_at=created_at or now,
        updated_at=created_at or now,
    )

@pytest.mark.asyncio
async def test_get_user_repo_chunks_multi_ranks_fusion_then_max_then_date(repo, db_client):
    # Queries: q1 = e0, q2 = e1
    q1 = _unit_e(0)
    q2 = _unit_e(1)
    queries = [q1, q2]

    # Three chunks for same user/repo, crafted similarities:
    # A: emb=(1,0) -> sims=[1,0] fusion=1.0 max=1.0
    # B: emb=(0.6,0.8) (norm=1) -> sims=[0.6,0.8] fusion=1.4 max=0.8
    # C: tie on fusion with D but lower max, then older date loses
    #    build C=(0.7,0.3) fusion=1.0 max=0.7
    #    D=(0.6,0.4) fusion=1.0 max=0.6
    t0 = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    A = _mk_embed_doc(embedding=_embed_xy(1.0, 0.0), created_at=t0 + datetime.timedelta(seconds=1))
    B = _mk_embed_doc(embedding=_embed_xy(0.6, 0.8), created_at=t0 + datetime.timedelta(seconds=2))
    C = _mk_embed_doc(embedding=_embed_xy(0.7, 0.3), created_at=t0 + datetime.timedelta(seconds=3))
    D = _mk_embed_doc(embedding=_embed_xy(0.6, 0.4), created_at=t0 + datetime.timedelta(seconds=0))

    await CodeChunks.insert_many([A, B, C, D])

    rows = await repo.get_user_repo_chunks_multi(
        user_id="UQ",
        repo_id="RQ",
        query_embeddings=queries,
        emb_dim=EMBED_DIM,
        limit=10,
    )

    # Expected order:
    # 1) B (fusion 1.4)
    # 2) C (fusion 1.0, max 0.7)
    # 3) A (fusion 1.0, max 1.0)  <-- wait, max 1.0 > 0.7. But fusion primary, then max.
    # Careful! A's fusion is 1.0 as well; its max is 1.0, so A should come before C.
    # Correct order: B, A, C, D (fusion desc, then max desc, then created_at desc)
    ids = [r["id"] for r in rows]
    assert ids[:4] == [B.id, A.id, C.id, D.id]
    # Check required fields exist
    assert {"id", "file_name", "file_path", "content", "created_at", "fusion_score", "max_sim"} <= set(rows[0].keys())


# ---------------------------------------------------------------------
# 2) Filters strictly by user and repo
# ---------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_user_repo_chunks_multi_filters_by_user_repo(repo, db_client):
    q = [_unit_e(0)]

    good = _mk_embed_doc(user_id="U1", repo_id="R1", embedding=_embed_xy(1.0, 0.0))
    wrong_user = _mk_embed_doc(user_id="U2", repo_id="R1", embedding=_embed_xy(1.0, 0.0))
    wrong_repo = _mk_embed_doc(user_id="U1", repo_id="R2", embedding=_embed_xy(1.0, 0.0))
    await CodeChunks.insert_many([good, wrong_user, wrong_repo])

    rows = await repo.get_user_repo_chunks_multi("U1", "R1", q, EMBED_DIM, limit=10)
    assert [r["id"] for r in rows] == [good.id]

# ---------------------------------------------------------------------
# 3) Handles zero-norm queries safely (treated as 0 similarity)
# ---------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_user_repo_chunks_multi_handles_zero_norm_queries(repo, db_client):
    # One real query (e0), one zero-norm query (all zeros)
    q_real = _unit_e(0)
    q_zero = _zeros()
    queries = [q_real, q_zero]

    d = _mk_embed_doc(user_id="UZ", repo_id="RZ", embedding=_embed_xy(1.0, 0.0))
    await CodeChunks.insert_many([d])

    rows = await repo.get_user_repo_chunks_multi("UZ", "RZ", queries, EMBED_DIM, limit=10)
    assert len(rows) == 1
    # fusion ~ 1.0 + 0.0
    assert rows[0]["fusion_score"] == pytest.approx(1.0, rel=1e-6, abs=1e-6)


# ---------------------------------------------------------------------
# 4) Respects limit and ordering by created_at when other keys tie
# ---------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_user_repo_chunks_multi_respects_limit_and_created_at_tiebreak(repo, db_client):
    q = [_unit_e(0), _unit_e(1)]  # both used to get equal fusion/max for same embeddings

    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    # Two identical embeddings; newer created_at should come first
    newer = _mk_embed_doc(user_id="UL", repo_id="RL", embedding=_embed_xy(1.0, 0.0), created_at=now + datetime.timedelta(seconds=2))
    older = _mk_embed_doc(user_id="UL", repo_id="RL", embedding=_embed_xy(1.0, 0.0), created_at=now + datetime.timedelta(seconds=1))
    extra = _mk_embed_doc(user_id="UL", repo_id="RL", embedding=_embed_xy(0.5, 0.5), created_at=now)

    await CodeChunks.insert_many([older, newer, extra])

    rows = await repo.get_user_repo_chunks_multi("UL", "RL", q, EMBED_DIM, limit=2)
    assert len(rows) == 2
    # Newer identical should be before older
    assert rows[0]["id"] == newer.id
    assert rows[1]["id"] in {older.id, extra.id}  # depends on fusion vs. extra; limit=2 enforces truncation


# ---------------------------------------------------------------------
# 5) Returns [] on bad inputs or dimension mismatch
# ---------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_user_repo_chunks_multi_returns_empty_on_bad_inputs(repo, db_client):
    q = [_unit_e(0)]
    assert await repo.get_user_repo_chunks_multi("", "R", q, EMBED_DIM, 10) == []
    assert await repo.get_user_repo_chunks_multi("U", "", q, EMBED_DIM, 10) == []
    assert await repo.get_user_repo_chunks_multi("U", "R", [], EMBED_DIM, 10) == []
    assert await repo.get_user_repo_chunks_multi("U", "R", q, EMBED_DIM, 0) == []

@pytest.mark.asyncio
async def test_get_user_repo_chunks_multi_returns_empty_on_dimension_mismatch(repo, db_client):
    bad_q = [[1.0] * (EMBED_DIM - 1)]
    rows = await repo.get_user_repo_chunks_multi("U", "R", bad_q, EMBED_DIM, 10)
    assert rows == []


# ---------------------------------------------------------------------
# 6) id remains UUID objects (not coerced to str)
# ---------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_user_repo_chunks_multi_returns_uuid_ids(repo, db_client):
    q = [_unit_e(0)]
    d = _mk_embed_doc(user_id="UT", repo_id="RT", embedding=_embed_xy(1.0, 0.0))
    await CodeChunks.insert_many([d])

    rows = await repo.get_user_repo_chunks_multi("UT", "RT", q, EMBED_DIM, 10)
    assert isinstance(rows[0]["id"], uuid.UUID)