import inspect
import uuid

import pytest

from models_src.repositories.test_doubles import (
    _CallSpyMixin,
    _ExceptionPlanMixin,
    _StubPlanMixin,
    _FakeBase,
    _FakeStore,
    _StubStore,
    GenericFakeStore,
    GenericStubStore,
)


# ---------------------------------------------------------------------------
# Helpers for tests
# ---------------------------------------------------------------------------

async def async_output_fn(user_id: str) -> str:
    return f"async-{user_id}"


def sync_output_fn(user_id: str) -> str:
    return f"sync-{user_id}"


async def dummy_method(user_id: str) -> str:  # just to get a stable __name__
    return f"dummy-{user_id}"


class DummyStore:
    """Simple async store-like object for FakeStore/GenericFakeStore tests."""
    def __init__(self):
        self.calls = []
        self.non_callable_attr = "static-value"

    async def foo(self, x, y=1):
        self.calls.append(("foo", x, y))
        return x + y

    async def bar(self, *, label: str):
        self.calls.append(("bar", label))
        return label.upper()


# ---------------------------------------------------------------------------
# _CallSpyMixin
# ---------------------------------------------------------------------------

class TestCallSpyMixin:
    def test_touch_records_name_args_kwargs(self):
        spy = _CallSpyMixin()

        def some_func(a, b):
            return a + b

        name = spy._touch(some_func, 1, b=2)

        assert name == "some_func"
        assert len(spy.received_calls) == 1
        method_name, args, kwargs = spy.received_calls[0]
        assert method_name == "some_func"
        assert args == (1,)
        assert kwargs == {"b": 2}

    def test_touch_name_records_with_given_name(self):
        spy = _CallSpyMixin()

        name = spy._touch_name("my_method", 42, flag=True)

        assert name == "my_method"
        assert len(spy.received_calls) == 1
        method_name, args, kwargs = spy.received_calls[0]
        assert method_name == "my_method"
        assert args == (42,)
        assert kwargs == {"flag": True}


# ---------------------------------------------------------------------------
# _ExceptionPlanMixin
# ---------------------------------------------------------------------------

class TestExceptionPlanMixin:
    def test_set_exception_and_maybe_raise(self):
        mixin = _ExceptionPlanMixin()

        def fn():
            pass

        exc = ValueError("boom")
        mixin.set_exception(fn, exc)

        # Correct name -> raises
        with pytest.raises(ValueError) as exc_info:
            mixin._maybe_raise("fn")
        assert str(exc_info.value) == "boom"

        # Other name -> no exception
        mixin._maybe_raise("other-method")  # should not raise


# ---------------------------------------------------------------------------
# _StubPlanMixin
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestStubPlanMixin:
    async def test_stub_returns_constant_output(self):
        stub = _StubPlanMixin()

        async def get_user(user_id: str):
            return "ignored"

        stub.set_output(get_user, {"user_id": "u-1"})
        result = await stub._stub(get_user, user_id="some-id")

        assert result == {"user_id": "u-1"}
        assert len(stub.received_calls) == 1
        method_name, args, kwargs = stub.received_calls[0]
        assert method_name == "get_user"
        assert args == ()
        assert kwargs == {"user_id": "some-id"}

    async def test_stub_uses_sync_callable_output(self):
        stub = _StubPlanMixin()

        async def get_user(user_id: str):
            return "ignored"

        stub.set_output(get_user, sync_output_fn)

        result = await stub._stub(get_user, user_id="abc")
        assert result == "sync-abc"

    async def test_stub_uses_async_callable_output(self):
        stub = _StubPlanMixin()

        async def get_user(user_id: str):
            return "ignored"

        stub.set_output(get_user, async_output_fn)

        result = await stub._stub(get_user, user_id="xyz")
        assert inspect.isawaitable(async_output_fn(user_id="xyz"))
        assert result == "async-xyz"

    async def test_stub_respects_planned_exception(self):
        stub = _StubPlanMixin()

        async def get_user(user_id: str):
            return "ignored"

        stub.set_output(get_user, {"user_id": "u"})
        stub.set_exception(get_user, RuntimeError("planned"))

        with pytest.raises(RuntimeError) as exc_info:
            await stub._stub(get_user, user_id="abc")

        assert str(exc_info.value) == "planned"

    async def test_stub_name_uses_name_based_resolution(self):
        stub = _StubPlanMixin()

        async def get_user(user_id: str):
            return "ignored"

        # tie the output to the function name "get_user"
        stub.set_output(get_user, {"ok": True})

        result = await stub._stub_name("get_user", user_id="abc")
        assert result == {"ok": True}
        assert len(stub.received_calls) == 1
        method_name, args, kwargs = stub.received_calls[0]
        assert method_name == "get_user"
        # wrapper passes kwargs only -> args is empty
        assert args == ()
        assert kwargs == {"user_id": "abc"}


# ---------------------------------------------------------------------------
# _FakeBase
# ---------------------------------------------------------------------------

class MyFake(_FakeBase):
    async def do_something(self, value: int):
        self._before(self.do_something, value)
        return value * 2

    async def do_something_name_based(self, value: int):
        self._before_name("do_something_name_based", value=value)
        return value * 3


