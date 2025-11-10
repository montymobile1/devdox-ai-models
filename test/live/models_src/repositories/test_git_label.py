import datetime
import math
import uuid
from uuid import UUID

import pytest
from pydantic import ValidationError

from models_src.db_inits.beanie_init import init_via_uri
from models_src.models.git_label_document import GitLabel
from models_src.dto.git_label import GitLabelRequestDTO
from models_src.repositories.git_label import BeanieGitLabelStore


###############################################################################
# Fixtures & helpers
###############################################################################

@pytest.fixture
def repo() -> BeanieGitLabelStore:
    return BeanieGitLabelStore()


def mk_req(
    *,
    user_id="u1",
    label="Work Token",
    git_hosting="github",
    username="alice",
    token_value="tkn_xxx",
    masked_token="***xxx",
    **kw,
) -> GitLabelRequestDTO:
    base = dict(
        user_id=user_id,
        label=label,
        git_hosting=git_hosting,
        username=username,
        token_value=token_value,
        masked_token=masked_token,
    )
    base.update(kw)
    return GitLabelRequestDTO(**base)


def mk_doc(**kw) -> GitLabel:
    now = datetime.datetime.now(datetime.timezone.utc)
    # generate a unique masked_token unless provided
    masked = kw.pop("masked_token", f"***{uuid.uuid4().hex[:6]}")
    base = dict(
        id=uuid.uuid4(),
        user_id="u1",
        label="Work",
        git_hosting="github",
        username="alice",
        token_value="tkn",
        masked_token=masked,   # <— unique unless overridden
        created_at=now,
        updated_at=now,
    )
    base.update(kw)
    return GitLabel(**base)


###############################################################################
# save
###############################################################################

@pytest.mark.asyncio
async def test_save_persists_minimal_and_maps_fields(repo, db_client):
    dto = await repo.save(mk_req(user_id="S1", masked_token="***abc"))
    assert dto is not None
    assert dto.user_id == "S1"
    assert dto.git_hosting == "github"
    assert dto.masked_token == "***abc"
    assert dto.id and isinstance(dto.id, UUID)
    assert dto.created_at and dto.updated_at
    # created_at >= updated_at is not guaranteed, but both must be populated


@pytest.mark.asyncio
async def test_save_violates_unique_index_for_same_user_hosting_masked_token(repo, db_client):
    await repo.save(mk_req(user_id="U1", git_hosting="github", masked_token="***same"))
    with pytest.raises(Exception):
        await repo.save(mk_req(user_id="U1", git_hosting="github", masked_token="***same"))


@pytest.mark.asyncio
async def test_save_allows_same_hosting_and_masked_token_for_different_users(repo, db_client):
    await repo.save(mk_req(user_id="UA", masked_token="***same"))
    dto = await repo.save(mk_req(user_id="UB", masked_token="***same"))
    assert dto.user_id == "UB"


@pytest.mark.asyncio
async def test_save_raises_validation_error_on_oversize_fields(repo, db_client):
    # git_hosting has max_length=50
    long_hosting = "x" * 200
    with pytest.raises(ValidationError):
        await repo.save(mk_req(git_hosting=long_hosting))


###############################################################################
# find_git_hostings_by_ids
###############################################################################

@pytest.mark.asyncio
async def test_find_git_hostings_by_ids_empty_input_returns_empty_list(repo, db_client):
    rows = await repo.find_git_hostings_by_ids([])
    assert rows == []


###############################################################################
# find_by_token_id_and_user
###############################################################################

@pytest.mark.asyncio
async def test_find_by_token_id_and_user_returns_document_for_valid_pair(repo, db_client):
    d = mk_doc(user_id="F1", label="Personal", git_hosting="gitlab", masked_token="***222")
    await GitLabel.insert_many([d])

    dto = await repo.find_by_token_id_and_user(str(d.id), "F1")
    assert dto is not None
    assert dto.label == "Personal"


@pytest.mark.asyncio
async def test_find_by_token_id_and_user_returns_none_on_mismatch_or_bad_id(repo, db_client):
    d = mk_doc(user_id="F2")
    await GitLabel.insert_many([d])

    # wrong user
    assert (await repo.find_by_token_id_and_user(str(d.id), "nope")) is None
    # bad uuid
    assert (await repo.find_by_token_id_and_user("not-a-uuid", "F2")) is None
    # blank
    assert (await repo.find_by_token_id_and_user("   ", "F2")) is None


###############################################################################
# find_by_id_and_user_id_and_git_hosting
###############################################################################

