from functools import lru_cache
from typing import Any

from core.config import settings
from modules.audio.model import AudioDocument

# 索引存储文件
class ElasticsearchUnavailable(RuntimeError):
    """让混合查询识别 ES 不可用的情况。"""


@lru_cache(maxsize=1)
def get_elasticsearch():
    try:
        from elasticsearch import Elasticsearch
    except ImportError as exc:
        raise ElasticsearchUnavailable("未安装 ES 客户端") from exc

    return Elasticsearch(
        settings.elasticsearch_url,
        request_timeout=2,
        max_retries=0,
        retry_on_timeout=False,
    )


def ensure_audio_index() -> None:
    client = get_elasticsearch().options(request_timeout=30)
    index = settings.elasticsearch_audio_index

    if client.indices.exists(index=index):
        return

    client.indices.create(
        index=index,
        mappings={
            "dynamic": "strict",
            "properties": {
                "audio_id": {"type": "keyword"},
                "segment_id": {"type": "keyword"},
                "segment_idx": {"type": "integer"},
                "title": {"type": "text"},
                "text": {"type": "text"},
                "visibility": {"type": "keyword"},
                "start_ms": {"type": "long"},
                "end_ms": {"type": "long"},
            },
        },
    )


def index_audio_document(row: AudioDocument) -> int:
    if row.status != "ready":
        return 0

    client = get_elasticsearch().options(request_timeout=30)
    count = 0

    for segment in row.segments:
        segment_id = f"{row.audio_id}:{segment.segment_idx}"
        client.index(
            index=settings.elasticsearch_audio_index,
            id=segment_id,
            document={
                "audio_id": row.audio_id,
                "segment_id": segment_id,
                "segment_idx": segment.segment_idx,
                "title": row.title,
                "text": segment.text,
                "visibility": row.visibility,
                "start_ms": segment.start_ms,
                "end_ms": segment.end_ms,
            },
        )
        count += 1

    return count


def refresh_audio_index() -> None:
    client = get_elasticsearch().options(request_timeout=30)
    client.indices.refresh(index=settings.elasticsearch_audio_index)

# 查询函数
def search_keyword(
    question: str,
    k: int,
    allowed: list[str],
    audio_id: str | None = None,
) -> list[dict[str, Any]]:
    if not allowed:
        return []

    try:
        from elastic_transport import TransportError
        from elasticsearch import ApiError
    except ImportError as exc:
        raise ElasticsearchUnavailable("未安装 ES 客户端") from exc

    filters: list[dict] = [
        {"terms": {"visibility": allowed}}
    ]
    if audio_id is not None:
        filters.append({"term": {"audio_id": audio_id}})

    try:
        response = get_elasticsearch().search(
            index=settings.elasticsearch_audio_index,
            size=k,
            query={
                "bool": {
                    "must": [{
                        "multi_match": {
                            "query": question,
                            "fields": ["text^2", "title"],
                        }
                    }],
                    "filter": filters,
                }
            },
        )
    except (TransportError, ApiError) as exc:
        raise ElasticsearchUnavailable(
            "ES 请求失败或索引尚未就绪"
        ) from exc

    if (
        response.get("timed_out")
        or response.get("_shards", {}).get("failed", 0)
    ):
        raise ElasticsearchUnavailable("ES 查询超时或部分分片失败")

    results: list[dict[str, Any]] = []
    for hit in response["hits"]["hits"]:
        source = hit.get("_source")
        if not isinstance(source, dict):
            continue
        if audio_id is not None and source.get("audio_id") != audio_id:
            continue
        results.append(source)

    return results