@pytest.mark.asyncio
class TestFakeBase:
    async def test_before_records_call_and_no_exception(self):
        fake = MyFake()
        result = await fake.do_something(10)

        assert result == 20
        assert len(fake.received_calls) == 1
        method_name, args, kwargs = fake.received_calls[0]
        assert method_name == "do_something"
        assert args == (10,)
        assert kwargs == {}

    async def test_before_name_records_call_and_no_exception(self):
        fake = MyFake()
        result = await fake.do_something_name_based(value=5)

        assert result == 15
        assert len(fake.received_calls) == 1
        method_name, args, kwargs = fake.received_calls[0]
        assert method_name == "do_something_name_based"
        assert args == ()
        assert kwargs == {"value": 5}

    async def test_before_respects_planned_exception(self):
        fake = MyFake()
        fake.set_exception(MyFake.do_something, ValueError("stop"))

        with pytest.raises(ValueError):
            await fake.do_something(1)

        # Call is recorded before exception
        assert len(fake.received_calls) == 1
        method_name, args, kwargs = fake.received_calls[0]
        assert method_name == "do_something"
        assert args == (1,)
        assert kwargs == {}


# ---------------------------------------------------------------------------
# _FakeStore
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestFakeStore:
    async def test_fake_store_forwards_non_callables(self):
        base = DummyStore()
        fake = _FakeStore(base_store=base)

        assert fake.non_callable_attr == "static-value"
        # accessing non-callable does NOT record a call
        assert fake.received_calls == []

    async def test_fake_store_wraps_async_methods_and_records_calls(self):
        base = DummyStore()
        fake = _FakeStore(base_store=base)

        result = await fake.foo(3, y=4)
        assert result == 7

        # Underlying store called
        assert base.calls == [("foo", 3, 4)]

        # Fake recorded call
        assert len(fake.received_calls) == 1
        method_name, args, kwargs = fake.received_calls[0]
        assert method_name == "foo"
        assert args == (3,)
        assert kwargs == {"y": 4}

    async def test_fake_store_respects_planned_exception(self):
        base = DummyStore()
        fake = _FakeStore(base_store=base)

        fake.set_exception(DummyStore.foo, RuntimeError("planned-fail"))

        with pytest.raises(RuntimeError) as exc_info:
            await fake.foo(1, y=2)

        assert "planned-fail" in str(exc_info.value)

        # Underlying store should NOT have been called
        assert base.calls == []
        # But call recorded in fake spy
        assert len(fake.received_calls) == 1
        method_name, args, kwargs = fake.received_calls[0]
        assert method_name == "foo"
        assert args == (1,)
        assert kwargs == {"y": 2}


# ---------------------------------------------------------------------------
# _StubStore
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestStubStore:
    async def test_stub_store_returns_configured_value(self):
        stub = _StubStore()

        async def get_user(user_id: str):
            return "ignored"

        stub.set_output(get_user, {"id": "user-123"})

        # call via dynamically created attribute
        result = await stub.get_user(user_id="abc")

        assert result == {"id": "user-123"}
        assert len(stub.received_calls) == 1
        method_name, args, kwargs = stub.received_calls[0]
        assert method_name == "get_user"
        assert args == ()
        assert kwargs == {"user_id": "abc"}

    async def test_stub_store_with_sync_callable_output(self):
        stub = _StubStore()

        async def get_user(user_id: str):
            return "ignored"

        stub.set_output(get_user, sync_output_fn)

        result = await stub.get_user(user_id="xyz")
        assert result == "sync-xyz"

    async def test_stub_store_with_async_callable_output(self):
        stub = _StubStore()

        async def get_user(user_id: str):
            return "ignored"

        stub.set_output(get_user, async_output_fn)

        result = await stub.get_user(user_id="xyz")
        assert result == "async-xyz"

    async def test_stub_store_respects_planned_exception(self):
        stub = _StubStore()

        async def get_user(user_id: str):
            return "ignored"

        stub.set_output(get_user, {"id": "user-x"})
        stub.set_exception(get_user, ValueError("planned-stub-error"))

        with pytest.raises(ValueError) as exc_info:
            await stub.get_user(user_id="abc")
        assert "planned-stub-error" in str(exc_info.value)


# ---------------------------------------------------------------------------
# GenericFakeStore & GenericStubStore
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGenericFakeStore:
    async def test_generic_fake_store_behaves_like_fake_store(self):
        base = DummyStore()
        fake = GenericFakeStore(base_store=base)

        result = await fake.foo(10, y=5)
        assert result == 15

        assert base.calls == [("foo", 10, 5)]
        assert len(fake.received_calls) == 1
        method_name, args, kwargs = fake.received_calls[0]
        assert method_name == "foo"
        assert args == (10,)
        assert kwargs == {"y": 5}


@pytest.mark.asyncio
class TestGenericStubStore:
    async def test_generic_stub_store_behaves_like_stub_store(self):
        stub = GenericStubStore()

        async def create_api_key(user_id: str):
            return "ignored"

        # Configure using method object; name must match attribute we call
        stub.set_output(create_api_key, {"api_key": "fake-key"})

        result = await stub.create_api_key(user_id="u1")
        assert result == {"api_key": "fake-key"}

        assert len(stub.received_calls) == 1
        method_name, args, kwargs = stub.received_calls[0]
        assert method_name == "create_api_key"
        assert args == ()
        assert kwargs == {"user_id": "u1"}
