from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.schemas.jobs import JobStatusResponse
from app.services.current_user import get_current_user

router = APIRouter()


def get_job_store(request: Request):
    if hasattr(request.app.state, "job_store"):
        return request.app.state.job_store
    return None


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    request: Request,
    current_user=Depends(get_current_user),
) -> JobStatusResponse:
    store = get_job_store(request)
    if store is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Job store not available")
    record = store.get(job_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if record.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return JobStatusResponse(
        job_id=record.job_id,
        job_type=record.job_type,
        status=record.status,
        stage=record.stage,
        progress=record.progress,
        result=record.result,
        error=record.error,
    )