@pytest.mark.asyncio
async def test_find_by_id_and_user_id_and_git_hosting_returns_match(repo, db_client):
    d = mk_doc(user_id="T1", git_hosting="gitlab", username="bob")
    await GitLabel.insert_many([d])

    dto = await repo.find_by_id_and_user_id_and_git_hosting(str(d.id), "T1", "gitlab")
    assert dto is not None
    assert dto.username == "bob"


@pytest.mark.asyncio
async def test_find_by_id_and_user_id_and_git_hosting_returns_none_for_wrong_triplet(repo, db_client):
    d = mk_doc(user_id="T2", git_hosting="github")
    await GitLabel.insert_many([d])

    assert (await repo.find_by_id_and_user_id_and_git_hosting(str(d.id), "T2", "gitlab")) is None
    assert (await repo.find_by_id_and_user_id_and_git_hosting(str(uuid.uuid4()), "T2", "github")) is None
    assert (await repo.find_by_id_and_user_id_and_git_hosting("not-a-uuid", "T2", "github")) is None


###############################################################################
# find_all_by_user_id (+ hosting filter) & count_by_user_id
###############################################################################

@pytest.mark.asyncio
async def test_find_all_by_user_id_returns_desc_sorted_and_paginates(repo, db_client):
    u = "P_USER"
    other = "Q_USER"
    start = datetime.datetime.now(datetime.timezone.utc).replace(minute=0, second=0, microsecond=0)

    docs = []
    for i in range(5):
        docs.append(
            mk_doc(
                user_id=u,
                label=f"L{i}",
                git_hosting="github" if i % 2 == 0 else "gitlab",
                masked_token=f"***{i:03d}",
                created_at=start + datetime.timedelta(hours=i),
                updated_at=start + datetime.timedelta(hours=i),
            )
        )
    # foreign user
    docs.append(
        mk_doc(
            user_id=other,
            label="Other",
            git_hosting="github",
            masked_token="***zzz",
            created_at=start + datetime.timedelta(hours=999),
            updated_at=start + datetime.timedelta(hours=999),
        )
    )
    await GitLabel.insert_many(docs)

    only_u = [d for d in docs if d.user_id == u]
    expected_sorted = sorted(only_u, key=lambda d: d.created_at, reverse=True)
    expected_ids = [d.id for d in expected_sorted]

    # counts
    assert await repo.count_by_user_id(u) == 5
    assert await repo.count_by_user_id(other) == 1

    LIMIT = 2
    pages = math.ceil(5 / LIMIT) + 1
    seen = []
    for p in range(pages):
        items = await repo.find_all_by_user_id(offset=p, limit=LIMIT, user_id=u)
        ids = [it.id for it in items]
        created = [it.created_at for it in items]

        exp_len = max(0, min(LIMIT, 5 - p * LIMIT))
        assert len(items) == exp_len
        assert ids == expected_ids[p * LIMIT : (p + 1) * LIMIT]
        assert created == sorted(created, reverse=True)

        seen.extend(ids)

    assert len(seen) == 5 and len(set(seen)) == 5 and seen == expected_ids


@pytest.mark.asyncio
async def test_find_all_by_user_id_applies_git_hosting_filter_when_provided(repo, db_client):
    now = datetime.datetime.now(datetime.timezone.utc)
    await GitLabel.insert_many(
        [
            mk_doc(user_id="HF", git_hosting="github", created_at=now, updated_at=now),
            mk_doc(user_id="HF", git_hosting="gitlab", created_at=now, updated_at=now),
            mk_doc(user_id="HF", git_hosting="github", created_at=now, updated_at=now),
        ]
    )
    items = await repo.find_all_by_user_id(offset=0, limit=10, user_id="HF", git_hosting="github")
    assert len(items) == 2
    assert all(i.git_hosting == "github" for i in items)


@pytest.mark.asyncio
async def test_count_by_user_id_applies_git_hosting_filter(repo, db_client):
    now = datetime.datetime.now(datetime.timezone.utc)
    await GitLabel.insert_many(
        [
            mk_doc(user_id="HC", git_hosting="github", created_at=now, updated_at=now),
            mk_doc(user_id="HC", git_hosting="gitlab", created_at=now, updated_at=now),
            mk_doc(user_id="HC", git_hosting="github", created_at=now, updated_at=now),
        ]
    )
    assert await repo.count_by_user_id("HC") == 3
    assert await repo.count_by_user_id("HC", git_hosting="github") == 2
    assert await repo.count_by_user_id("HC", git_hosting="gitlab") == 1


