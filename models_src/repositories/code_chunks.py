import datetime
import logging
import math
import uuid
from abc import abstractmethod
from dataclasses import asdict
from typing import Any, Dict, List, Protocol

import numpy as np

from models_src.dto.code_chunks import CodeChunksRequestDTO, CodeChunksResponseDTO
from models_src.dto.utils import BeanieModelMapper, TortoiseModelMapper
from models_src.models.code_chunks import CodeChunks
from models_src.models.code_chunks_document import CodeChunks as CodeChunksDocument, CodeChunksProjection, \
    CodeChunksSearchProjection, EMBED_DIM
from models_src.models.db import PgVectorConnection


# --------------------------------------------------
# Specification
# --------------------------------------------------

class ICodeChunksStore(Protocol):
    
    @abstractmethod
    async def save(
            self, create_model: CodeChunksRequestDTO
    ) -> CodeChunksResponseDTO: ...
    
    @abstractmethod
    async def bulk_save(self, create_model: list[CodeChunksRequestDTO]) -> List[CodeChunksResponseDTO]: ...
    
    @abstractmethod
    async def find_all_by_repo_id_with_limit(
            self, repo_id: str, limit: int = 100
    ) -> List[CodeChunksResponseDTO]: ...
    
    @abstractmethod
    async def get_repo_file_chunks(self,  user_id : str | uuid.UUID , repo_id: str | uuid.UUID,  file_name:str="readme") -> List[dict]: ...
    
    @abstractmethod
    async def get_user_repo_chunks_multi(
            self,
            user_id: str | uuid.UUID,
            repo_id: str | uuid.UUID,
            query_embeddings: List[List[float]],
            emb_dim: int,
            limit: int = 10,
    ) -> List[Dict[str, Any]]: ...

# --------------------------------------------------
# Storage Backend
# --------------------------------------------------

