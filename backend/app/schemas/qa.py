from pydantic import BaseModel


class AskRequest(BaseModel):
    document_id: int
    question: str
    top_k: int = 3


class AskSource(BaseModel):
    page_number: int
    snippet: str


class AskResponse(BaseModel):
    answer: str
    confidence: float
    sources: list[AskSource]
