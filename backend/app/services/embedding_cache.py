import json
import hashlib

from redis import Redis

from app.core.settings import get_settings


class EmbeddingCache:
    def __init__(self, redis_url: str | None = None) -> None:
        settings = get_settings()
        self.redis_url = redis_url or settings.redis_url
        self._client: Redis | None = None

    def _get_client(self) -> Redis:
        if self._client is None:
            self._client = Redis.from_url(self.redis_url)
        return self._client

    def _key(self, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"embedding:{digest}"

    def get(self, text: str) -> list[float] | None:
        payload = self._get_client().get(self._key(text))
        if payload is None:
            return None
        return json.loads(payload)

    def set(self, text: str, embedding: list[float]) -> None:
        self._get_client().set(self._key(text), json.dumps(embedding))
