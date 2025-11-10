import datetime
import hashlib
import math
import random
import string
import uuid

import pytest

from models_src.dto.api_key import APIKeyRequestDTO
from models_src.repositories.api_key import BeanieApiKeyStore

store = BeanieApiKeyStore

def make_seeded_key(seed: int, prefix="dvd_", mask_len=24, suffix_len=4, visible=None):
    """
    Deterministic for tests: same seed -> same outputs.
    Returns (plain, masked, hashed_hex).
    """
    rng = random.Random(seed)
    alphabet = string.ascii_letters + string.digits
    tail = "".join(rng.choice(alphabet) for _ in range(suffix_len))

    if visible is None:
        visible = suffix_len  # show all tail chars by default

    plain = f"{prefix}{tail}"
    masked = f"{prefix}{'*' * mask_len}{tail[-visible:]}"
    hashed_hex = hashlib.sha256(plain.encode("utf-8")).hexdigest()
    return plain, masked, hashed_hex

@pytest.mark.asyncio
async def test_save_inserts(db_client):

    req = APIKeyRequestDTO(
        user_id="user_2xioBPMzrTczyKDABvynLeToHst",
        api_key="8410b11db2d50368c27045290ed9ae97e2393e944892f175a6d3612925b9c47c",
        masked_api_key="dvd_************************xPDU",
        is_active=True,
    )
    
    inserted = await store().save(req)
    assert inserted
    assert inserted.user_id == req.user_id


@pytest.mark.asyncio
async def test_exists_by_hash_key_where_hash_key_exists(db_client):
    
    req = APIKeyRequestDTO(
        user_id="user_2xioBPMzrTczyKDABvynLeToHst",
        api_key="8410b11db2d50368c27045290ed9ae97e2393e944892f175a6d3612925b9c47c",
        masked_api_key="dvd_************************xPDU",
        is_active=True,
    )
    
    repo = store()
    
    _ = await repo.save(req)
    
    returned_api_key = await repo.exists_by_hash_key(hash_key=req.api_key)
    
    assert returned_api_key

    
@pytest.mark.asyncio
async def test_exists_by_hash_key_where_hash_key_does_not_exist(db_client):
    
    req = APIKeyRequestDTO(
        user_id="user_2xioBPMzrTczyKDABvynLeToHst",
        api_key="8410b11db2d50368c27045290ed9ae97e2393e944892f175a6d3612925b9c47c",
        masked_api_key="dvd_************************xPDU",
        is_active=True,
    )
    
    repo = store()
    
    _ = await repo.save(req)
    
    returned_api_key = await repo.exists_by_hash_key(hash_key="HASH_KEY_DOES_NOT_EXIST")
    
    assert not returned_api_key


@pytest.mark.asyncio
async def test_update_is_active_by_user_id_and_api_key_id(db_client):
    
    req = APIKeyRequestDTO(
        user_id="user_2xioBPMzrTczyKDABvynLeToHst",
        api_key="8410b11db2d50368c27045290ed9ae97e2393e944892f175a6d3612925b9c47c",
        masked_api_key="dvd_************************xPDU",
        is_active=True,
    )
    
    repo = store()
    
    inserted = await repo.save(req)
    
    matched_count = await repo.update_is_active_by_user_id_and_api_key_id(
        user_id=req.user_id,
        api_key_id=inserted.id,
        is_active=False,
    )
    
    assert matched_count == 1
    
    returned_api_key = await repo.model.find_one(repo.model.id == inserted.id)
    assert returned_api_key.is_active == False


@pytest.mark.asyncio
async def test_count_by_user_id(db_client):
    
    # ARRANGE
    req = APIKeyRequestDTO(
        user_id="user_2xioBPMzrTczyKDABvynLeToHst",
        api_key="8410b11db2d50368c27045290ed9ae97e2393e944892f175a6d3612925b9c47c",
        masked_api_key="dvd_************************xPDU",
        is_active=True,
    )
    
    req_2 = APIKeyRequestDTO(
        user_id="user_2xioBPMzrTczyKDABvynLeToHst",
        api_key="8410b11db2d50368c27045290ed9ae97e2393e944892f175a6d3612925b9c47d",
        masked_api_key="dvd_************************oPPP",
        is_active=True,
    )
    
    repo = store()
    
    _ = await repo.save(req)
    _ = await repo.save(req_2)
    
    # ACT
    counted = await repo.count_by_user_id(req.user_id)
    
    # ASSERT
    assert counted == 2


