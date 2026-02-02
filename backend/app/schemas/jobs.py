from typing import Any

from pydantic import BaseModel


class JobStatusResponse(BaseModel):
    job_id: str
    job_type: str
    status: str
    stage: str | None = None
    progress: int = 0
    result: dict[str, Any] | None = None
    error: str | None = None
