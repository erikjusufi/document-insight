from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import spacy
from spacy.cli.download import download as spacy_download
from spacy.util import is_package

from app.core.settings import get_settings


@dataclass(frozen=True)
class Entity:
    text: str
    label: str


class NERService:
    def __init__(self, model_map: dict[str, str] | None = None, default_model: str | None = None) -> None:
        settings = get_settings()
        self.model_map = model_map or settings.ner_model_map
        self.default_model = default_model or settings.ner_default_model
        self._models: dict[str, object] = {}

    def _get_nlp(self, language: str | None):
        model_name = self.model_map.get(language or "", self.default_model)
        if model_name not in self._models:
            self._models[model_name] = spacy.load(model_name)
        return self._models[model_name]

    def extract(self, text: str, language: str | None = None) -> list[Entity]:
        doc = self._get_nlp(language)(text)
        return [Entity(text=ent.text, label=ent.label_) for ent in doc.ents]


def _is_model_available(model_name: str) -> bool:
    if is_package(model_name):
        return True
    if Path(model_name).exists():
        return True
    return False


def _ensure_pip_available() -> None:
    try:
        import pip  # noqa: F401
    except Exception as exc:
        try:
            import ensurepip

            ensurepip.bootstrap(upgrade=True)
        except Exception as inner_exc:
            raise RuntimeError(
                "pip is required to auto-download spaCy models. "
                "Install pip or set NER_AUTO_DOWNLOAD=false."
            ) from inner_exc
        try:
            import pip  # noqa: F401
        except Exception as inner_exc:
            raise RuntimeError(
                "pip is required to auto-download spaCy models. "
                "Install pip or set NER_AUTO_DOWNLOAD=false."
            ) from inner_exc


def ensure_models_available(model_names: Iterable[str], *, auto_download: bool) -> None:
    missing = [name for name in model_names if not _is_model_available(name)]
    if not missing:
        return
    if not auto_download:
        missing_list = ", ".join(missing)
        raise RuntimeError(
            f"Missing spaCy model(s): {missing_list}. "
            "Install them or set NER_AUTO_DOWNLOAD=true."
        )
    _ensure_pip_available()
    for name in missing:
        try:
            spacy_download(name)
        except SystemExit as exc:
            raise RuntimeError(
                f"Failed to auto-download spaCy model '{name}'. "
                "Install it manually or set NER_AUTO_DOWNLOAD=false."
            ) from exc
