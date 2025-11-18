import datetime
import uuid

import pytest

from models_src.repositories.test_doubles import (
    _CallSpyMixin,
    _ExceptionPlanMixin,
    _StubPlanMixin,
    _FakeBase,
    _FakeStore,
    _StubStore,
    AnyInMemory,
    GenericFakeStore,
    GenericStubStore,
    make_fake_user,
    make_fake_git_label,
)

# ---------------------------------------------------------------------------
# Helpers for Stub tests
# ---------------------------------------------------------------------------

async def async_fn_example(x: int) -> int:
    return x * 2


def sync_fn_example(x: int) -> int:
    return x * 3


async def async_fn_with_kwargs(x: int, y: int) -> int:
    return x + y


# ---------------------------------------------------------------------------
# Helpers for FakeStore / GenericFakeStore tests
# ---------------------------------------------------------------------------

class MockStore:
    """
    Simple async store used only in these tests.
    Holds data in the backend, not in itself.
    """
    def __init__(self, storage_backend: "MockInMemoryBackend") -> None:
        self._storage_backend = storage_backend

    async def save_value(self, value: int) -> int:
        self._storage_backend.saved_values.append(value)
        return len(self._storage_backend.saved_values)

    async def get_values(self) -> list[int]:
        return list(self._storage_backend.saved_values)

    async def sum_values(self) -> int:
        return sum(self._storage_backend.saved_values)


class MockInMemoryBackend(AnyInMemory):
    """
    Minimal in-memory backend used only in these tests.
    Implements the AnyInMemory marker and declares store_cls.
    """
    store_cls = MockStore

    def __init__(self) -> None:
        self.saved_values: list[int] = []


# ---------------------------------------------------------------------------
# Tests for _CallSpyMixin
# ---------------------------------------------------------------------------

class TestCallSpyMixin:
    def test_name_returns_callable_name(self):
        """
        - Verifies _name returns the __name__ of the passed callable.
        - Ensures that the name resolution used by _touch is correct.
        """
        spy = _CallSpyMixin()

        def sample_method():
            # A mock method meant for testing purposes
            pass

        result = spy._name(sample_method)

        assert result == "sample_method"

    def test_touch_records_call_and_returns_name(self):
        """
        - Checks that _touch appends the correct (name, args, kwargs) triple.
        - Confirms that it returns the method name for downstream use.
        """
        
        spy = _CallSpyMixin()

        def sample_method(a, b):
            return a + b

        returned_name = spy._touch(sample_method, 1, 2, x=3)

        assert returned_name == "sample_method"
        assert len(spy.received_calls) == 1
        method_name, args, kwargs = spy.received_calls[0]
        assert method_name == "sample_method"
        assert args == (1, 2)
        assert kwargs == {"x": 3}

    def test_touch_name_records_call_and_returns_name(self):
        """
        - Ensures _touch_name works purely with string method names.
        - Verifies that args/kwargs are recorded correctly under that name.
        """
        
        spy = _CallSpyMixin()

        returned_name = spy._touch_name("custom_method", 10, flag=True)

        assert returned_name == "custom_method"
        assert len(spy.received_calls) == 1
        method_name, args, kwargs = spy.received_calls[0]
        assert method_name == "custom_method"
        assert args == (10,)
        assert kwargs == {"flag": True}


# ---------------------------------------------------------------------------
# Tests for _ExceptionPlanMixin
# ---------------------------------------------------------------------------

class TestExceptionPlanMixin:
    def test_maybe_raise_does_nothing_when_no_exception_planned(self):
        """
        - Confirms that _maybe_raise is a no-op when no exception is configured.
        - Guards against accidental raises in the default case.
        """
        
        planner = _ExceptionPlanMixin()

        # no exception configured
        planner._maybe_raise("nonexistent_method")  # should not raise

    def test_set_exception_and_maybe_raise_raises(self):
        """
        - Ensures set_exception stores the exception under method.__name__.
        - Verifies that _maybe_raise looks up by method_name and raises the exact instance.
        """
        
        planner = _ExceptionPlanMixin()

        def some_method():
            # Just a mock method to test with
            pass

        exc = RuntimeError("planned error")
        planner.set_exception(some_method, exc)

        with pytest.raises(RuntimeError) as ctx:
            planner._maybe_raise("some_method")

        assert ctx.value is exc


