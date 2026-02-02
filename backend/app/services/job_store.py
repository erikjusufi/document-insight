from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from time import time
from uuid import uuid4


@dataclass
class JobRecord:
    job_id: str
    job_type: str
    user_id: int
    status: str = "queued"
    stage: str | None = None
    progress: int = 0
    result: dict | None = None
    error: str | None = None
    updated_at: float = field(default_factory=time)


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = Lock()

    def create(self, job_type: str, user_id: int) -> JobRecord:
        job_id = uuid4().hex
        record = JobRecord(job_id=job_id, job_type=job_type, user_id=user_id)
        with self._lock:
            self._jobs[job_id] = record
        return record

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, *, status: str | None = None, stage: str | None = None, progress: int | None = None) -> None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return
            if status is not None:
                record.status = status
            if stage is not None:
                record.stage = stage
            if progress is not None:
                record.progress = max(0, min(progress, 100))
            record.updated_at = time()

    def complete(self, job_id: str, result: dict | None = None) -> None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return
            record.status = "completed"
            record.stage = "completed"
            record.progress = 100
            record.result = result
            record.updated_at = time()

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return
            record.status = "failed"
            record.stage = "failed"
            record.error = error
            record.progress = min(record.progress or 0, 100)
            record.updated_at = time()
