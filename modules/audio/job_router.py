from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Annotated, Literal
from fastapi import File, Form, UploadFile

from database.connection import get_session
from modules.audio import job_service
from modules.audio.job_schemas import AudioJobOut
from modules.audio.schemas import TranscriptIn
from modules.user.permissions import require_permission
from modules.user.schemas import CurrentUser


router = APIRouter(prefix="/audio/jobs", tags=["音频异步任务"])


@router.post("/transcripts", response_model=AudioJobOut, status_code=202)
def submit_transcript(
    data: TranscriptIn,
    db: Session = Depends(get_session),
    user: CurrentUser = Depends(require_permission("kb.manage_docs")),
) -> AudioJobOut:
    return job_service.submit_transcript_job(db, data, user)


@router.get("/{job_id}", response_model=AudioJobOut)
def status(
    job_id: str,
    db: Session = Depends(get_session),
    _: CurrentUser = Depends(require_permission("kb.manage_docs")),
) -> AudioJobOut:
    return job_service.get_job(db, job_id)

@router.post("", response_model=AudioJobOut, status_code=202)
async def submit(
    file: Annotated[UploadFile, File()],
    visibility: Annotated[Literal["public", "internal"], Form()] = "public",
    db: Session = Depends(get_session),
    user: CurrentUser = Depends(require_permission("kb.manage_docs")),
) -> AudioJobOut:
    return await job_service.submit_job(db, file, visibility, user)

# 排队任务取消路由
@router.post("/{job_id}/cancel", response_model=AudioJobOut)
def cancel(
    job_id: str,
    db: Session = Depends(get_session),
    _: CurrentUser = Depends(require_permission("kb.manage_docs")),
) -> AudioJobOut:
    return job_service.cancel_job(db, job_id)