@pytest.mark.asyncio
async def test_find_all_by_user_id_raises_on_missing_user_id(repo, db_client):
    with pytest.raises(Exception):
        await repo.find_all_by_user_id(offset=0, limit=10, user_id="")


###############################################################################
# find_all_by_user_id_and_label & count_by_user_id_and_label (regex semantics)
###############################################################################

@pytest.mark.asyncio
async def test_find_all_by_user_id_and_label_matches_case_insensitive_contains(repo, db_client):
    now = datetime.datetime.now(datetime.timezone.utc)
    await GitLabel.insert_many(
        [
            mk_doc(user_id="RX", label="Work", git_hosting="github", created_at=now, updated_at=now),
            mk_doc(user_id="RX", label="work tools", git_hosting="gitlab", created_at=now, updated_at=now),
            mk_doc(user_id="RX", label="Personal", git_hosting="github", created_at=now, updated_at=now),
            mk_doc(user_id="RY", label="Work", git_hosting="github", created_at=now, updated_at=now),
        ]
    )
    items = await repo.find_all_by_user_id_and_label(offset=0, limit=10, user_id="RX", label="orK")
    got = {i.label for i in items}
    assert got == {"Work", "work tools"}


@pytest.mark.asyncio
async def test_find_all_by_user_id_and_label_honors_regex_anchors(repo, db_client):
    now = datetime.datetime.now(datetime.timezone.utc)
    await GitLabel.insert_many(
        [
            mk_doc(user_id="RZ", label="Work", created_at=now, updated_at=now),
            mk_doc(user_id="RZ", label="work tools", created_at=now, updated_at=now),
        ]
    )
    # '^Work$' should match exactly "Work" (case-insensitive), not "work tools"
    items = await repo.find_all_by_user_id_and_label(offset=0, limit=10, user_id="RZ", label="^Work$")
    assert [i.label for i in items] == ["Work"]


@pytest.mark.asyncio
async def test_count_by_user_id_and_label_counts_case_insensitive_regex(repo, db_client):
    now = datetime.datetime.now(datetime.timezone.utc)
    await GitLabel.insert_many(
        [
            mk_doc(user_id="RC", label="Work", created_at=now, updated_at=now),
            mk_doc(user_id="RC", label="work tools", created_at=now, updated_at=now),
            mk_doc(user_id="RC", label="Personal", created_at=now, updated_at=now),
        ]
    )
    cnt = await repo.count_by_user_id_and_label("RC", "work")
    assert cnt == 2


@pytest.mark.asyncio
async def test_find_all_by_user_id_and_label_raises_on_missing_inputs(repo, db_client):
    with pytest.raises(Exception):
        await repo.find_all_by_user_id_and_label(offset=0, limit=10, user_id="", label="x")
    with pytest.raises(Exception):
        await repo.find_all_by_user_id_and_label(offset=0, limit=10, user_id="U", label="  ")


@pytest.mark.asyncio
async def test_count_by_user_id_and_label_raises_on_missing_inputs(repo, db_client):
    with pytest.raises(Exception):
        await repo.count_by_user_id_and_label("", "x")
    with pytest.raises(Exception):
        await repo.count_by_user_id_and_label("U", "  ")


###############################################################################
# delete_by_id_and_user_id
###############################################################################

@pytest.mark.asyncio
async def test_delete_by_id_and_user_id_deletes_one_and_returns_counts(repo, db_client):
    d1 = mk_doc(user_id="D1", label="A", masked_token="***a")
    d2 = mk_doc(user_id="D1", label="B", masked_token="***b")
    await GitLabel.insert_many([d1, d2])

    deleted = await repo.delete_by_id_and_user_id(str(d1.id), "D1")
    assert deleted == 1

    # second delete -> 0
    deleted_again = await repo.delete_by_id_and_user_id(str(d1.id), "D1")
    assert deleted_again == 0


@pytest.mark.asyncio
async def test_delete_by_id_and_user_id_returns_zero_when_not_found(repo, db_client):
    d = mk_doc(user_id="D2")
    await GitLabel.insert_many([d])
    assert await repo.delete_by_id_and_user_id(str(uuid.uuid4()), "D2") == 0


@pytest.mark.asyncio
async def test_delete_by_id_and_user_id_returns_minus_one_on_invalid_inputs(repo, db_client):
    d = mk_doc(user_id="D3")
    await GitLabel.insert_many([d])

    assert await repo.delete_by_id_and_user_id("not-a-uuid", "D3") == -1
    assert await repo.delete_by_id_and_user_id(str(d.id), "") == -1
