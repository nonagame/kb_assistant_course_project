from sqlalchemy.orm import Session

from database.connection import engine
from modules.user import model as user_model  # noqa: F401
from modules.audio import model as audio_model, job_model  # noqa: F401
from modules.audio import job_repository, repository, service
from modules.audio.celery_app import celery_app


@celery_app.task(name="modules.audio.tasks.process_audio_job")
def process_audio_job(job_id: str, audio_id: str) -> None:
    db = Session(engine, autoflush=False, expire_on_commit=False)
    try:
        job = job_repository.get_job(db, job_id, lock=True)
        if job is None or job.audio_id != audio_id or job.status != "queued":
            db.rollback()
            return
        job_repository.update_job(db, job, status="running", progress=10, message="正在处理音频")
        document = repository.get_document(db, audio_id)
        if document is not None:
            document.status = "processing"
            document.updated_at = repository.utc_now()
        db.commit()
        document = repository.get_document(db, audio_id)
        if document is None:
            raise RuntimeError("音频记录不存在")
        if document.source_mode == "transcript":
            service.process_saved_transcript(db, audio_id)
        else:
            service.process_saved_audio(db, audio_id)
        job = job_repository.get_job(db, job_id)
        if job is not None:
            job_repository.update_job(db, job, status="succeeded", progress=100, message="处理完成")
            db.commit()
    except Exception as exc:
        db.rollback()
        job = job_repository.get_job(db, job_id)
        if job is not None:
            job_repository.update_job(db, job, status="failed", progress=100,
                                      message=f"{type(exc).__name__}：处理失败，请检查 Worker 日志")
            db.commit()
        raise
    finally:
        db.close()