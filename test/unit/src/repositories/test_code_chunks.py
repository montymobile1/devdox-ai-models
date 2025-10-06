import uuid
import pytest
from unittest.mock import MagicMock, AsyncMock

from models_src.dto.code_chunks import CodeChunksRequestDTO, CodeChunksResponseDTO
from models_src.repositories.code_chunks import TortoiseCodeChunksStore
import models_src.repositories.code_chunks as repo_mod  # to patch PgVectorConnection or class symbol when needed
from test.unit.common_test_tools.model_factories import make_codechunk
from test.unit.common_test_tools.qs_chain import make_qs_chain


class TestSave:
    @pytest.mark.asyncio
    async def test_save_returns_dto_with_real_model_instance(self, monkeypatch):
        """model.create returns a real CodeChunks instance → repo maps to DTO."""
        store = TortoiseCodeChunksStore()

        model = MagicMock()
        model.create = AsyncMock(return_value=make_codechunk(user_id="u", repo_id="r"))
        monkeypatch.setattr(store, "model", model)

        req = CodeChunksRequestDTO(
            user_id="u",
            repo_id="r",
            content="x = 1",
            file_name="file.py",
            file_path="src/file.py",
            file_size=3,
            commit_number="c1",
            embedding=None,
            metadata={"k": "v"},
        )
        dto = await store.save(req)

        assert isinstance(dto, CodeChunksResponseDTO)
        assert dto.user_id == "u" and dto.repo_id == "r"
        model.create.assert_awaited_once()


class TestBulkSave:

    @pytest.mark.asyncio
    async def test_bulk_save_builds_instances_calls_bulk_create_and_maps(self, monkeypatch):
        store = TortoiseCodeChunksStore()
        
        # Patch classmethod on the class symbol used by the store
        from models_src.repositories import code_chunks as repo_mod
        monkeypatch.setattr(repo_mod.CodeChunks, "bulk_create", AsyncMock(return_value=None))
        
        reqs = [
            CodeChunksRequestDTO(
                user_id="u",
                repo_id="r",
                content=f"chunk-{i}",
                file_name="f.py",
                file_path=f"src/{i}.py",
                file_size=1,
                commit_number="c1",
            )
            for i in range(2)
        ]
        
        out = await store.bulk_save(reqs)
        
        assert len(out) == 2
        assert all(isinstance(x, CodeChunksResponseDTO) for x in out)
        # ensure contents came through the mapper
        assert {o.content for o in out} == {"chunk-0", "chunk-1"}


class TestFindAllByRepoIdWithLimit:
    @pytest.mark.asyncio
    async def test_filters_limits_all_and_maps(self, monkeypatch):
        """Filter(repo_id), limit(N), all() → mapped DTO list."""
        store = TortoiseCodeChunksStore()

        rows = [make_codechunk(repo_id="r"), make_codechunk(repo_id="r")]
        qs = make_qs_chain(result_for_all=rows)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        out = await store.find_all_by_repo_id_with_limit("r", limit=10)
        assert len(out) == 2 and all(isinstance(x, CodeChunksResponseDTO) for x in out)

        model.filter.assert_called_once_with(repo_id="r")
        qs.limit.assert_called_once_with(10)
        qs.all.assert_awaited_once()


class TestGetRepoFileChunks:
    @pytest.mark.asyncio
    async def test_happy_path_filters_orders_and_values(self, monkeypatch):
        """Filter by (user_id, repo_id, file_name__icontains), order desc, values('content')."""
        store = TortoiseCodeChunksStore()

        out_rows = [{"content": "A"}, {"content": "B"}]
        qs = make_qs_chain(result_for_values=out_rows)
        model = MagicMock()
        model.filter.return_value = qs
        monkeypatch.setattr(store, "model", model)

        out = await store.get_repo_file_chunks(user_id="u", repo_id="r", file_name="readme")
        assert out == out_rows

        model.filter.assert_called_once_with(
            file_name__icontains="readme", user_id="u", repo_id="r"
        )
        qs.order_by.assert_called_once_with("-created_at")
        qs.values.assert_awaited_once_with("content")

    @pytest.mark.asyncio
    async def test_exception_returns_empty_list_and_logs(self, monkeypatch):
        """If anything inside try fails, function logs and returns []."""
        store = TortoiseCodeChunksStore()

        model = MagicMock()
        model.filter.side_effect = Exception("boom")
        monkeypatch.setattr(store, "model", model)

        logged = {}
        def fake_exc(msg):
            logged["msg"] = msg
        monkeypatch.setattr(repo_mod.logging, "exception", fake_exc)

        out = await store.get_repo_file_chunks(user_id="u", repo_id="r", file_name="readme")
        assert out == []
        assert "get_repo_file_chunks" in logged.get("msg", "")

