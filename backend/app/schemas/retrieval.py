from pydantic import BaseModel


class RetrievalRequest(BaseModel):
    query: str
    top_k: int = 3
    min_score: float = 0.0
    offset: int = 0


class RetrievalResultResponse(BaseModel):
    page_number: int
    chunk_index: int
    snippet: str
    score: float


class RetrievalResponse(BaseModel):
    document_id: int
    results: list[RetrievalResultResponse]