@pytest.mark.asyncio
async def test_find_all_by_user_id_pagination_and_sorting(db_client):
    # ARRANGE
    repo = store()

    user_id = "user_2xioBPMzrTczyKDABvynLeToHst"
    other_user = "someone_else"

    current_date = datetime.datetime.now().date()
    start_of_day = datetime.datetime.combine(current_date, datetime.time.min)

    TOTAL = 5
    LIMIT = 2

    created_docs = []
    for i in range(TOTAL):
        gid = uuid.uuid4()
        # ensure different keys (avoid unique conflicts)
        _, masked, hashed = make_seeded_key(42 + i)

        doc = repo.model(
            id=gid,
            user_id=user_id,
            api_key=hashed,
            masked_api_key=masked,
            is_active=True,
            last_used_at=start_of_day,
            created_at=start_of_day + datetime.timedelta(hours=i),   # 00:00 .. 04:00
            updated_at=start_of_day + datetime.timedelta(hours=i),
        )
        created_docs.append(doc)

    # add a foreign-user doc that should never appear
    foreign_doc = repo.model(
        id=uuid.uuid4(),
        user_id=other_user,
        api_key="zzz",
        masked_api_key="***",
        is_active=True,
        last_used_at=start_of_day,
        created_at=start_of_day + datetime.timedelta(hours=999),
        updated_at=start_of_day + datetime.timedelta(hours=999),
    )

    await repo.model.insert_many([*created_docs, foreign_doc])

    # expected global order: DESC by created_at
    expected_sorted = sorted(created_docs, key=lambda d: d.created_at, reverse=True)
    expected_ids = [d.id for d in expected_sorted]

    # ACT + ASSERT (page-by-page)
    pages = math.ceil(TOTAL / LIMIT) + 1  # include one extra empty page on purpose
    seen_ids = []

    # quick sanity check on count API
    assert await repo.count_by_user_id(user_id) == TOTAL

    for page in range(pages):
        items = await repo.find_all_by_user_id(user_id=user_id, limit=LIMIT, offset=page)

        # convert to IDs / timestamps from DTOs
        ids = [it.id for it in items]
        created_list = [it.created_at for it in items]

        # expected length for this page
        exp_len = max(0, min(LIMIT, TOTAL - page * LIMIT))
        assert len(items) == exp_len, f"page {page}: expected {exp_len}, got {len(items)}"

        # the exact slice we expect on this page
        exp_slice = expected_ids[page * LIMIT:(page + 1) * LIMIT]
        assert ids == exp_slice, f"page {page}: ids {ids} != expected {exp_slice}"

        # intra-page sort (strictly descending by created_at)
        assert created_list == sorted(created_list, reverse=True), f"page {page} not sorted desc by created_at"

        # ensure all returned docs belong to the intended user
        assert all(getattr(it, "user_id", user_id) == user_id for it in items), f"page {page}: foreign user leak"

        seen_ids.extend(ids)

    # after all pages: no duplicates and the global order matches
    assert len(seen_ids) == TOTAL
    assert len(set(seen_ids)) == TOTAL
    assert seen_ids == expected_ids


