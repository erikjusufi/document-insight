import json
from pathlib import Path

import faiss
import numpy as np

from app.core.settings import get_settings


class FaissService:
    def __init__(self, index_dir: str | None = None) -> None:
        settings = get_settings()
        self.index_dir = Path(index_dir or settings.faiss_index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def _index_path(self, document_id: int) -> Path:
        return self.index_dir / f"doc_{document_id}.index"

    def _meta_path(self, document_id: int) -> Path:
        return self.index_dir / f"doc_{document_id}.json"

    def save_index(self, document_id: int, vectors: list[list[float]], ids: list[int]) -> None:
        if not vectors:
            return
        dim = len(vectors[0])
        index = faiss.IndexFlatIP(dim)
        vecs = np.array(vectors, dtype="float32")
        index.add(vecs)
        faiss.write_index(index, str(self._index_path(document_id)))
        self._meta_path(document_id).write_text(json.dumps(ids))

    def load_index(self, document_id: int):
        index_path = self._index_path(document_id)
        meta_path = self._meta_path(document_id)
        if not index_path.exists() or not meta_path.exists():
            return None, []
        index = faiss.read_index(str(index_path))
        ids = json.loads(meta_path.read_text())
        return index, ids

    def search(self, document_id: int, query_vector: list[float], top_k: int) -> list[tuple[int, float]]:
        index, ids = self.load_index(document_id)
        if index is None or not ids:
            return []
        vec = np.array([query_vector], dtype="float32")
        scores, indices = index.search(vec, top_k)
        results: list[tuple[int, float]] = []
        for idx, score in zip(indices[0], scores[0]):
            if idx < 0 or idx >= len(ids):
                continue
            results.append((ids[idx], float(score)))
        return results
