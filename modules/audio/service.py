import logging
from uuid import uuid4

from fastapi import HTTPException
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.orm import Session

from modules.audio import repository
from modules.knowledge.rag.vectorstore import delete_audio_vectors, get_audio_vectorstore
from modules.user.schemas import CurrentUser
from modules.user.permissions import allowed_visibilities

from pathlib import Path
from fastapi import UploadFile
from core.config import settings
from modules.audio.asr import transcribe
from modules.audio.media import convert_to_wav, probe_duration_ms
from modules.audio.media import clip_to_mp3

logger = logging.getLogger(__name__)


def mark_failed(db: Session, audio_id: str, exc: Exception) -> None:
    db.rollback()
    row = repository.get_document(db, audio_id)
    if row is not None:
        row.status = "failed"
        row.error_message = type(exc).__name__ + "：处理失败，请检查服务端日志"
        row.updated_at = repository.utc_now()
        db.commit()
    # 先标记不可检索，再补偿可能写入了一部分的向量；索引停服时保留日志。
    try:
        delete_audio_vectors(audio_id)
    except Exception:
        logger.exception("清理失败音频的向量失败：%s", audio_id)


def _write_vectors(row, segments: list[dict]) -> None:
    delete_audio_vectors(row.audio_id)
    documents: list[Document] = []
    ids: list[str] = []
    for segment in segments:
        segment_id = f"{row.audio_id}:{segment['segment_idx']}"
        documents.append(
            Document(
                page_content=segment["text"],
                metadata={
                    "audio_id": row.audio_id,
                    "segment_id": segment_id,
                    "segment_idx": segment["segment_idx"],
                    "start_ms": segment["start_ms"],
                    "end_ms": segment["end_ms"],
                    "title": row.title,
                    "visibility": row.visibility,
                },
            )
        )
        ids.append(segment_id)
    if documents:
        get_audio_vectorstore().add_documents(documents=documents, ids=ids)


def prepare_transcript(data, user: CurrentUser, db: Session):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=240,
        chunk_overlap=40,
        separators=["\n\n", "。", "！", "？", "\n", ""],
    )
    chunks = [text for text in splitter.split_text(data.transcript) if text.strip()]
    audio_id = f"aud-{uuid4().hex[:12]}"
    row = repository.create_document(
        db,
        audio_id=audio_id,
        title=data.title,
        original_filename=None,
        stored_path=None,
        visibility=data.visibility,
        source_mode="transcript",
        uploader_user_id=user.id,
        uploader_username=user.username,
    )
    segments = [
        {"segment_idx": i, "start_ms": i * 30_000, "end_ms": (i + 1) * 30_000, "text": text}
        for i, text in enumerate(chunks)
    ]
    repository.replace_segments(db, row, segments)
    return row


def _finish_index(db: Session, row):
    segments = [
        {"segment_idx": item.segment_idx, "start_ms": item.start_ms,
         "end_ms": item.end_ms, "text": item.text}
        for item in row.segments
    ]
    if not segments:
        raise RuntimeError("没有可索引的非空片段")
    _write_vectors(row, segments)
    row.status = "ready"
    row.error_message = None
    row.updated_at = repository.utc_now()
    db.commit()
    db.refresh(row)
    return row


def process_saved_transcript(db: Session, audio_id: str):
    try:
        row = repository.get_document(db, audio_id)
        if row is None or row.source_mode != "transcript":
            raise RuntimeError("转写文本记录不存在")
        return _finish_index(db, row)
    except Exception as exc:
        logger.exception("转写文本入库失败：%s", audio_id)
        mark_failed(db, audio_id, exc)
        raise


def ingest_transcript(data, user: CurrentUser, db: Session):
    row = prepare_transcript(data, user, db)
    db.commit()
    try:
        return process_saved_transcript(db, row.audio_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail={
            "message": "转写文本索引失败，请查询详情", "audio_id": row.audio_id,
        }) from exc

# 查询详情与可见范围
def get_visible_audio(db: Session, audio_id: str, user: CurrentUser):
    row = repository.get_document(db, audio_id)
    if row is None or row.visibility not in allowed_visibilities(user):
        raise HTTPException(status_code=404, detail="音频不存在")
    return row


# 真实上传 Service
ALLOWED_SUFFIXES = {".mp3", ".wav", ".m4a", ".mp4", ".aac", ".flac"}

# Whisper 原始片段通常只有几秒，不能直接作为最终知识块。
# 连续片段累计到约 240 字或约 30 秒时，合并为一个 audio_segment。
ASR_CHUNK_MAX_CHARS = 240
ASR_CHUNK_MAX_DURATION_MS = 30_000


