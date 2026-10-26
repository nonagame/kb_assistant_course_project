import json
import time
from contextlib import contextmanager
from copy import deepcopy
from typing import Any

from fastapi import HTTPException
from redis.exceptions import RedisError

from core.config import settings


# 字典以 `session_id` 为键，只保存待办和所属用户等业务字段；默认保存 48 小时。
_memory: dict[str, tuple[float, dict[str, Any]]] = {}
SAVED_FIELDS = {"active_route", "pending_leave", "requester", "user_id", "last_leave_id"}


def _redis_client():
    import redis

    return redis.Redis.from_url(
        settings.redis_url, decode_responses=True,
        socket_connect_timeout=5, socket_timeout=5,
    )


@contextmanager
def session_scope(session_id: str, user_id: int, *, existing: bool):
    """按顺序处理会话；每次请求先核对归属。"""
    previous = load_session(session_id)
    if previous is not None and previous.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Session 不属于当前用户")
    if existing and previous is None:
        raise HTTPException(status_code=409, detail="Session 不存在或已过期，请不带 session_id 重新开始")
    yield previous or {}


def load_session(session_id: str) -> dict[str, Any] | None:
    if settings.session_backend == "redis":
        try:
            raw = _redis_client().get(f"kb:session:{session_id}")
        except RedisError as exc:
            raise HTTPException(status_code=503, detail="Session Redis 不可用") from exc
        return json.loads(raw) if raw else None
    item = _memory.get(session_id)
    if item is None:
        return None
    expires_at, value = item
    if time.monotonic() >= expires_at:
        _memory.pop(session_id, None)
        return None
    return deepcopy(value)


def save_session(session_id: str, state: dict[str, Any]) -> None:
    safe = {key: value for key, value in state.items() if key in SAVED_FIELDS}
    if settings.session_backend == "redis":
        try:
            _redis_client().setex(
                f"kb:session:{session_id}", settings.session_ttl_seconds,
                json.dumps(safe, ensure_ascii=False),
            )
        except RedisError as exc:
            raise HTTPException(status_code=503, detail="Session Redis 不可用") from exc
        return
    _memory[session_id] = (time.monotonic() + settings.session_ttl_seconds, deepcopy(safe))


def clear_session(session_id: str) -> None:
    if settings.session_backend == "redis":
        try:
            _redis_client().delete(f"kb:session:{session_id}")
        except RedisError as exc:
            raise HTTPException(status_code=503, detail="Session Redis 不可用") from exc
        return
    _memory.pop(session_id, None)


def clear_sessions():
    _memory.clear()