from app.core.settings import get_settings
from app.services.qa_service import QAService


def test_qa_model_preset_best(monkeypatch) -> None:
    monkeypatch.setenv("QA_MODEL_PRESET", "best")
    monkeypatch.setenv("QA_MODEL_NAME", "best-model")
    get_settings.cache_clear()

    service = QAService()
    assert service.model_name == "best-model"


def test_qa_model_preset_distilbert(monkeypatch) -> None:
    monkeypatch.setenv("QA_MODEL_PRESET", "distilbert")
    monkeypatch.setenv("QA_DISTILBERT_MODEL_NAME", "distilbert-model")
    get_settings.cache_clear()

    service = QAService()
    assert service.model_name == "distilbert-model"