def merge_asr_segments(
    raw_segments: list[dict],
    duration_ms: int,
    max_chars: int = ASR_CHUNK_MAX_CHARS,
    max_duration_ms: int = ASR_CHUNK_MAX_DURATION_MS,
) -> list[dict]:
    """把 Whisper 的短识别片段合并成适合检索和裁剪的知识片段。"""
    merged: list[dict] = []
    current_texts: list[str] = []
    current_start_ms: int | None = None
    current_end_ms: int | None = None

    for item in raw_segments:
        text = item["text"].strip()

        # Whisper 尾段时间可能略超出媒体实际时长，这里先做边界约束。
        start_ms = max(0, min(int(item["start_ms"]), duration_ms))
        end_ms = max(0, min(int(item["end_ms"]), duration_ms))

        if not text or end_ms <= start_ms:
            continue

        if current_start_ms is None:
            current_start_ms = start_ms

        current_texts.append(text)
        current_end_ms = end_ms

        current_text = "".join(current_texts)
        current_duration_ms = current_end_ms - current_start_ms

        # 达到任一条件就结束当前知识片段。
        if len(current_text) >= max_chars or current_duration_ms >= max_duration_ms:
            merged.append({
                "segment_idx": len(merged),
                "start_ms": current_start_ms,
                "end_ms": current_end_ms,
                "text": current_text,
            })
            current_texts = []
            current_start_ms = None
            current_end_ms = None

    # 保存最后不足 240 字、30 秒的剩余内容。
    if current_texts and current_start_ms is not None and current_end_ms is not None:
        merged.append({
            "segment_idx": len(merged),
            "start_ms": current_start_ms,
            "end_ms": current_end_ms,
            "text": "".join(current_texts),
        })

    return merged


def process_saved_audio(db: Session, audio_id: str):
    wav_path = settings.audio_wav_dir / f"{audio_id}.wav"
    try:
        row = repository.get_document(db, audio_id)
        if row is None or not row.stored_path:
            raise RuntimeError("音频记录或原始文件路径不存在")

        source_path = settings.audio_dir / row.stored_path
        if not source_path.is_file():
            raise RuntimeError("原始音频文件不存在")

        row.status = "processing"
        db.commit()

        row.duration_ms = probe_duration_ms(source_path)
        convert_to_wav(source_path, wav_path)

        # raw_segments 是 Whisper 根据语音停顿产生的短片段，
        # 不能直接写入知识库，需要先合并。
        raw_segments, language = transcribe(wav_path)
        segments = merge_asr_segments(raw_segments, row.duration_ms)

        if not segments:
            raise RuntimeError("没有识别到非空语音片段")

        repository.replace_segments(db, row, segments)
        row.language = language
        return _finish_index(db, row)

    except Exception as exc:
        logger.exception("音频处理失败：%s", audio_id)
        mark_failed(db, audio_id, exc)
        raise
    finally:
        try:
            wav_path.unlink(missing_ok=True)
        except OSError:
            logger.exception("清理识别中间文件失败：%s", wav_path)


async def prepare_audio(upload: UploadFile, visibility: str, user: CurrentUser, db: Session):
    """保存原录音并创建数据库记录。"""
    original_name = Path((upload.filename or "").replace("\\", "/")).name
    suffix = Path(original_name).suffix.lower()

    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="不支持的音频格式")
    if len(original_name) > 255:
        raise HTTPException(status_code=400, detail="文件名不能超过 255 个字符")

    limit = settings.audio_max_upload_mb * 1024 * 1024
    content = await upload.read(limit + 1)

    if not content:
        raise HTTPException(status_code=400, detail="音频文件不能为空")
    if len(content) > limit:
        raise HTTPException(status_code=413, detail="音频文件过大")

    audio_id = f"aud-{uuid4().hex[:12]}"
    settings.audio_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{audio_id}{suffix}"
    path = settings.audio_dir / stored_name

    try:
        path.write_bytes(content)
        row = repository.create_document(
            db,
            audio_id=audio_id,
            title=Path(original_name).stem[:200],
            original_filename=original_name,
            stored_path=stored_name,
            visibility=visibility,
            source_mode="asr",
            uploader_user_id=user.id,
            uploader_username=user.username,
        )
        db.commit()
        db.refresh(row)
        return row
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise


async def ingest_audio(upload: UploadFile, visibility: str, user: CurrentUser, db: Session):
    row = await prepare_audio(upload, visibility, user, db)
    audio_id = row.audio_id

    try:
        return process_saved_audio(db, audio_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "音频处理失败，请查询详情",
                "audio_id": audio_id,
            },
        ) from exc

# 裁剪函数
def create_clip(
    db: Session,
    audio_id: str,
    user: CurrentUser,
    segment_idx: int | None,
    start_ms: int | None,
    end_ms: int | None,
) -> Path:
    row = get_visible_audio(db, audio_id, user)
    if row.status != "ready":
        raise HTTPException(status_code=409, detail="音频尚未处理完成")
    if not row.stored_path:
        raise HTTPException(status_code=409, detail="该记录仅保存转写文本，没有可裁剪的原始音频")
    if segment_idx is not None:
        segment = next((item for item in row.segments if item.segment_idx == segment_idx), None)
        if segment is None:
            raise HTTPException(status_code=404, detail="音频片段不存在")
        start_ms, end_ms = segment.start_ms, segment.end_ms
    if start_ms is None or end_ms is None or end_ms <= start_ms:
        raise HTTPException(status_code=400, detail="必须提供合法片段编号或时间范围")
    if end_ms > row.duration_ms or end_ms - start_ms > 60_000:
        raise HTTPException(status_code=400, detail="裁剪范围超出音频或超过 60 秒")
    source = settings.audio_dir / row.stored_path
    if not source.is_file():
        raise HTTPException(status_code=404, detail="原始音频文件不存在")
    target = settings.audio_clip_dir / f"clip-{uuid4().hex}.mp3"
    try:
        clip_to_mp3(source, target, start_ms, end_ms)
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail="裁剪失败，请检查 FFmpeg") from exc
    return target