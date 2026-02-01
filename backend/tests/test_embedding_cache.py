from app.services.embedding_cache import EmbeddingCache
from app.services.embedding_service import EmbeddingService


class FakeCache(EmbeddingCache):
    def __init__(self):
        self.store = {}

    def get(self, text: str):
        return self.store.get(text)

    def set(self, text: str, embedding: list[float]) -> None:
        self.store[text] = embedding


class FakeModel:
    def __init__(self):
        self.calls = []

    def encode(self, texts, normalize_embeddings=True):
        self.calls.append(list(texts))
        return [[float(len(text))] for text in texts]


def test_embedding_service_uses_cache(monkeypatch):
    fake_cache = FakeCache()
    fake_cache.set("hello", [1.0])

    service = EmbeddingService(cache=fake_cache)
    fake_model = FakeModel()

    monkeypatch.setattr(service, "_get_model", lambda: fake_model)

    result = service.embed_texts(["hello", "world"])

    assert result[0] == [1.0]
    assert result[1] == [5.0]
    assert fake_cache.get("world") == [5.0]
    assert fake_model.calls == [["world"]]


def test_embedding_service_cache_hit_no_model_call(monkeypatch):
    fake_cache = FakeCache()
    fake_cache.set("cached", [2.0])

    service = EmbeddingService(cache=fake_cache)
    fake_model = FakeModel()

    monkeypatch.setattr(service, "_get_model", lambda: fake_model)

    result = service.embed_texts(["cached"])

    assert result == [[2.0]]
    assert fake_model.calls == []
