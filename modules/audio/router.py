from fastapi import APIRouter, Depends, HTTPException,File, Form, UploadFile,Query
from sqlalchemy.orm import Session
from typing import Annotated, Literal

from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from fastapi.responses import StreamingResponse

from database.connection import get_session
from modules.audio import service
from modules.audio.schemas import AudioDetailOut, TranscriptIn
from modules.user.permissions import require_permission
from modules.user.schemas import CurrentUser
from modules.user.dependencies import get_current_user
from modules.audio import search
from modules.audio.schemas import AudioQueryOut
from modules.audio.schemas import AudioAskIn
from modules.audio.hybrid import hybrid_search
from modules.audio.schemas import AudioHybridOut

router = APIRouter(prefix="/audio", tags=["音频知识库"])

# 创建并注册文本入库接口
@router.post("/transcripts", response_model=AudioDetailOut, status_code=201)
def ingest_transcript(
    data: TranscriptIn,
    user: CurrentUser = Depends(require_permission("kb.manage_docs")),
    db: Session = Depends(get_session),
) -> AudioDetailOut:
    return service.ingest_transcript(data, user, db)


# GET 接口
@router.get("/query", response_model=AudioQueryOut)
def query_audio(
    q: str = Query(min_length=1, max_length=2000),
    k: int = Query(default=4, ge=1, le=10),
    audio_id: str | None = Query(default=None, min_length=1, max_length=80),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict:
    question = q.strip()
    if not question:
        raise HTTPException(status_code=422, detail="q 不能为空白")

    return {
        "q": question,
        "hits": search.search_audio(
            db=db,
            question=question,
            k=k,
            user=user,
            audio_id=audio_id,
        ),
    }

# 查询详情与可见范围
# 动态路径放在静态路径后面
@router.get("/{audio_id}", response_model=AudioDetailOut)
def audio_detail(
    audio_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> AudioDetailOut:
    return service.get_visible_audio(db, audio_id, user)

# 上传 路由
@router.post("/ingest", response_model=AudioDetailOut, status_code=201)
async def ingest_audio(
    file: Annotated[UploadFile, File()],
    visibility: Annotated[Literal["public", "internal"], Form()] = "public",
    user: CurrentUser = Depends(require_permission("kb.manage_docs")),
    db: Session = Depends(get_session),
) -> AudioDetailOut:
    return await service.ingest_audio(file, visibility, user, db)

# 裁剪路由
@router.get("/{audio_id}/clip")
def audio_clip(
    audio_id: str,
    segment_idx: int | None = Query(default=None, ge=0),
    start_ms: int | None = Query(default=None, ge=0),
    end_ms: int | None = Query(default=None, gt=0),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> FileResponse:
    path = service.create_clip(db, audio_id, user, segment_idx, start_ms, end_ms)
    return FileResponse(
        path,
        media_type="audio/mpeg",
        filename=f"{audio_id}.mp3",
        background=BackgroundTask(path.unlink, missing_ok=True),
    )

# 带引用的 SSE 流式音频回答路由
@router.post("/ask/stream")
def ask_audio_stream(
    data: AudioAskIn,
    user: CurrentUser = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_session
    ),
) -> StreamingResponse:
    citations = search.search_audio(
        db,
        data.question,
        data.k,
        user,
        data.audio_id,
    )
    return StreamingResponse(
        search.stream_answer(
            data.question,
            citations,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

# 混合查询路由
@router.get("/query/hybrid", response_model=AudioHybridOut)
def query_audio_hybrid(
    q: str = Query(min_length=1, max_length=2000),
    k: int = Query(default=5, ge=1, le=10),
    audio_id: str | None = Query(
        default=None,
        min_length=1,
        max_length=80,
    ),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict:
    question = q.strip()
    if not question:
        raise HTTPException(status_code=422, detail="q 不能为空白")

    if audio_id is not None:
        audio_id = audio_id.strip()
        if not audio_id:
            raise HTTPException(
                status_code=422,
                detail="audio_id 不能为空白",
            )

    return hybrid_search(db, question, k, user, audio_id)

# 混合证据接入流式回答的路由
@router.post("/ask/hybrid/stream")
def ask_audio_hybrid_stream(
    data: AudioAskIn,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> StreamingResponse:
    result = hybrid_search(
        db,
        data.question,
        data.k,
        user,
        data.audio_id,
    )

    return StreamingResponse(
        search.stream_answer(
            data.question,
            result["hits"],
            retrieval_mode=result["retrieval_mode"],
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )