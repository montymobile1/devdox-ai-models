import datetime
import math
import uuid
import pytest

from models_src.repositories.repo import BeanieRepoStore
from models_src.dto.repo import RepoRequestDTO
from models_src.models.repo_enums import StatusTypes

store = BeanieRepoStore

def _mk_req(
    user_id="user_X",
    repo_id="gid_1",
    repo_name="alpha",
    html_url="https://host/alpha",
    repo_alias_name="alpha-local",
    **kw,
):
    # supply only the required + common fields; everything else uses defaults
    return RepoRequestDTO(
        user_id=user_id,
        repo_id=repo_id,
        repo_name=repo_name,
        html_url=html_url,
        repo_alias_name=repo_alias_name,
        **kw,
    )

@pytest.mark.asyncio
async def test_repo_save_inserts_and_maps(db_client):
    
    repo = store()
    req = _mk_req(user_id="u1", repo_id="r1", repo_name="A", html_url="http://x/A", repo_alias_name="A-local")
    dto = await repo.save(req)

    assert dto is not None
    assert dto.user_id == "u1"
    assert dto.repo_id == "r1"
    assert dto.repo_name == "A"
    assert dto.html_url == "http://x/A"
    assert dto.repo_alias_name == "A-local"

    in_db = await repo.model.find_one(repo.model.user_id == "u1", repo.model.repo_id == "r1")
    assert in_db is not None

@pytest.mark.asyncio
async def test_repo_find_all_by_user_pagination_and_sorting(db_client):

    repo = store()

    user_id = "u1"
    other_user = "u2"

    # create 5 repos for u1 with ascending created_at
    start = datetime.datetime.now(datetime.timezone.utc).replace(minute=0, second=0, microsecond=0)
    docs = []
    for i in range(5):
        d = repo.model(
            id=uuid.uuid4(),
            user_id=user_id,
            repo_id=f"rid{i}",
            repo_name=f"R{i}",
            html_url=f"http://h/R{i}",
            repo_alias_name=f"alias{i}",
            created_at=start + datetime.timedelta(hours=i),
            updated_at=start + datetime.timedelta(hours=i),
        )
        docs.append(d)
    # add a foreign user doc
    foreign = repo.model(
        id=uuid.uuid4(),
        user_id=other_user,
        repo_id="foreign",
        repo_name="F",
        html_url="http://h/F",
        repo_alias_name="aliasF",
        created_at=start + datetime.timedelta(hours=999),
        updated_at=start + datetime.timedelta(hours=999),
    )
    await repo.model.insert_many([*docs, foreign])

    # expected order: DESC by created_at
    expected_sorted = sorted(docs, key=lambda d: d.created_at, reverse=True)
    expected_ids = [d.id for d in expected_sorted]

    LIMIT = 2
    pages = math.ceil(len(docs) / LIMIT) + 1
    seen = []

    # sanity
    assert await repo.count_by_user_id(user_id) == len(docs)

    for p in range(pages):
        items = await repo.find_all_by_user_id(user_id=user_id, offset=p, limit=LIMIT)
        ids = [it.id for it in items]
        created = [it.created_at for it in items]

        exp_len = max(0, min(LIMIT, len(docs) - p * LIMIT))
        assert len(items) == exp_len

        exp_slice = expected_ids[p * LIMIT:(p + 1) * LIMIT]
        assert ids == exp_slice
        assert created == sorted(created, reverse=True)

        seen.extend(ids)

    assert len(seen) == len(docs)
    assert len(set(seen)) == len(docs)
    assert seen == expected_ids


@pytest.mark.asyncio
async def test_repo_get_find_variants_and_html_url_lookup(db_client):

    repo = store()

    d = repo.model(
        id=uuid.uuid4(),
        user_id="u1",
        repo_id="rid1",
        repo_name="Alpha",
        html_url="http://h/A",
        repo_alias_name="alpha",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
    )
    await repo.model.insert_many([d])

    # find_by_repo_id
    dto = await repo.find_by_repo_id("rid1")
    assert dto is not None and dto.repo_name == "Alpha"

    # find_by_repo_id_user_id
    dto2 = await repo.find_by_repo_id_user_id("rid1", "u1")
    assert dto2 is not None and dto2.html_url == "http://h/A"

    # find_by_id (string-UUID)
    dto3 = await repo.find_by_id(str(d.id))
    assert dto3 is not None and dto3.repo_name == "Alpha"

    # find_by_user_id_and_html_url
    dto4 = await repo.find_by_user_id_and_html_url("u1", "http://h/A")
    assert dto4 is not None and dto4.repo_id == "rid1"

    # find_by_id (missing)
    assert await repo.find_by_id(str(uuid.uuid4())) is None


@pytest.mark.asyncio
async def test_repo_update_analysis_metadata_and_system_reference(db_client):

    repo = store()

    d = repo.model(
        id=uuid.uuid4(),
        user_id="u1",
        repo_id="rid1",
        repo_name="Alpha",
        html_url="http://h/A",
        repo_alias_name="alpha",
        total_files=0,
        total_chunks=0,
        total_embeddings=0,
        status=StatusTypes.IN_PROGRESS,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
    )
    await repo.model.insert_many([d])

    end_time = datetime.datetime.now(datetime.timezone.utc)

    matched = await repo.update_analysis_metadata_by_id(
        id=str(d.id),
        status=StatusTypes.COMPLETED,
        processing_end_time=end_time,
        total_files=10,
        total_chunks=20,
        total_embeddings=30,
    )
    assert matched == 1

    in_db = await repo.model.find_one(repo.model.id == d.id)
    assert in_db.status == StatusTypes.COMPLETED
    assert in_db.processing_end_time.date() == end_time.date()
    assert in_db.total_files == 10
    assert in_db.total_chunks == 20
    assert in_db.total_embeddings == 30

    # system reference
    matched2 = await repo.update_repo_system_reference_by_id(str(d.id), "SYS-REF-001")
    assert matched2 == 1
    in_db2 = await repo.model.find_one(repo.model.id == d.id)
    assert in_db2.repo_system_reference == "SYS-REF-001"

    # bad inputs
    assert await repo.update_analysis_metadata_by_id("", "", end_time, 1, 1, 1) == -1
    assert await repo.update_repo_system_reference_by_id("   ", "X") == -1


@pytest.mark.asyncio
async def test_repo_find_by_user_and_path_and_alias_and_save_context(db_client):

    repo = store()

    d = repo.model(
        id=uuid.uuid4(),
        user_id="u1",
        repo_id="rid1",
        repo_name="Alpha",
        html_url="http://h/A",
        repo_alias_name="alpha",
        relative_path="/u1/alpha",
        status=StatusTypes.IN_PROGRESS,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
    )
    await repo.model.insert_many([d])

    # find by path
    dto_p = await repo.find_by_user_and_path("u1", "/u1/alpha")
    assert dto_p is not None and dto_p.repo_name == "Alpha"

    # find by alias
    dto_a = await repo.find_by_user_and_alias_name("u1", "alpha")
    assert dto_a is not None and dto_a.repo_id == "rid1"

    # save_context: flips status to 'pending' on existing repo
    dto_c = await repo.save_context("rid1", "u1", config={"ignored": True})
    assert dto_c is not None and dto_c.status == StatusTypes.PENDING

    # save_context on missing -> error
    with pytest.raises(Exception):
        await repo.save_context("nope", "u1", config={})
