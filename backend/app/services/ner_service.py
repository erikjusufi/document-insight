from dataclasses import dataclass

import spacy

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
