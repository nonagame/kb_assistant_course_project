from datetime import datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class AudioJob(Base):
    __tablename__ = "audio_jobs"
    __table_args__ = (
        Index("ix_audio_jobs_audio_id", "audio_id"),
    )

    job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    audio_id: Mapped[str] = mapped_column(ForeignKey("audio_documents.audio_id", ondelete="CASCADE"), nullable=False)
    celery_task_id: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    progress: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), default=0, nullable=False)
    message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(mysql.DATETIME(fsp=6), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(mysql.DATETIME(fsp=6), nullable=False)