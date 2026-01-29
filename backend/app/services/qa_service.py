from dataclasses import dataclass

from transformers import AutoTokenizer, pipeline

from app.core.settings import get_settings


@dataclass(frozen=True)
class QAAnswer:
    answer: str
    score: float


class QAService:
    def __init__(self, model_name: str | None = None) -> None:
        settings = get_settings()
        self.model_name = model_name or settings.qa_model_name
        self._pipeline = None

    def load(self) -> None:
        if self._pipeline is None:
            tokenizer = AutoTokenizer.from_pretrained(self.model_name, use_fast=False)
            self._pipeline = pipeline(
                "question-answering",
                model=self.model_name,
                tokenizer=tokenizer,
            )

    def answer(self, question: str, context: str) -> QAAnswer:
        if self._pipeline is None:
            self.load()
        result = self._pipeline(question=question, context=context)
        return QAAnswer(answer=result["answer"], score=float(result["score"]))

    def best_answer(self, question: str, contexts: list[str]) -> QAAnswer:
        best = QAAnswer(answer="", score=0.0)
        for context in contexts:
            candidate = self.answer(question, context)
            if candidate.score > best.score:
                best = candidate
        return best
