from datetime import datetime, timezone
from sqlalchemy.orm import Session

from modules.audio.model import AudioDocument, AudioSegment


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_document(
    db: Session,
    *,
    audio_id: str,
    title: str,
    original_filename: str | None,
    stored_path: str | None,
    visibility: str,
    source_mode: str,
    uploader_user_id: int,
    uploader_username: str,
) -> AudioDocument:
    now = utc_now()
    row = AudioDocument(
        audio_id=audio_id,
        title=title,
        original_filename=original_filename,
        stored_path=stored_path,
        duration_ms=0,
        language=None,
        visibility=visibility,
        status="processing",
        source_mode=source_mode,
        error_message=None,
        uploader_user_id=uploader_user_id,
        uploader_username=uploader_username,
        segment_count=0,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def get_document(db: Session, audio_id: str) -> AudioDocument | None:
    return db.get(AudioDocument, audio_id)


def replace_segments(db: Session, row: AudioDocument, segments: list[dict]) -> None:
    row.segments = [
        AudioSegment(
            audio_id=row.audio_id,
            segment_idx=segment["segment_idx"],
            start_ms=segment["start_ms"],
            end_ms=segment["end_ms"],
            text=segment["text"],
        )
        for segment in segments
    ]
    row.segment_count = len(segments)
    row.updated_at = utc_now()
    db.flush()