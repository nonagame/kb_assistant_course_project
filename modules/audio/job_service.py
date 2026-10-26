from uuid import uuid4

from fastapi import HTTPException,UploadFile
from sqlalchemy.orm import Session

from modules.audio import job_repository, repository
from modules.audio.service import prepare_transcript
from modules.user.schemas import CurrentUser
from modules.audio.service import prepare_audio, mark_failed

def publish_job(db: Session, job):
    # 先保存固定 task_id，Worker 即使立即开始也不会被提交接口改回 queued。
    from modules.audio.tasks import process_audio_job

    job_id, audio_id = job.job_id, job.audio_id
    job.celery_task_id = uuid4().hex
    db.commit()
    try:
        process_audio_job.apply_async(args=[job_id, audio_id], task_id=job.celery_task_id)
    except Exception as exc:
        db.rollback()
        job = job_repository.get_job(db, job_id, lock=True)
        if job is not None and job.status == "queued":
            job_repository.update_job(db, job, status="failed", progress=0, message="无法提交到 Celery broker")
            document = repository.get_document(db, audio_id)
            if document is not None:
                document.status = "failed"
                document.error_message = "无法提交到 Celery broker"
                document.updated_at = repository.utc_now()
            db.commit()
        else:
            db.rollback()
        raise HTTPException(status_code=503, detail={
            "message": "异步任务提交失败，请查询任务状态",
            "job_id": job_id, "audio_id": audio_id,
        }) from exc
    db.expire_all()
    return job_repository.get_job(db, job_id)


def submit_transcript_job(db: Session, data, user: CurrentUser):
    document = prepare_transcript(data, user, db)
    document.status = "queued"
    job = job_repository.create_job(db, f"job-{uuid4().hex[:12]}", document.audio_id)
    return publish_job(db, job)


def get_job(db: Session, job_id: str):
    row = job_repository.get_job(db, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return row

# 音频提交
async def submit_job(
    db: Session, upload: UploadFile, visibility: str, user: CurrentUser,
):
    # 格式、大小、保存路径和写入失败清理均由第九章同一函数处理。
    document = await prepare_audio(upload, visibility, user, db)
    audio_id = document.audio_id
    try:
        document.status = "queued"
        job = job_repository.create_job(db, f"job-{uuid4().hex[:12]}", audio_id)
        db.commit()
    except Exception as exc:
        mark_failed(db, audio_id, exc)
        raise HTTPException(status_code=503, detail={
            "message": "创建任务失败，请查询音频状态", "audio_id": audio_id,
        }) from exc
    return publish_job(db, job)

# 排队任务取消
def cancel_job(db: Session, job_id: str):
    # 与 Worker 使用同一行锁；只有一方能把 queued 改成下一状态。
    row = job_repository.get_job(db, job_id, lock=True)
    if row is None:
        db.rollback()
        raise HTTPException(status_code=404, detail="任务不存在")
    if row.status != "queued":
        db.rollback()
        raise HTTPException(status_code=409, detail="只有 queued 任务可以取消")
    job_repository.update_job(db, row, status="cancelled", progress=0, message="任务已取消")
    document = repository.get_document(db, row.audio_id)
    if document is not None:
        document.status = "cancelled"
        document.updated_at = repository.utc_now()
    db.commit()
    db.refresh(row)
    return row