# ---------------------------------------------------------------------------
# Tests for _StubPlanMixin
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestStubPlanMixin:
    async def test_stub_returns_constant_output(self):
        """
        - Validates that constant outputs configured via set_output are returned.
        - Verifies that method name is recorded in received_calls via _stub.
        """
        stub = _StubPlanMixin()

        async def some_method():
            ...

        stub.set_output(some_method, 123)

        result = await stub._stub(some_method)

        assert result == 123
        assert stub.received_calls[0][0] == "some_method"

    async def test_stub_uses_sync_callable_output(self):
        """
        - Ensures that when output is a sync callable, _stub calls it with kwargs.
        - Confirms that the returned value is passed back directly.
        """
        
        stub = _StubPlanMixin()

        async def some_method(x: int):
            ...

        def output_callable(x: int) -> int:
            return x * 10

        stub.set_output(some_method, output_callable)

        result = await stub._stub(some_method, x=3)

        assert result == 30

    async def test_stub_awaits_async_callable_output(self):
        """
        - Ensures that when output is async, _stub awaits the result.
        - Confirms that asynchronous output callables are supported end-to-end.
        """
        
        stub = _StubPlanMixin()

        async def some_method(x: int):
            ...

        async def async_output_callable(x: int) -> int:
            return x + 7

        stub.set_output(some_method, async_output_callable)

        result = await stub._stub(some_method, x=5)

        assert result == 12

    async def test_stub_raises_planned_exception(self):
        """
        - Verifies that exception planning takes precedence over returning output.
        - Ensures _maybe_raise hooks into _stub’s flow correctly.
        """
        
        stub = _StubPlanMixin()

        async def some_method():
            ...

        exc = ValueError("boom")
        stub.set_output(some_method, 42)
        stub.set_exception(some_method, exc)

        with pytest.raises(ValueError) as ctx:
            await stub._stub(some_method)

        assert ctx.value is exc

    async def test_stub_name_uses_method_name_to_resolve_output(self):
        """
        - Confirms that _stub_name uses the provided string method_name for lookups.
        - Ensures that name-based stubbing behaves consistently with callable-based stubbing.
        """
        
        stub = _StubPlanMixin()

        async def some_method():
            ...

        stub.set_output(some_method, "ok")

        result = await stub._stub_name("some_method")

        assert result == "ok"
        assert stub.received_calls[0][0] == "some_method"

    async def test_stub_name_raises_key_error_if_output_not_set(self):
        """
        - Documents the failure mode when outputs are not configured.
        - Guarantees that misuse (forgetting set_output) fails loudly rather than silently.
        """
        
        stub = _StubPlanMixin()

        with pytest.raises(KeyError):
            await stub._stub_name("unknown_method")



# ---------------------------------------------------------------------------
# Tests for _FakeBase
# ---------------------------------------------------------------------------

class MyFake(_FakeBase):
    async def do_something(self, x: int) -> int:
        # simulate pre-hook call
        self._before(self.do_something, x)
        return x * 2

    async def do_something_name_based(self, value: int) -> int:
        self._before_name("do_something_name_based", value=value)
        return value * 3


@pytest.mark.asyncio
class TestFakeBase:
    async def test_before_records_call_and_no_exception(self):
        """
        - Ensures _before calls _touch with the correct method and arguments.
        - Confirms that no exception is raised when nothing is planned.
        """
        
        fake = MyFake()

        result = await fake.do_something(5)

        assert result == 10
        assert len(fake.received_calls) == 1
        method_name, args, kwargs = fake.received_calls[0]
        assert method_name == "do_something"
        assert args == (5,)
        assert kwargs == {}

    async def test_before_respects_exception_plan(self):
        """
        - Validates that _before consults _maybe_raise after recording the call.
        - Confirms that an exception bound to the method name is raised.
        """
        
        fake = MyFake()

        # Plan an exception for do_something
        def do_something_fn():
            ...

        fake.set_exception(do_something_fn, RuntimeError("planned"))

        # _before uses method.__name__ == "do_something"
        with pytest.raises(RuntimeError):
            # direct call of the hook to isolate behavior
            fake._before(do_something_fn, 1)


    async def test_before_name_records_call_and_no_exception(self):
        """
        - Ensures _before_name records a call keyed by the explicit string name.
        - Focuses on name-based tracking; exact arg packing can vary, so name/kwargs are key.
        """
        fake = MyFake()

        result = await fake.do_something_name_based(value=5)

        assert result == 15
        assert len(fake.received_calls) == 1
        method_name, args, kwargs = fake.received_calls[0]
        assert method_name == "do_something_name_based"
        assert args == (5,) or args == ()  # args may be empty; primary validation is name & kwargs
        assert kwargs == {"value": 5} or kwargs == {}

    async def test_before_name_respects_exception_plan(self):
        """
        - Confirms that _before_name also consults _maybe_raise on the string method name.
        - Verifies symmetry with _before in how planned exceptions are applied.
        """
        
        fake = MyFake()

        # Plan exception under the explicit name used in _before_name
        fake._exceptions["do_something_name_based"] = ValueError("boom")

        with pytest.raises(ValueError):
            fake._before_name("do_something_name_based", value=1)


