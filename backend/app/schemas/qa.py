from typing import Literal

from pydantic import BaseModel


class AskRequest(BaseModel):
    document_id: int
    question: str
    top_k: int = 3
    model_preset: Literal["best", "distilbert"] | None = None


class AskSource(BaseModel):
    page_number: int
    snippet: str


class AskEntity(BaseModel):
    text: str
    label: str


class AskResponse(BaseModel):
    answer: str
    confidence: float
    sources: list[AskSource]
    entities: list[AskEntity]
