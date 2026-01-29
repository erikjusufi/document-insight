from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Document Insight Service"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./app.db"
    secret_key: str = "dev-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    storage_dir: str = "./storage"
    ocr_languages: list[str] = ["en", "hr"]
    ocr_min_text_length: int = 100
    qa_model_name: str = "deepset/xlm-roberta-large-squad2"
    qa_load_on_startup: bool = True
    qa_top_k: int = 10
    qa_max_context_chars: int = 4000


@lru_cache
def get_settings() -> Settings:
    return Settings()
