from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.audio.job_model import AudioJob

def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_job(db: Session, job_id: str, audio_id: str) -> AudioJob:
    now = utc_now()
    row = AudioJob(
        job_id=job_id,
        audio_id=audio_id,
        status="queued",
        progress=0,
        message="等待 Worker 处理",
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def get_job(db: Session, job_id: str, *, lock: bool = False) -> AudioJob | None:
    # lock = True 给当前任务加数据库行锁
    statement = select(AudioJob).where(AudioJob.job_id == job_id)
    if lock:
        statement = statement.with_for_update()
    return db.scalar(statement.execution_options(populate_existing=True))


def update_job(
    db: Session,
    row: AudioJob,
    *,
    status: str,
    progress: int,
    message: str,
) -> None:
    row.status = status
    row.progress = progress
    row.message = message
    row.updated_at = utc_now()