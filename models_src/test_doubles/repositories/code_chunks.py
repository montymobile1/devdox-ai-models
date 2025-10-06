import datetime
import math
import uuid
from dataclasses import asdict
from typing import Any, Dict, List
from uuid import uuid4

from models_src.dto.code_chunks import CodeChunksRequestDTO, CodeChunksResponseDTO
from models_src.repositories.code_chunks import ICodeChunksStore
from models_src.test_doubles.repositories.bases import FakeBase, StubPlanMixin

EMBED_DIM = 768
ZERO_NORM_TOLERANCE = 1e-12

class FakeCodeChunksStore(FakeBase, ICodeChunksStore):

    def __init__(self):
        super().__init__()
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

        self._before(self.save, create_model=create_model)

        response = CodeChunksResponseDTO(**asdict(create_model))
        response.id = uuid4()
        response.created_at = datetime.datetime.now(datetime.timezone.utc)

        self.data_store.append(response)
        self.total_count = len(self.data_store)

        return response

    async def bulk_save(self, create_model: list[CodeChunksRequestDTO]) -> List[CodeChunksResponseDTO]:
        self._before(self.bulk_save, create_model=create_model)

        response = []
        for model in create_model:
            v = CodeChunksResponseDTO(**asdict(model))
            v.id = uuid4()
            v.created_at = datetime.datetime.now(datetime.timezone.utc)

            response.append(v)

        self.data_store.extend(response)
        self.total_count = len(self.data_store)

        return response

    async def find_all_by_repo_id_with_limit(
        self, repo_id: str, limit: int = 100
    ) -> List[CodeChunksResponseDTO]:
        self._before(self.find_all_by_repo_id_with_limit, repo_id=repo_id, limit=limit)

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

        self._before(self.get_repo_file_chunks, user_id=user_id, repo_id=repo_id)

        all_data = self.__get_data_store()
        sorted_data = sorted(all_data, key=lambda k: k.created_at, reverse=True)
        returned_data: List[dict] = []
        for data in sorted_data:
            if (
                str(user_id) == str(data.user_id)
                and str(repo_id) == str(data.repo_id)
                and file_name in data.file_name
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
        self._before(
            self.get_user_repo_chunks_multi,
            user_id=user_id, repo_id=repo_id,
            query_embeddings=query_embeddings, emb_dim=emb_dim, limit=limit
        )
        
        if not repo_id or not user_id or limit <= 0 or not query_embeddings:
            return []
        if any(len(v) != emb_dim for v in query_embeddings):
            return []
        if emb_dim != EMBED_DIM:  # keep fake strict to catch mismatches in tests
            return []
        
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


class StubCodeChunksStore(StubPlanMixin, ICodeChunksStore):

    def __init__(self):
        super().__init__()

    async def save(self, create_model: CodeChunksRequestDTO) -> CodeChunksResponseDTO:
        return await self._stub(self.save, create_model=create_model)

    async def find_all_by_repo_id_with_limit(
        self, repo_id: str, limit: int = 100
    ) -> List[CodeChunksResponseDTO]:
        return await self._stub(
            self.find_all_by_repo_id_with_limit, repo_id=repo_id, limit=limit
        )

    async def get_repo_file_chunks(self, user_id: str | uuid.UUID, repo_id: str | uuid.UUID,
                                   file_name: str = "readme") -> List[dict]:
        return await self._stub(
            self.get_repo_file_chunks, user_id=user_id, repo_id=repo_id, file_name=file_name
        )
    
    async def get_user_repo_chunks_multi(
            self,
            user_id: str | uuid.UUID,
            repo_id: str | uuid.UUID,
            query_embeddings: List[List[float]],
            emb_dim: int,
            limit: int = 10,
    ) -> List[Dict[str, Any]]:
        return await self._stub(
            self.get_user_repo_chunks_multi,
            user_id=user_id, repo_id=repo_id, query_embeddings=query_embeddings, emb_dim=emb_dim, limit=limit
        )

    async def bulk_save(
        self, create_model: list[CodeChunksRequestDTO]
    ) -> List[CodeChunksResponseDTO]:
        return await self._stub(
            self.bulk_save,
            create_model=create_model
        )
