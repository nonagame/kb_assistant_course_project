from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TranscriptIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=200)
    transcript: str = Field(min_length=1, max_length=100_000)
    visibility: str = Field(default="public", pattern=r"^(public|internal)$")


class AudioSegmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    segment_idx: int
    start_ms: int
    end_ms: int
    text: str


class AudioDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    audio_id: str
    title: str
    original_filename: str | None
    duration_ms: int
    language: str | None
    visibility: str
    status: str
    source_mode: str
    error_message: str | None
    segment_count: int
    created_at: datetime
    updated_at: datetime
    segments: list[AudioSegmentOut]

# 检索响应模型
class AudioHit(BaseModel):
    audio_id: str
    segment_id: str
    start_ms: int
    end_ms: int
    text: str
    visibility: str
    score: float
class AudioQueryOut(BaseModel):
    q: str
    hits: list[AudioHit]

# 带引用的 SSE 流式音频回答 请求模型
class AudioAskIn(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True
    )
    # 用户问题
    question: str = Field(
        min_length=1,
        max_length=2000,
    )
    # k表示最多使用多少条音频证据
    k: int = Field(
        default=4,
        ge=1,
        le=10,
    )
    # 不传表示搜索当前用户有权限查看的全部音频，传入表只在指定音频中搜索
    audio_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=80,
    )

# 混合查询接口
class AudioHybridOut(BaseModel):
    q: str
    retrieval_mode: Literal["hybrid", "vector_only"]
    hits: list[AudioHit]