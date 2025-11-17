import datetime
import inspect
import uuid
from typing import Any, Callable, Dict, List, Tuple, Union

from models_src.dto.git_label import GitLabelResponseDTO

from models_src.dto.user import UserResponseDTO

from models_src.repositories.api_key import ApiKeyStore
from models_src.repositories.code_chunks import CodeChunksStore
from models_src.repositories.git_label import GitLabelStore
from models_src.repositories.queue_job_claim_registry import QueueProcessingRegistryStore
from models_src.repositories.repo import RepoStore
from models_src.repositories.user import UserStore


class _CallSpyMixin:
    """Collects (method_name, args, kwargs) for assertions."""

    def __init__(self) -> None:
        self.received_calls: List[Tuple[str, tuple, dict]] = []

    def _name(self, method: Callable) -> str:
        return method.__name__

    def _touch(self, method: Callable, /, *args, **kwargs) -> str:
        """Existing API: accept a callable."""
        name = self._name(method)
        self.received_calls.append((name, args, kwargs))
        return name

    def _touch_name(self, method_name: str, /, *args, **kwargs) -> str:
        """New API: accept just the method name."""
        self.received_calls.append((method_name, args, kwargs))
        return method_name


class _ExceptionPlanMixin:
    """Lets you pre-wire exceptions per method name."""

    def __init__(self) -> None:
        self._exceptions: Dict[str, Exception] = {}

    def set_exception(self, method: Callable, exc: Exception) -> None:
        self._exceptions[method.__name__] = exc

    def _maybe_raise(self, method_name: str) -> None:
        exc = self._exceptions.get(method_name)
        if exc:
            raise exc


class _StubPlanMixin(_CallSpyMixin, _ExceptionPlanMixin):
    """
    For stubs: predefine outputs per method.
    set_output(method, value_or_callable)
    """

    def __init__(self) -> None:
        _CallSpyMixin.__init__(self)
        _ExceptionPlanMixin.__init__(self)
        self._outputs: Dict[str, Any] = {}

    def set_output(self, method: Callable, output: Any) -> None:
        self._outputs[method.__name__] = output

    async def _stub(self, method: Callable, /, **kwargs):
        """Existing API: callable-based."""
        mname = self._touch(method, **kwargs)
        self._maybe_raise(mname)
        out = self._outputs[mname]

        # handle both sync/async callables safely:
        if callable(out):
            result = out(**kwargs)
            if inspect.isawaitable(result):
                return await result
            return result
        return out

    async def _stub_name(self, method_name: str, /, **kwargs):
        """New API: name-based, for dynamic wrappers."""
        mname = self._touch_name(method_name, **kwargs)
        self._maybe_raise(mname)
        out = self._outputs[mname]

        if callable(out):
            result = out(**kwargs)
            if inspect.isawaitable(result):
                return await result
            return result
        return out


class _FakeBase(_CallSpyMixin, _ExceptionPlanMixin):
    """
    For fakes: just call tracking + exceptions.
    Your class keeps its own store and accessors.
    """

    def __init__(self) -> None:
        _CallSpyMixin.__init__(self)
        _ExceptionPlanMixin.__init__(self)

    def _before(self, method: Callable, /, *args, **kwargs) -> str:
        mname = self._touch(method, *args, **kwargs)
        self._maybe_raise(mname)
        return mname

    def _before_name(self, method_name: str, /, *args, **kwargs) -> str:
        """Name-based variant, for dynamic wrappers."""
        mname = self._touch_name(method_name, *args, **kwargs)
        self._maybe_raise(mname)
        return mname


class _FakeStore(_FakeBase):
    """
    Generic fake: wraps any store and records calls BEFORE delegating.
    Works for any interface whose methods are async.
    """

    def __init__(self, base_store: Any):
        super().__init__()
        self._base_store = base_store

    def __getattr__(self, name: str):
        """
        For any attribute that doesn't exist on AsyncFakeStore itself,
        we grab it from the underlying store and wrap async callables.
        """
        target = getattr(self._base_store, name)

        # Non-callables (properties, plain attrs) are just forwarded
        if not callable(target):
            return target

        # For your stores everything is async, so we just async-wrap.
        async def wrapper(*args, __name=name, **kwargs):
            # record + maybe raise planned exception
            self._before_name(__name, *args, **kwargs)
            # delegate to underlying impl
            return await target(*args, **kwargs)

        return wrapper


class _StubStore(_StubPlanMixin):
    """
    Generic async stub: returns whatever you configured via set_output / set_exception.
    All methods are treated as async.
    """

    def __getattr__(self, name: str):
        async def wrapper(*args, __name=name, **kwargs):
            return await self._stub_name(__name, **kwargs)
        return wrapper


InMemoryStore = Union[ApiKeyStore, CodeChunksStore, GitLabelStore, QueueProcessingRegistryStore, RepoStore, UserStore]


class GenericFakeStore(_FakeStore):
    def __init__(self, base_store:InMemoryStore):
        super().__init__(base_store=base_store)


class GenericStubStore(_StubStore):
    """
    Generic stub
    """
    pass

def make_fake_user(user_id="user123", email="test@example.com", encryption_salt="xyz"):
    return UserResponseDTO(
        id=uuid.UUID("dd0551f4-2164-4739-bf3f-9ccd1644ca75"),
        user_id=user_id,
        email=email,
        encryption_salt=encryption_salt,
    )

def make_fake_git_label(**overrides) -> GitLabelResponseDTO:
    now = datetime.datetime.now()
    return GitLabelResponseDTO(
        id=overrides.get("id", uuid.uuid4()),
        user_id=overrides.get("user_id", "fake-user"),
        label=overrides.get("label", "fake-label"),
        git_hosting=overrides.get("git_hosting", "github"),
        username=overrides.get("username", "fakeuser"),
        token_value=overrides.get("token_value", "real-token"),
        masked_token=overrides.get("masked_token", "****1234"),
        created_at=overrides.get("created_at", now),
        updated_at=overrides.get("updated_at", now),
    )