class TestGetUserRepoChunksMulti:
    @pytest.mark.asyncio
    async def test_executes_sql_via_fake_pgvector_connection(self, monkeypatch):
        """
        We fake PgVectorConnection; assert the param ordering matches:
        [*query_embeddings, user_id, repo_id, limit]
        """
        store = TortoiseCodeChunksStore()

        captured = {"sql": None, "params": None}
        rows = [
            {"id": uuid.uuid4(), "content": "x", "fusion_score": 1.23, "max_sim": 0.9, "created_at": None},
            {"id": uuid.uuid4(), "content": "y", "fusion_score": 1.10, "max_sim": 0.8, "created_at": None},
        ]

        class FakeConn:
            def __init__(self, alias): self.alias = alias
            async def __aenter__(self): return self
            async def __aexit__(self, exc_type, exc, tb): return False
            async def fetch(self, sql, *params):
                captured["sql"] = sql
                captured["params"] = params
                return rows

        monkeypatch.setattr(repo_mod, "PgVectorConnection", FakeConn)

        emb1 = [0.0] * 768
        emb2 = [0.1] * 768
        out = await store.get_user_repo_chunks_multi(
            user_id="u",
            repo_id="r",
            query_embeddings=[emb1, emb2],
            emb_dim=768,
            limit=5,
        )
        assert out == rows

        # Params layout: [emb1, emb2, "u", "r", 5]
        assert captured["params"][0] is emb1
        assert captured["params"][1] is emb2
        assert captured["params"][2] == "u"
        assert captured["params"][3] == "r"
        assert captured["params"][4] == 5

        # (Optional) Sanity check sql contains the CTEs we expect
        assert "WITH queries(qvec) AS" in captured["sql"]
        assert "CROSS JOIN queries" in captured["sql"]
        assert "SUM(sim)        AS fusion_score" in captured["sql"]
    
    @pytest.mark.asyncio
    async def test_rejects_bad_inputs_multi(self):
        store = TortoiseCodeChunksStore()
        e1 = [0.0] * 768
        e2 = [0.1] * 768

        # missing repo/user/limit <= 0 / empty embeddings
        assert await store.get_user_repo_chunks_multi(user_id="", repo_id="r", query_embeddings=[e1], emb_dim=768, limit=5) == []
        assert await store.get_user_repo_chunks_multi(user_id="u", repo_id="", query_embeddings=[e1], emb_dim=768, limit=5) == []
        assert await store.get_user_repo_chunks_multi(user_id="u", repo_id="r", query_embeddings=[e1], emb_dim=768, limit=0) == []
        assert await store.get_user_repo_chunks_multi(user_id="u", repo_id="r", query_embeddings=[], emb_dim=768, limit=5) == []

        # inconsistent dims
        bad = [0.0] * 10
        assert await store.get_user_repo_chunks_multi(user_id="u", repo_id="r", query_embeddings=[e1, bad], emb_dim=768, limit=5) == []
    
    @pytest.mark.asyncio
    async def test_multi_failure_logs_error_and_returns_empty_list(self, monkeypatch):
        store = TortoiseCodeChunksStore()

        class BoomConn:
            def __init__(self, alias): ...
            async def __aenter__(self): return self
            async def __aexit__(self, exc_type, exc, tb): return False
            async def fetch(self, sql, *params):
                raise RuntimeError("db down")

        monkeypatch.setattr(repo_mod, "PgVectorConnection", BoomConn)

        logged = {"msg": None}
        def fake_exc(msg):
            logged["msg"] = msg
        monkeypatch.setattr(repo_mod.logging, "exception", fake_exc)

        emb1 = [0.0] * 768
        out = await store.get_user_repo_chunks_multi(
            user_id="u", repo_id="r", query_embeddings=[emb1], emb_dim=768, limit=3
        )
        assert out == []
        assert "Multi-query similarity search failed" in (logged["msg"] or "")