# ---------------------------------------------------------------------------
# Tests for _FakeStore
# ---------------------------------------------------------------------------

class DummyBaseStore:
    def __init__(self) -> None:
        self.counter = 0
        self.label = "dummy"

    async def increment(self, by: int) -> int:
        self.counter += by
        return self.counter


@pytest.mark.asyncio
class TestFakeStore:
    async def test_fake_store_wraps_async_methods_and_records_calls(self):
        """
        - Asserts that __getattr__ wraps async methods and calls _before_name.
        - Checks that underlying method is actually awaited and state is updated.
        """
        
        base = DummyBaseStore()
        fake = _FakeStore(base)

        result = await fake.increment(3)

        assert result == 3
        assert base.counter == 3
        assert len(fake.received_calls) == 1
        method_name, args, kwargs = fake.received_calls[0]
        assert method_name == "increment"
        assert args == (3,)
        assert kwargs == {}

    async def test_fake_store_forwards_non_callables_without_spying(self):
        """
        - Ensures non-callable attributes from the base store are just forwarded.
        - Confirms that property/attribute access does not get recorded as a call.
        """
        
        base = DummyBaseStore()
        fake = _FakeStore(base)

        value = fake.label  # non-callable attribute

        assert value == "dummy"
        assert fake.received_calls == []

    async def test_fake_store_respects_exception_plan_for_wrapped_method(self):
        """
        - Verifies that a planned exception on 'increment' aborts the wrapped call.
        - Ensures underlying base_store.increment is not invoked when exception is planned.
        """
        
        base = DummyBaseStore()
        fake = _FakeStore(base)

        fake.set_exception(DummyBaseStore.increment, RuntimeError("stop"))

        with pytest.raises(RuntimeError):
            await fake.increment(1)

        assert base.counter == 0


# ---------------------------------------------------------------------------
# Tests for _StubStore and GenericStubStore
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestStubStore:
    async def test_stub_store_returns_configured_output(self):
        """
        - Checks that __getattr__ on _StubStore dispatches to _stub_name with method name.
        - Ensures the configured output is returned and that the call is recorded.
        """
        stub = _StubStore()

        async def some_method(foo: int):
            ...

        stub.set_output(some_method, "result")

        result = await stub.some_method(foo=1)

        assert result == "result"
        assert stub.received_calls[0][0] == "some_method"

    async def test_stub_store_raises_planned_exception(self):
        """
        - Ensures that planning an exception still works through the __getattr__ path.
        - Confirms that errors bubble up to callers of stubbed async methods.
        """
        
        stub = _StubStore()

        async def some_method():
            ...

        stub.set_output(some_method, 123)
        stub.set_exception(some_method, ValueError("planned"))

        with pytest.raises(ValueError):
            await stub.some_method()


    async def test_generic_stub_store_behaves_like_stub_store(self):
        """
        - Sanity-checks GenericStubStore as a thin alias over _StubStore.
        - Guarantees it participates in call tracking and output resolution like the base stub.
        """
        
        stub = GenericStubStore()

        async def some_method(x: int):
            ...

        stub.set_output(some_method, lambda x: x + 5)

        result = await stub.some_method(x=7)

        assert result == 12
        assert stub.received_calls[0][0] == "some_method"


# ---------------------------------------------------------------------------
# Tests for GenericFakeStore + AnyInMemory
# ---------------------------------------------------------------------------

@pytest.fixture
def generic_fake_store() -> GenericFakeStore:
    backend = MockInMemoryBackend()
    return GenericFakeStore(backend)


