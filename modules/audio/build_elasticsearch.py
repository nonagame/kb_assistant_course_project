# 构建入口
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from core.config import settings
from database.connection import engine
from modules.audio.elasticsearch_store import (
    ensure_audio_index,
    index_audio_document,
    refresh_audio_index,
)
from modules.audio.model import AudioDocument


def main() -> None:
    print(f"ES_INDEX_TARGET index={settings.elasticsearch_audio_index}")
    ensure_audio_index()

    with Session(engine) as db:
        statement = (
            select(AudioDocument)
            .where(AudioDocument.status == "ready")
            .options(selectinload(AudioDocument.segments))
            .order_by(AudioDocument.audio_id)
        )
        rows = list(db.scalars(statement))
        total = sum(index_audio_document(row) for row in rows)
        refresh_audio_index()

    print(f"ES_INDEX_OK audio={len(rows)} segments_written={total}")


if __name__ == "__main__":
    main()