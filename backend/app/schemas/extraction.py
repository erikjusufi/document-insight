from pydantic import BaseModel


class ExtractionResponse(BaseModel):
    document_id: int
    pages_extracted: int
    chunks_created: int
