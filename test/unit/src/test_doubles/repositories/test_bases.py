import pytest

from models_src.test_doubles.repositories.bases import (
    CallSpyMixin,
    ExceptionPlanMixin,
    FakeBase, StubPlanMixin,
)


class TestCallSpyMixin:
    def test_call_spy_records_multiple_calls(self, ):
        class MySpy(CallSpyMixin):
            def act(self, x): return self._touch(self.act, x)
    
        spy = MySpy()
        spy.act(1)
        spy.act(2)
        assert spy.received_calls == [("act", (1,), {}), ("act", (2,), {})]
    
    def test_call_spy_with_kwargs(self, ):
        class MySpy(CallSpyMixin):
            def run(self, **kwargs): return self._touch(self.run, **kwargs)
    
        spy = MySpy()
        spy.run(x=10, y=20)
        assert spy.received_calls == [("run", (), {"x": 10, "y": 20})]
    
    def test_call_spy_args_and_name(self):
        class MySpy(CallSpyMixin):
            def op(self, a, b): return self._touch(self.op, a, b)
    
        spy = MySpy()
        spy.op(9, 8)
        name, args, kwargs = spy.received_calls[0]
        assert name == "op"
        assert args == (9, 8)
        assert kwargs == {}

class TestExceptionPlanMixin:
    def test_exception_plan_set_and_raises(self):
        class MyMixin(ExceptionPlanMixin):
            def trigger(self): self._maybe_raise("trigger")

        m = MyMixin()
        m.set_exception(MyMixin.trigger, ValueError("explode"))

        with pytest.raises(ValueError, match="explode"):
            m.trigger()

    def test_exception_plan_no_exception(self):
        class MyMixin(ExceptionPlanMixin):
            def trigger(self): return self._maybe_raise("trigger") or "ok"

        m = MyMixin()
        assert m.trigger() == "ok"

    def test_exception_plan_unknown_method(self):
        m = ExceptionPlanMixin()
        m.set_exception(lambda: None, KeyError("bad"))
        assert m._exceptions.get("<lambda>").args[0] == "bad"

    def test_exception_plan_overwrite_existing(self):
        class M(ExceptionPlanMixin):
            def do(self):
                self._maybe_raise("do")

        m = M()
        m.set_exception(M.do, ValueError("first"))
        m.set_exception(M.do, KeyError("second"))

        with pytest.raises(KeyError, match="second"):
            m.do()


class TestStubPlanMixin:
    @pytest.mark.asyncio
    async def test_stub_plan_static_output(self):
        class Stub(StubPlanMixin):
            async def fetch(self): return await self._stub(self.fetch)

        s = Stub()
        s.set_output(Stub.fetch, {"data": 123})
        result = await s.fetch()
        assert result == {"data": 123}
        assert s.received_calls == [("fetch", (), {})]

    @pytest.mark.asyncio
    async def test_stub_plan_callable_output(self):
        class Stub(StubPlanMixin):
            async def fetch(self, *, key): return await self._stub(self.fetch, key=key)

        s = Stub()
        s.set_output(Stub.fetch, lambda *, key: {"echo": key})
        result = await s.fetch(key="abc")
        assert result == {"echo": "abc"}

    @pytest.mark.asyncio
    async def test_stub_plan_output_missing(self):
        class Stub(StubPlanMixin):
            async def get(self): return await self._stub(self.get)

        s = Stub()
        with pytest.raises(KeyError):
            await s.get()

    @pytest.mark.asyncio
    async def test_stub_plan_callable_output_raises(self):
        class Stub(StubPlanMixin):
            async def boom(self): return await self._stub(self.boom)

        async def fail(): raise RuntimeError("bad lambda")

        s = Stub()
        s.set_output(Stub.boom, fail)

        with pytest.raises(RuntimeError, match="bad lambda"):
            await s.boom()

    @pytest.mark.asyncio
    async def test_stub_plan_exception_then_output(self):
        class Stub(StubPlanMixin):
            async def ping(self): return await self._stub(self.ping)

        s = Stub()
        s.set_exception(Stub.ping, ValueError("fail"))
        s.set_output(Stub.ping, "unreachable")

        with pytest.raises(ValueError, match="fail"):
            await s.ping()

    @pytest.mark.asyncio
    async def test_stub_plan_mutation_like_callable_returns_none(self):
        class Stub(StubPlanMixin):
            async def x(self):
                return await self._stub(self.x)

        async def null():
            return None

        s = Stub()
        s.set_output(Stub.x, null)
        result = await s.x()
        assert result is None


class TestFakeBase:
    def test_fake_base_tracks_and_raises(self):
        class Fake(FakeBase):
            def call(self, a): return self._before(self.call, a)
    
        f = Fake()
        f.set_exception(Fake.call, RuntimeError("nope"))
    
        with pytest.raises(RuntimeError, match="nope"):
            f.call(9)
    
        assert f.received_calls == [("call", (9,), {})]
    
    def test_fake_base_no_exception(self):
        class Fake(FakeBase):
            def go(self, x): return self._before(self.go, x)
    
        f = Fake()
        assert f.go(42) == "go"
        assert f.received_calls == [("go", (42,), {})]
