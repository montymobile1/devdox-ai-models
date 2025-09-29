import datetime
import logging
import uuid
from abc import abstractmethod
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Protocol

from tortoise import connections

from models_src.dto.code_chunks import CodeChunksRequestDTO, CodeChunksResponseDTO
from models_src.dto.utils import TortoiseModelMapper
from models_src.models import CodeChunks


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
            conn = connections.get("default")
            params = [embedding, str(user_id), str(repo_id), int(limit)]
            return await conn.execute_query_dict(sql, params)
        except Exception as e:
            logging.error(f"Similarity search failed: {e}")
            return []
