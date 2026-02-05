from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: int
    filename: str
    content_type: str
    size_bytes: int
    language: str | None = None


class DocumentLibraryResponse(BaseModel):
    id: int
    filename: str
    content_type: str
    size_bytes: int
    language: str | None = None
    pages_count: int
    chunks_count: int
    extraction_status: str
