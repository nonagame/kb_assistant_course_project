import logging

from sqlalchemy.orm import Session

from core.config import settings
from modules.audio.elasticsearch_store import (
    ElasticsearchUnavailable,
    search_keyword,
)
from modules.audio.search import search_audio, verified_segment
from modules.user.permissions import allowed_visibilities
from modules.user.schemas import CurrentUser


logger = logging.getLogger(__name__)

# RRF 函数
def _rrf(
    vector_hits: list[dict],
    keyword_hits: list[dict],
    k: int,
) -> list[dict]:
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}

    for hits in (vector_hits, keyword_hits):
        seen: set[str] = set()
        for rank, item in enumerate(hits, start=1):
            segment_id = item["segment_id"]
            if segment_id in seen:
                continue
            seen.add(segment_id)

            scores[segment_id] = (
                scores.get(segment_id, 0.0) + 1.0 / (60 + rank)
            )
            items.setdefault(segment_id, item)

    ordered = sorted(
        scores,
        key=lambda key: (-scores[key], key),
    )[:k]

    return [
        {**items[key], "score": round(scores[key], 6)}
        for key in ordered
    ]


# 混合查询函数
def hybrid_search(
    db: Session,
    question: str,
    k: int,
    user: CurrentUser,
    audio_id: str | None = None,
) -> dict:
    allowed = allowed_visibilities(user)

    # 向量结果已由 search_audio 完成权限与 MySQL 复核。
    vector_hits = search_audio(db, question, k * 2, user, audio_id)

    mode = "vector_only"
    keywords: list[dict] = []
    if settings.elasticsearch_enabled:
        try:
            keywords = search_keyword(question, k * 6, allowed, audio_id)
            mode = "hybrid"
        except ElasticsearchUnavailable:
            logger.warning("ES 不可用，本次使用 vector_only", exc_info=True)

    # ES 中的内容是候选，不能直接当作最终证据。
    verified_keywords: list[dict] = []
    for item in keywords:
        segment = verified_segment(db, item, allowed)
        if segment is None:
            continue

        verified_keywords.append({
            "audio_id": item["audio_id"],
            "segment_id": item["segment_id"],
            "start_ms": segment.start_ms,
            "end_ms": segment.end_ms,
            "text": segment.text,
            "visibility": item["visibility"],
        })

    return {
        "q": question,
        "retrieval_mode": mode,
        "hits": _rrf(vector_hits, verified_keywords, k),
    }