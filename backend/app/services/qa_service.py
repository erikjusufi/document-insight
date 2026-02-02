from dataclasses import dataclass

from transformers import AutoTokenizer, pipeline

from app.core.settings import get_settings


@dataclass(frozen=True)
class QAAnswer:
    answer: str
    score: float


class QAService:
    _pipeline_by_model: dict[str, object] = {}

    def __init__(self, model_name: str | None = None) -> None:
        settings = get_settings()
        if model_name:
            self.model_name = model_name
        else:
            preset = settings.qa_model_preset.lower()
            if preset == "distilbert":
                self.model_name = settings.qa_distilbert_model_name
            else:
                self.model_name = settings.qa_model_name

    def _resolve_model_name(self, model_preset: str | None) -> str:
        settings = get_settings()
        if not model_preset:
            return self.model_name
        preset = model_preset.lower()
        if preset == "distilbert":
            return settings.qa_distilbert_model_name
        return settings.qa_model_name

    def load(self, model_name: str | None = None) -> None:
        resolved = model_name or self.model_name
        if resolved in self._pipeline_by_model:
            return
        tokenizer = AutoTokenizer.from_pretrained(resolved, use_fast=False)
        self._pipeline_by_model[resolved] = pipeline(
            "question-answering",
            model=resolved,
            tokenizer=tokenizer,
        )

    def answer(self, question: str, context: str, model_preset: str | None = None) -> QAAnswer:
        resolved = self._resolve_model_name(model_preset)
        self.load(resolved)
        pipeline_ref = self._pipeline_by_model[resolved]
        result = pipeline_ref(question=question, context=context)
        return QAAnswer(answer=result["answer"], score=float(result["score"]))

    def best_answer(
        self,
        question: str,
        contexts: list[str],
        model_preset: str | None = None,
    ) -> QAAnswer:
        best = QAAnswer(answer="", score=0.0)
        for context in contexts:
            candidate = self.answer(question, context, model_preset=model_preset)
            if candidate.score > best.score:
                best = candidate
        return best
