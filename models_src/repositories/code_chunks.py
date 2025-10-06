import logging
import uuid
from abc import abstractmethod
from dataclasses import asdict
from typing import Any, Dict, List, Protocol

from models_src.dto.code_chunks import CodeChunksRequestDTO, CodeChunksResponseDTO
from models_src.dto.utils import TortoiseModelMapper
from models_src.models import CodeChunks
from models_src.models.db import PgVectorConnection


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
    
    async def similarity_search(
            self,
            embedding: List[float],
            user_id: str | uuid.UUID,
            repo_id: str | uuid.UUID,
            limit: int = 5,
    ) -> List[Dict[str, Any]]: ...
    
    @abstractmethod
    async def get_user_repo_chunks(
            self,user_id: str | uuid.UUID , repo_id: str | uuid.UUID, query_embedding: List[float], limit: int = None
    ) -> List[dict]: ...


class TortoiseCodeChunksStore(ICodeChunksStore):

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
        try:
            result = await self.model.filter( file_name__icontains=file_name,  user_id=user_id, repo_id=repo_id).order_by("-created_at").values("content")
            return result
        except Exception:
            logging.exception(f"{self.get_repo_file_chunks.__name__} failed")
            return []  # Return empty list on error
    
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
        if not repo_id or not user_id or limit <= 0 or not query_embeddings:
            return []

        # Guard: consistent dimensions
        if any(len(v) != emb_dim for v in query_embeddings):
            logging.error("Embeddings have inconsistent dimensions.")
            return []

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
    
    async def get_user_repo_chunks(
        self,
        user_id: str | uuid.UUID,
        repo_id: str | uuid.UUID,
        query_embedding: List[float],
        limit: int = 5,
    ) -> List[Dict]:
        return await self.similarity_search(
            embedding=query_embedding,
            user_id=user_id,
            repo_id=repo_id,
            limit=limit,
        )

    async def similarity_search(
        self,
        embedding: List[float],
        user_id: str | uuid.UUID,
        repo_id: str | uuid.UUID,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:

        if not repo_id or not user_id or limit <= 0:
            return []

        if not embedding or len(embedding) != 768:
            logging.error(
                f"Embedding dim mismatch: got {0 if not embedding else len(embedding)}, expected 768"
            )
            return []

        sql = """
            WITH ranked AS (
                SELECT
                    c.*,
                    1 - (c.embedding <=> $1::vector(768)) AS score
                FROM public.code_chunks c
                WHERE c.user_id = $2
                  AND c.repo_id = $3
            )
            SELECT *
            FROM ranked
            ORDER BY score DESC, created_at DESC
            LIMIT $4;
        """
        try:
            async with PgVectorConnection("default") as conn:
                params = (embedding, str(user_id), str(repo_id), int(limit))
                rows = await conn.fetch(sql, *params)
                return [dict(r) for r in rows]
        except Exception as e:
            logging.error(f"Similarity search failed: {e}")
            return []
