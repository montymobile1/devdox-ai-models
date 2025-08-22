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
            return 1.0
        # norms
        n1 = math.sqrt(sum(x * x for x in vec1))
        n2 = math.sqrt(sum(y * y for y in vec2))
        
        if n1 < ZERO_NORM_TOLERANCE or n2 < ZERO_NORM_TOLERANCE:
            return 1.0
        
        sim = sum(a * b for a, b in zip(vec1, vec2)) / (n1 * n2)

        distance = 1 - sim

        score = 1 - distance  # same as SQL: 1 - (embedding <=> $1)

        return score

    async def get_user_repo_chunks(
        self,
        user_id: str | uuid.UUID,
        repo_id: str | uuid.UUID,
        query_embedding: List[float],
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        self._before(self.get_user_repo_chunks, user_id=user_id, repo_id=repo_id, query_embedding=query_embedding, limit=limit)

        return await self.similarity_search(
            embedding=query_embedding, user_id=user_id, repo_id=repo_id, limit=limit
        )

    async def similarity_search(
        self,
        embedding: List[float],
        user_id: str | uuid.UUID,
        repo_id: str | uuid.UUID,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        self._before(
            self.similarity_search,
            embedding=embedding,
            user_id=user_id,
            repo_id=repo_id,
            limit=limit,
        )

        if not repo_id or not user_id or limit <= 0:
            return []
        if not embedding or len(embedding) != EMBED_DIM:
            return []

        results: List[Dict[str, Any]] = []
        for row in self.__get_data_store():
            if str(row.user_id) != str(user_id) or str(row.repo_id) != str(repo_id):
                continue
            # row.embedding should be List[float] (length EMBED_DIM) or None
            score = self.calculate_score(getattr(row, "embedding", None), embedding)
            row_dict = asdict(row)
            out = dict(row_dict)
            out["score"] = score
            results.append(out)

        # ORDER BY score DESC, created_at DESC
        results.sort(
            key=lambda r: (r.get("score", float("-inf")), r.get("created_at", datetime.datetime.min)),
            reverse=True,
        )
        return results[: max(1, int(limit))]


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
    
    async def get_user_repo_chunks(
        self,
        user_id: str | uuid.UUID,
        repo_id: str | uuid.UUID,
        query_embedding: List[float],
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        return await self._stub(
            self.get_user_repo_chunks, user_id=user_id, repo_id=repo_id, query_embedding=query_embedding, limit=limit
        )

    async def similarity_search(
        self,
        embedding: List[float],
        user_id: str | uuid.UUID,
        repo_id: str | uuid.UUID,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        return await self._stub(
            self.similarity_search, embedding=embedding, user_id=user_id, repo_id=repo_id, limit=limit
        )