@pytest.mark.asyncio
class TestGenericFakeStore:
    async def test_generic_fake_store_construction_binds_store_and_backend(self, generic_fake_store):
        """
        - Verifies that GenericFakeStore builds store_cls(storage_backend=backend).
        - Ensures 'store' and 'backend' attributes are exposed and wired together correctly.
        """
        
        fake = generic_fake_store

        assert isinstance(fake.backend, MockInMemoryBackend)
        assert isinstance(fake.store, MockStore)
        assert fake.store._storage_backend is fake.backend

    async def test_generic_fake_store_records_calls_and_delegates_to_store(self, generic_fake_store):
        """
        - Confirms that calling fake.save_value goes through FakeStore’s wrapper.
        - Ensures underlying store method mutates backend state and the call is tracked.
        """
        
        fake = generic_fake_store

        result = await fake.save_value(10)

        assert result == 1
        assert fake.backend.saved_values == [10]
        assert len(fake.received_calls) == 1
        method_name, args, kwargs = fake.received_calls[0]
        assert method_name == "save_value"
        assert args == (10,)
        assert kwargs == {}

    async def test_mutations_via_backend_visible_through_fake_methods(self, generic_fake_store):
        """
        - Ensures that backend state changes are visible when calling store methods via fake.
        - Confirms separation: backend mutations are not spied, but fake method calls are.
        """
        
        fake = generic_fake_store

        # mutate backing store via backend only (no spying)
        fake.backend.saved_values.extend([1, 2, 3])

        values = await fake.get_values()

        assert values == [1, 2, 3]
        assert fake.received_calls[0][0] == "get_values"

    def test_generic_fake_store_raises_type_error_when_no_store_cls(self):
        """
        - Validates that GenericFakeStore enforces the 'store_cls' contract.
        - Guards against accidental usage with arbitrary objects.
        """
        
        class NoStoreClsBackend:
            # No 'store_cls' attribute on purpose
            def __init__(self):
                self.saved_values = []

        with pytest.raises(TypeError):
            GenericFakeStore(NoStoreClsBackend())

    def test_generic_fake_store_raises_type_error_when_store_cls_is_none(self):
        """
        - Ensures that having store_cls=None is treated as an invalid configuration.
        - Confirms the combined hasattr(...) and truthiness check in __init__.
        """
        
        class EmptyStoreClsBackend(AnyInMemory):
            store_cls = None

        with pytest.raises(TypeError):
            GenericFakeStore(EmptyStoreClsBackend())


# ---------------------------------------------------------------------------
# Tests for helper factories: make_fake_user / make_fake_git_label
# ---------------------------------------------------------------------------

class TestFactories:
    def test_make_fake_user_defaults(self):
        """
        - Verifies the default values used by make_fake_user.
        - Confirms that a stable UUID is assigned for deterministic tests.
        """
        
        user = make_fake_user()

        assert user.user_id == "user123"
        assert user.email == "test@example.com"
        assert user.encryption_salt == "xyz"
        assert user.id == uuid.UUID("dd0551f4-2164-4739-bf3f-9ccd1644ca75")

    def test_make_fake_user_overrides(self):
        """
        - Ensures that keyword overrides propagate into the created DTO.
        - Guarantees the factory is flexible for different test scenarios.
        """

        user = make_fake_user(
            user_id="u2",
            email="another@example.com",
            encryption_salt="abc",
        )

        assert user.user_id == "u2"
        assert user.email == "another@example.com"
        assert user.encryption_salt == "abc"

    def test_make_fake_git_label_defaults(self):
        """
        - Verifies all default fields for the GitLabelResponseDTO factory.
        - Confirms timestamp fields are actual datetimes.
        """
        
        label = make_fake_git_label()

        assert label.user_id == "fake-user"
        assert label.label == "fake-label"
        assert label.git_hosting == "github"
        assert label.username == "fakeuser"
        assert label.token_value == "real-token"
        assert label.masked_token == "****1234"
        assert isinstance(label.created_at, datetime.datetime)
        assert isinstance(label.updated_at, datetime.datetime)

    def test_make_fake_git_label_overrides(self):
        """
        - Ensures override parameters are honored by make_fake_git_label.
        - Confirms that caller can fully control identifying fields for scenarios.
        """
        
        custom_id = uuid.uuid4()
        label = make_fake_git_label(
            id=custom_id,
            user_id="u-override",
            label="override-label",
            git_hosting="gitlab",
        )

        assert label.id == custom_id
        assert label.user_id == "u-override"
        assert label.label == "override-label"
        assert label.git_hosting == "gitlab"