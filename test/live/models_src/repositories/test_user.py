import datetime
import uuid
import pytest

from models_src.repositories.user import BeanieUserStore
from models_src.dto.user import UserRequestDTO

store = BeanieUserStore


def _mk_user_request(
    user_id: str = "user_abc",
    first_name: str = "Alice",
    last_name: str = "Doe",
    email: str = "alice@example.com",
    role: str = "member",
    username: str = "alice",
    active: bool = True,
    membership_level: str = "free",
    token_limit: int = 1000,
    token_used: int = 0,
    encryption_salt: str = "0",
):
    # Build whatever your UserRequestDTO actually requires
    return UserRequestDTO(
        user_id=user_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        username=username,
        role=role,
        active=active,
        membership_level=membership_level,
        token_limit=token_limit,
        token_used=token_used,
        encryption_salt=encryption_salt,
    )


@pytest.mark.asyncio
async def test_user_save_inserts_and_maps(db_client):
        repo = store()

        req = _mk_user_request(user_id="user_1", email="u1@example.com", first_name="U", last_name="One")
        inserted = await repo.save(req)

        assert inserted is not None
        assert inserted.user_id == "user_1"
        assert inserted.email == "u1@example.com"
        assert inserted.first_name == "U"
        assert inserted.last_name == "One"

        # verify it exists in DB
        in_db = await repo.model.find_one(repo.model.user_id == "user_1")
        assert in_db is not None
        assert in_db.email == "u1@example.com"


@pytest.mark.asyncio
async def test_user_find_by_user_id_found_missing_blank(db_client):
    repo = store()

    # Insert two users (direct insert to avoid DTO dependency if needed)
    u1 = repo.model(
        id=uuid.uuid4(),
        user_id="user_find_1",
        first_name="John",
        last_name="Smith",
        email="john@example.com",
        username="john",
        role="member",
        active=True,
        membership_level="free",
        token_limit=500,
        token_used=0,
        encryption_salt="0",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
    )
    u2 = repo.model(
        id=uuid.uuid4(),
        user_id="user_find_2",
        first_name="Jane",
        last_name="Roe",
        email="jane@example.com",
        username="jane",
        role="admin",
        active=True,
        membership_level="pro",
        token_limit=5000,
        token_used=10,
        encryption_salt="0",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
    )
    await repo.model.insert_many([u1, u2])

    # found
    dto = await repo.find_by_user_id("user_find_1")
    assert dto is not None
    assert dto.email == "john@example.com"
    assert dto.role == "member"

    # missing
    dto2 = await repo.find_by_user_id("does_not_exist")
    assert dto2 is None

    # blank short-circuit
    dto3 = await repo.find_by_user_id("   ")
    assert dto3 is None



@pytest.mark.asyncio
async def test_user_increment_token_usage_happy_path_and_edges(db_client):

    repo = store()

    # Insert two users
    u1 = repo.model(
        id=uuid.uuid4(),
        user_id="user_inc_1",
        first_name="A",
        last_name="A",
        email="a@example.com",
        username="a",
        role="member",
        active=True,
        membership_level="free",
        token_limit=1000,
        token_used=100,
        encryption_salt="0",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
    )
    u2 = repo.model(
        id=uuid.uuid4(),
        user_id="user_inc_2",
        first_name="B",
        last_name="B",
        email="b@example.com",
        username="b",
        role="member",
        active=True,
        membership_level="free",
        token_limit=1000,
        token_used=50,
        encryption_salt="0",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
    )
    await repo.model.insert_many([u1, u2])

    # ACT: increment user_inc_1 by 250
    matched = await repo.increment_token_usage("user_inc_1", 250)
    assert matched == 1

    # ASSERT: only u1 changed
    d1 = await repo.model.find_one(repo.model.user_id == "user_inc_1")
    d2 = await repo.model.find_one(repo.model.user_id == "user_inc_2")
    assert d1.token_used == 350
    assert d2.token_used == 50

    # Missing user -> 0
    matched_missing = await repo.increment_token_usage("no_such_user", 10)
    assert matched_missing == 0

    # Invalid inputs -> -1 (legacy semantics)
    assert await repo.increment_token_usage("   ", 10) == -1
    assert await repo.increment_token_usage("user_inc_1", 0) == -1

@pytest.mark.asyncio
async def test_exists_by_user_id(db_client):
    repo = store()
    
    # Insert two users (direct insert to avoid DTO dependency if needed)
    u1 = repo.model(
        id=uuid.uuid4(),
        user_id="user_find_1",
        first_name="John",
        last_name="Smith",
        email="john@example.com",
        username="john",
        role="member",
        active=True,
        membership_level="free",
        token_limit=500,
        token_used=0,
        encryption_salt="0",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
    )
    u2 = repo.model(
        id=uuid.uuid4(),
        user_id="user_find_2",
        first_name="Jane",
        last_name="Roe",
        email="jane@example.com",
        username="jane",
        role="admin",
        active=True,
        membership_level="pro",
        token_limit=5000,
        token_used=10,
        encryption_salt="0",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
    )
    await repo.model.insert_many([u1, u2])
    
    # found
    dto = await repo.exists_by_user_id("user_find_1")
    assert dto is True
    
    # missing
    dto2 = await repo.exists_by_user_id("does_not_exist")
    assert dto2 is False
    
    # blank short-circuit
    dto3 = await repo.exists_by_user_id("   ")
    assert dto3 is False