from sentence_transformers import SentenceTransformer

from app.core.settings import get_settings
from app.services.embedding_cache import EmbeddingCache


class EmbeddingService:
    def __init__(self, model_name: str | None = None, cache: EmbeddingCache | None = None) -> None:
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model_name
        self._model: SentenceTransformer | None = None
        self._cache = cache or EmbeddingCache()

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        missing: list[str] = []
        missing_indices: list[int] = []

        for idx, text in enumerate(texts):
            cached = self._safe_get(text)
            if cached is None:
                missing.append(text)
                missing_indices.append(idx)
                embeddings.append([])
            else:
                embeddings.append(cached)

        if missing:
            model = self._get_model()
            computed_raw = model.encode(missing, normalize_embeddings=True)
            computed = computed_raw.tolist() if hasattr(computed_raw, "tolist") else list(computed_raw)
            for text, vector in zip(missing, computed):
                self._safe_set(text, vector)
            for idx, vector in zip(missing_indices, computed):
                embeddings[idx] = vector

        return embeddings

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def _safe_get(self, text: str) -> list[float] | None:
        try:
            return self._cache.get(text)
        except Exception:
            return None

    def _safe_set(self, text: str, embedding: list[float]) -> None:
        try:
            self._cache.set(text, embedding)
        except Exception:
            return
