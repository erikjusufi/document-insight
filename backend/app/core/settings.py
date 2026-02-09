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
    sample_docs_dir: str = "../samples"
    ocr_languages: list[str] = ["en", "hr"]
    ocr_min_text_length: int = 100
    qa_model_preset: str = "best"
    qa_model_name: str = "deepset/xlm-roberta-large-squad2"
    qa_distilbert_model_name: str = "distilbert-base-cased-distilled-squad"
    qa_load_on_startup: bool = True
    qa_top_k: int = 10
    qa_max_context_chars: int = 4000
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    faiss_index_dir: str = "./storage/faiss"
    redis_url: str = "redis://localhost:6379/0"
    ner_default_model: str = "en_core_web_sm"
    ner_model_map: dict[str, str] = {"en": "en_core_web_sm", "hr": "hr_core_news_sm"}
    ner_auto_download: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