@pytest.mark.asyncio
async def test_find_by_active_api_key_behaviors(db_client):
    # ARRANGE
    repo = store()

    user_id = "user_2xioBPMzrTczyKDABvynLeToHst"
    start = datetime.datetime.now(datetime.timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # two distinct keys (avoid unique-index collisions on api_key)
    api_key_active   = "hash_k1_active"
    api_key_inactive = "hash_k2_inactive"

    docs = [
        # should be returned when (api_key_active, is_active=True)
        repo.model(
            id=uuid.uuid4(),
            user_id=user_id,
            api_key=api_key_active,
            masked_api_key="dvd_************************A1",
            is_active=True,
            last_used_at=start,
            created_at=start + datetime.timedelta(hours=1),
            updated_at=start + datetime.timedelta(hours=1),
        ),
        # same user, different api_key but inactive
        repo.model(
            id=uuid.uuid4(),
            user_id=user_id,
            api_key=api_key_inactive,
            masked_api_key="dvd_************************B2",
            is_active=False,
            last_used_at=start,
            created_at=start + datetime.timedelta(hours=2),
            updated_at=start + datetime.timedelta(hours=2),
        ),
        # noise: other user, different key
        repo.model(
            id=uuid.uuid4(),
            user_id="someone_else",
            api_key="hash_noise",
            masked_api_key="dvd_************************Z9",
            is_active=True,
            last_used_at=start,
            created_at=start + datetime.timedelta(hours=3),
            updated_at=start + datetime.timedelta(hours=3),
        ),
    ]
    await repo.model.insert_many(docs)

    # ACT + ASSERT

    # 1) Happy path: active key with is_active=True -> returns DTO
    dto_active = await repo.find_by_active_api_key(api_key_active, is_active=True)
    assert dto_active is not None, "Expected an active DTO, got None"
    assert dto_active.user_id == user_id
    assert dto_active.api_key == api_key_active
    assert dto_active.is_active is True

    # 2) Inactive path: inactive key with is_active=False -> returns DTO
    dto_inactive = await repo.find_by_active_api_key(api_key_inactive, is_active=False)
    assert dto_inactive is not None, "Expected an inactive DTO, got None"
    assert dto_inactive.user_id == user_id
    assert dto_inactive.api_key == api_key_inactive
    assert dto_inactive.is_active is False

    # 3) Wrong-status path: searching inactive key with is_active=True -> None
    dto_wrong_status = await repo.find_by_active_api_key(api_key_inactive, is_active=True)
    assert dto_wrong_status is None

    # 4) Not found: unknown key -> None
    dto_missing = await repo.find_by_active_api_key("totally_unknown_key", is_active=True)
    assert dto_missing is None

    # 5) Blank key short-circuit -> None (no DB hit)
    dto_blank = await repo.find_by_active_api_key("   ", is_active=True)
    assert dto_blank is None

@pytest.mark.asyncio
async def test_update_last_used_by_id_updates_only_target_and_returns_1(db_client):

    repo = store()

    user_id = "user_2xioBPMzrTczyKDABvynLeToHst"
    start = datetime.datetime.now(datetime.timezone.utc).replace(
        minute=0, second=0, microsecond=0
    )

    # two docs with known last_used_at values
    d1 = repo.model(
        id=uuid.uuid4(),
        user_id=user_id,
        api_key="key_1",
        masked_api_key="dvd_************************K1",
        is_active=True,
        last_used_at=start - datetime.timedelta(hours=2),
        created_at=start - datetime.timedelta(hours=2),
        updated_at=start - datetime.timedelta(hours=2),
    )
    d2 = repo.model(
        id=uuid.uuid4(),
        user_id=user_id,
        api_key="key_2",
        masked_api_key="dvd_************************K2",
        is_active=True,
        last_used_at=start - datetime.timedelta(hours=1),
        created_at=start - datetime.timedelta(hours=1),
        updated_at=start - datetime.timedelta(hours=1),
    )
    await repo.model.insert_many([d1, d2])

    before_1 = (await repo.model.find_one(repo.model.id == d1.id)).last_used_at
    before_2 = (await repo.model.find_one(repo.model.id == d2.id)).last_used_at

    # Use a fixed, timezone-aware timestamp for determinism
    fixed_last_used = start + datetime.timedelta(hours=10)

    # ACT
    matched = await repo.update_last_used_by_id(str(d1.id), last_used_at=fixed_last_used)

    # ASSERT
    assert matched == 1

    after_1 = (await repo.model.find_one(repo.model.id == d1.id)).last_used_at
    after_2 = (await repo.model.find_one(repo.model.id == d2.id)).last_used_at


    # Target moved forward in time
    assert after_1 > before_1

    # Non-target unchanged
    assert after_2 == before_2

@pytest.mark.asyncio
async def test_update_last_used_by_id_string_uuid_and_edge_cases(db_client):

    repo = store()

    # insert one doc
    d = repo.model(
        id=uuid.uuid4(),
        user_id="u",
        api_key="key_x",
        masked_api_key="dvd_************************X1",
        is_active=True,
        last_used_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1),
        created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1),
        updated_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1),
    )
    await repo.model.insert_many([d])

    # 1) string UUID should work
    matched_str = await repo.update_last_used_by_id(str(d.id))
    assert matched_str == 1

    # 2) non-existent but valid UUID -> 0
    matched_missing = await repo.update_last_used_by_id(str(uuid.uuid4()))
    assert matched_missing == 0

    # 3) invalid/blank -> -1
    assert await repo.update_last_used_by_id("   ") == -1
    assert await repo.update_last_used_by_id("not-a-uuid") == -1
    assert await repo.update_last_used_by_id(None) == -1  # type: ignore[arg-type]
