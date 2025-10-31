import logging
import uuid
from abc import abstractmethod
from dataclasses import asdict
from typing import Any, Dict, List, Protocol, Union

from models_src.dto.code_chunks import CodeChunksRequestDTO, CodeChunksResponseDTO
from models_src.dto.utils import TortoiseModelMapper
from models_src.models import CodeChunks
import numpy as np
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

        _ = await self.model.insert_many(objs)

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
        if not query_embeddings or not user_id or not repo_id or limit <= 0:
            return []

        # Guard: consistent dimensions
        if any(len(v) != emb_dim for v in query_embeddings):
            logging.error("Embeddings have inconsistent dimensions.")
            return []

        try:
            # Fetch all chunks for the user/repo first (or use $vectorSearch if MongoDB 7.1+)
            chunks_cursor = CodeChunks.find(
                CodeChunks.user_id == str(user_id),
                CodeChunks.repo_id == str(repo_id)
            )
            chunks = await chunks_cursor.to_list()

            results = []
            for chunk in chunks:
                sims = []
                for qvec in query_embeddings:
                    # cosine similarity
                    c_emb = np.array(chunk.embedding, dtype=float)
                    q_emb = np.array(qvec, dtype=float)
                    sim = float(np.dot(c_emb, q_emb) / (np.linalg.norm(c_emb) * np.linalg.norm(q_emb) + 1e-10))
                    sims.append(sim)

                fusion_score = sum(sims)
                max_sim = max(sims)

                results.append({
                    "id": str(chunk.id),
                    "file_name": chunk.file_name,
                    "file_path": chunk.file_path,
                    "content": chunk.content,
                    "created_at": chunk.created_at,
                    "fusion_score": fusion_score,
                    "max_sim": max_sim
                })

            # Sort by fusion_score DESC, max_sim DESC, created_at DESC
            results.sort(key=lambda x: (-x["fusion_score"], -x["max_sim"], -x["created_at"].timestamp()))
            return results[:limit]

        except Exception:
            logging.exception("Multi-query similarity search failed")
            return []