class TortoiseCodeChunksBackend(ICodeChunksStore):
    
    model = CodeChunks
    model_mapper = TortoiseModelMapper
    
    def __init__(self):
        """
        Have to add this as an empty __init__ to override it, because when using it with Depends(),
        FastAPI dependency mechanism will automatically assume its
        ```
        def __init__(self, *args, **kwargs):
                pass
        ```
        Causing unneeded behavior.
        """
        pass
    
    async def save(self, create_model: CodeChunksRequestDTO) -> CodeChunksResponseDTO:
        data = await self.model.create(**asdict(create_model))
        return self.model_mapper.map_model_to_dataclass(data, CodeChunksResponseDTO)
    
    async def bulk_save(self, create_model: list[CodeChunksRequestDTO]) -> List[CodeChunksResponseDTO]:
        objs = [
            self.model(**asdict(r))
            for r in create_model
        ]
        
        _ = await self.model.bulk_create(objs, batch_size=1000)
        
        return self.model_mapper.map_models_to_dataclasses_list(objs, CodeChunksResponseDTO)
    
    async def find_all_by_repo_id_with_limit(
            self, repo_id: str, limit: int = 100
    ) -> List[CodeChunksResponseDTO]:
        raw_data = await self.model.filter(repo_id=repo_id).limit(limit).all()
        return self.model_mapper.map_models_to_dataclasses_list(
            raw_data, CodeChunksResponseDTO
        )
    
    async def get_repo_file_chunks(self,  user_id : str | uuid.UUID , repo_id: str | uuid.UUID,  file_name:str="readme") -> List[dict]:
        """Return chunks of a specific file"""
        result = await self.model.filter( file_name__icontains=file_name,  user_id=user_id, repo_id=repo_id).order_by("-created_at").values("content")
        return result

    
    async def get_user_repo_chunks_multi(
            self,
            user_id: str | uuid.UUID,
            repo_id: str | uuid.UUID,
            query_embeddings: List[List[float]],
            emb_dim: int,
            limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Multi-query:
        - Accepts multiple query vectors.
        - Computes similarity per (chunk, query).
        - Fuses per-chunk via SUM(sim) as fusion_score.
        - Orders by fusion_score, then max_sim, then created_at.
        """

        # Build VALUES placeholders for each query vector: ($1::vector(dim)), ($2::vector(dim)), ...
        n = len(query_embeddings)
        values_sql = ", ".join(f"(${i+1}::vector({emb_dim}))" for i in range(n))
        
        # Next placeholders for user_id, repo_id, limit:
        p_user   = n + 1
        p_repo   = n + 2
        p_limit  = n + 3
        
        sql = f"""
            WITH queries(qvec) AS (
              VALUES {values_sql}
            ),
            scored AS (
              SELECT
                c.id,
                c.created_at,
                1 - (c.embedding <=> q.qvec) AS sim
              FROM public.code_chunks AS c
              CROSS JOIN queries AS q
              WHERE c.user_id = ${p_user}
                AND c.repo_id = ${p_repo}
                -- OPTIONAL, ENABLE IF YOU WANT TO REMOVE THE LOW RANKED ONES
                -- AND (1 - (c.embedding <=> q.qvec)) >= 0.20
            ),
            agg AS (
              SELECT
                id,
                MAX(created_at) AS created_at,
                SUM(sim)        AS fusion_score,
                MAX(sim)        AS max_sim
              FROM scored
              GROUP BY id
            )
            SELECT
              c.id,
              c.file_name,
              c.file_path,
              c.content,
              a.created_at,
              a.fusion_score,
              a.max_sim
            FROM agg a
            JOIN public.code_chunks c ON c.id = a.id
              -- for defensive clarity:
              AND c.user_id = ${p_user}
              AND c.repo_id = ${p_repo}
            ORDER BY a.fusion_score DESC, a.max_sim DESC, a.created_at DESC
            LIMIT ${p_limit};
        """
        try:
            async with PgVectorConnection("default") as conn:
                params = [*query_embeddings, str(user_id), str(repo_id), int(limit)]
                rows = await conn.fetch(sql, *params)
                return [dict(r) for r in rows]
        except Exception:
            logging.exception("Multi-query similarity search failed")
            return []

class BeanieCodeChunksBackend(ICodeChunksStore):
    """
    Beanie implementation for ICodeChunksStore (basic methods).
    """

    model = CodeChunksDocument
    model_mapper = BeanieModelMapper

    async def save(self, create_model: CodeChunksRequestDTO) -> CodeChunksResponseDTO:
        """
        Persist a single chunk. Pydantic validation (e.g., embedding length) happens
        when instantiating the Document.
        """
        doc = self.model(**asdict(create_model))
        saved = await doc.create()
        return self.model_mapper.map_document_to_dataclass(saved, CodeChunksResponseDTO)

    async def bulk_save(self, create_model: list[CodeChunksRequestDTO]) -> List[CodeChunksResponseDTO]:
        """
        Insert many in one go. Returns DTOs for the inserted docs.
        """
    
        docs = [self.model(**asdict(r)) for r in create_model]
        
        await self.model.insert_many(docs)
        return self.model_mapper.map_documents_to_dataclasses_list(docs, CodeChunksResponseDTO)
        

    async def find_all_by_repo_id_with_limit(
        self, repo_id: str, limit: int = 100
    ) -> List[CodeChunksResponseDTO]:
        """
        Return newest-first by created_at, limited.
        """
        docs = await (
            self.model.find(self.model.repo_id == str(repo_id))
            .sort(-self.model.created_at)
            .limit(int(limit))
            .to_list()
        )
        return self.model_mapper.map_documents_to_dataclasses_list(docs, CodeChunksResponseDTO)
    
    async def get_repo_file_chunks(
            self,
            user_id: str | uuid.UUID,
            repo_id: str | uuid.UUID,
            file_name: str = "readme",
    ) -> List[dict]:
        """
        Return only {"content": ...} dicts for a specific user's repo,
        case-insensitive contains on file_name. Newest first.
        """
        uid = str(user_id)
        rid = str(repo_id)
        if not uid or not rid or not file_name:
            return []
        
        # Case-insensitive substring match on file_name
        docs = await (
            self.model.find(
                {
                    "user_id": uid,
                    "repo_id": rid,
                    "file_name": {"$regex": file_name, "$options": "i"},
                }
            )
            .sort(-self.model.created_at)
            .project(CodeChunksProjection).to_list()
        )
        
        list_of_dict_docs = [val.model_dump() for val in docs]
        
        return list_of_dict_docs

    
    async def get_user_repo_chunks_multi(
            self,
            user_id: str | uuid.UUID,
            repo_id: str | uuid.UUID,
            query_embeddings: List[List[float]],
            emb_dim: int,
            limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Multi-query search (Python/NumPy):
          - Normalize queries once (unit vectors with zero-protection).
          - For each chunk, compute dot against each unit query (no chunk normalization).
          - fusion_score = SUM of sims; max_sim = max of sims.
          - Sort: fusion_score desc, then max_sim desc, then created_at desc.
        """
        
        # Normalize queries (protect zeros with isclose)
        EPS = 1e-12
        queries = np.asarray(query_embeddings, dtype=np.float32)  # (Q, D)
        q_norms = np.linalg.norm(queries, axis=1)                 # (Q,)
        q_norms[np.isclose(q_norms, 0.0, rtol=1e-9, atol=1e-9)] = 1.0
        queries_unit = queries / q_norms[:, None]                 # (Q, D)
        
        # Fetch only the fields we need (bypasses full model validation)
        docs = await (
            self.model
            .find(self.model.user_id == str(user_id), self.model.repo_id == str(repo_id))
            .project(CodeChunksSearchProjection)
            .to_list()
        )
        
        ranked: List[Dict[str, Any]] = []
        for doc in docs:
            emb = doc.embedding
            if not emb or len(emb) != emb_dim:
                continue
            
            chunk_vec = np.asarray(emb, dtype=np.float32)  # (D,)
            chunk_norm = float(np.linalg.norm(chunk_vec))
            if chunk_norm <= EPS:
                # zero vector -> meaningless similarity
                continue
            
            # Dot against unit queries (no chunk normalization)
            sims = chunk_vec @ queries_unit.T  # (Q,)
            
            fusion_score = float(sims.sum())
            max_sim = float(sims.max()) if sims.size else 0.0
            
            ranked.append({
                "id": doc.id,  # UUID
                "file_name": doc.file_name,
                "file_path": doc.file_path,
                "content": doc.content,
                "created_at": doc.created_at,
                "fusion_score": fusion_score,
                "max_sim": max_sim,
            })
        
        ranked.sort(key=lambda r: (r["fusion_score"], r["max_sim"], r["created_at"]), reverse=True)
        return ranked[: int(limit)]

ZERO_NORM_TOLERANCE = 1e-12

class InMemoryCodeChunksBackend(ICodeChunksStore):
    
    def __init__(self):
        self.data_store: List[CodeChunksResponseDTO] = []
        self.total_count = 0
    
    def __get_data_store(self):
        return self.data_store
    
    def __set_data_store(self, data: List[CodeChunksResponseDTO]):
        self.data_store = data
        self.total_count = len(self.data_store)
    
    def set_fake_data(self, fake_data: list[CodeChunksResponseDTO]):
        self.data_store.extend(fake_data)
        self.total_count = len(self.data_store)
    
    async def save(self, create_model: CodeChunksRequestDTO) -> CodeChunksResponseDTO:
        response = CodeChunksResponseDTO(**asdict(create_model))
        response.id = uuid.uuid4()
        response.created_at = datetime.datetime.now(datetime.timezone.utc)
        
        self.data_store.append(response)
        self.total_count = len(self.data_store)
        
        return response
    
    async def bulk_save(self, create_model: list[CodeChunksRequestDTO]) -> List[CodeChunksResponseDTO]:
        response = []
        for model in create_model:
            v = CodeChunksResponseDTO(**asdict(model))
            v.id = uuid.uuid4()
            v.created_at = datetime.datetime.now(datetime.timezone.utc)
            
            response.append(v)
        
        self.data_store.extend(response)
        self.total_count = len(self.data_store)
        
        return response
    
    async def find_all_by_repo_id_with_limit(
            self, repo_id: str, limit: int = 100
    ) -> List[CodeChunksResponseDTO]:
        data = self.__get_data_store()
        
        final_result = []
        index_limit_counter = 1
        for index, result in enumerate(data):
            if index_limit_counter > limit:
                break
            
            if result.repo_id == repo_id:
                final_result.append(result)
                index_limit_counter += 1
        
        return final_result
    
    async def get_repo_file_chunks(self, user_id: str | uuid.UUID, repo_id: str | uuid.UUID,
                                   file_name: str = "readme") -> List[dict]:

        all_data = self.__get_data_store()
        sorted_data = sorted(all_data, key=lambda k: k.created_at, reverse=True)
        returned_data: List[dict] = []
        for data in sorted_data:
            if (
                    str(user_id) == str(data.user_id)
                    and str(repo_id) == str(data.repo_id)
                    and file_name.lower() in data.file_name.lower()
            ):
                returned_data.append({"content": data.content})
        return returned_data
    
    def calculate_score(self, vec1: List[float] | None, vec2: List[float] | None) -> float:
        """
        Attempts to mimic the postgresql cosine distance calculation the "<=>" part
        """
        
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return float("-inf")  # push invalid rows to the bottom
        n1 = math.sqrt(sum(x * x for x in vec1))
        n2 = math.sqrt(sum(y * y for y in vec2))
        if n1 < ZERO_NORM_TOLERANCE or n2 < ZERO_NORM_TOLERANCE:
            return float("-inf")
        sim = sum(a * b for a, b in zip(vec1, vec2)) / (n1 * n2)
        sim = max(-1.0, min(1.0, sim))  # clamp for numerical safety
        return sim  # score == cosine similarity
    
    async def get_user_repo_chunks_multi(
            self,
            user_id: str | uuid.UUID,
            repo_id: str | uuid.UUID,
            query_embeddings: List[List[float]],
            emb_dim: int,
            limit: int = 10,
    ) -> List[Dict[str, Any]]:

        out: List[Dict[str, Any]] = []
        for row in self.__get_data_store():
            if str(row.user_id) != str(user_id) or str(row.repo_id) != str(repo_id):
                continue
            
            sims = [self.calculate_score(getattr(row, "embedding", None), qv) for qv in query_embeddings]
            valid_sims = [s for s in sims if s != float("-inf")]
            if valid_sims:
                fusion_score = sum(valid_sims)
                max_sim = max(valid_sims)
            else:
                fusion_score = float("-inf")
                max_sim = float("-inf")
            
            out.append({
                "id": row.id,
                "file_name": row.file_name,
                "file_path": row.file_path,
                "content": row.content,
                "created_at": row.created_at,
                "fusion_score": fusion_score,
                "max_sim": max_sim,
            })
        
        default_dt = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
        out.sort(
            key=lambda r: (
                r.get("fusion_score", float("-inf")),
                r.get("max_sim", float("-inf")),
                r.get("created_at", default_dt),
            ),
            reverse=True,
        )
        return out[: max(1, int(limit))]


# --------------------------------------------------
# Base Store
# --------------------------------------------------

class CodeChunksStore(ICodeChunksStore):
    
    def __init__(self, storage_backend:ICodeChunksStore):
        self._storage_backend = storage_backend
    
    async def save(self, create_model: CodeChunksRequestDTO) -> CodeChunksResponseDTO:
        return await self._storage_backend.save(create_model=create_model)
    
    async def bulk_save(self, create_model: list[CodeChunksRequestDTO]) -> List[CodeChunksResponseDTO]:
        if not create_model:
            return []
        
        return await self._storage_backend.bulk_save(create_model=create_model)
    
    async def find_all_by_repo_id_with_limit(
            self, repo_id: str, limit: int = 100
    ) -> List[CodeChunksResponseDTO]:
        if not repo_id or not repo_id.strip() or limit <= 0:
            return []
        
        return await self._storage_backend.find_all_by_repo_id_with_limit(repo_id=repo_id, limit=limit)
    
    async def get_repo_file_chunks(self,  user_id : str | uuid.UUID , repo_id: str | uuid.UUID,  file_name:str="readme") -> List[dict]:
        
        try:
            return await self._storage_backend.get_repo_file_chunks(user_id=user_id, repo_id=repo_id, file_name=file_name)
        except Exception:
            logging.exception(f"{self.get_repo_file_chunks.__name__} failed")
            return []
        
    
    async def get_user_repo_chunks_multi(
            self,
            user_id: str | uuid.UUID,
            repo_id: str | uuid.UUID,
            query_embeddings: List[List[float]],
            emb_dim: int,
            limit: int = 10,
    ) -> List[Dict[str, Any]]:
        if not query_embeddings or not user_id or (not isinstance(user_id, uuid.UUID) and not user_id.strip()) or not repo_id or (not isinstance(repo_id, uuid.UUID) and not repo_id.strip()) or limit <= 0:
            return []
        
        # dimension guard (match your behavior)
        if any(len(v) != emb_dim for v in query_embeddings):
            logging.error("Embeddings have inconsistent dimensions.")
            return []
        
        return await self._storage_backend.get_user_repo_chunks_multi(user_id=user_id, repo_id=repo_id, query_embeddings=query_embeddings, emb_dim=emb_dim, limit=limit)

# --------------------------------------------------
# Factory
# --------------------------------------------------

def get_active_code_chunks_store():
    return CodeChunksStore(storage_backend=BeanieCodeChunksBackend())