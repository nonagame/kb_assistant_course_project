from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class AudioDocument(Base):
    __tablename__ = "audio_documents"

    audio_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    stored_path: Mapped[str | None] = mapped_column(String(1024))
    duration_ms: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), default=0, nullable=False)
    language: Mapped[str | None] = mapped_column(String(32))
    visibility: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="processing", nullable=False, index=True)
    source_mode: Mapped[str] = mapped_column(String(32), default="asr", nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(500))
    uploader_user_id: Mapped[int | None] = mapped_column(
        mysql.BIGINT(unsigned=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    uploader_username: Mapped[str | None] = mapped_column(String(64))
    segment_count: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(mysql.DATETIME(fsp=6), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(mysql.DATETIME(fsp=6), nullable=False)

    segments: Mapped[list["AudioSegment"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )


class AudioSegment(Base):
    __tablename__ = "audio_segments"

    audio_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("audio_documents.audio_id", ondelete="CASCADE"), primary_key=True
    )
    segment_idx: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), primary_key=True)
    start_ms: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), nullable=False)
    end_ms: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), nullable=False)
    text: Mapped[str] = mapped_column(mysql.MEDIUMTEXT, nullable=False)

    document: Mapped[AudioDocument] = relationship(back_populates="segments")