from pydantic import BaseModel


class EntityResponse(BaseModel):
    text: str
    label: str


class EntitiesResponse(BaseModel):
    document_id: int
    entities: list[EntityResponse]
