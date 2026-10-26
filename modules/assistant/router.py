"""接收请求"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.session_store import save_session, session_scope
from database.connection import get_session
from modules.assistant.graph import router_graph
from modules.assistant.schemas import ChatRequest, ChatResponse
from modules.user.dependencies import get_current_user
from modules.user.permissions import allowed_visibilities
from modules.user.schemas import CurrentUser


router = APIRouter(tags=["智能助手"])

# 接收请求并保存会话的路由
@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict:
    # 上下文记忆
    session_id = request.session_id or f"sid-{uuid.uuid4().hex}"
    with session_scope(session_id, user.id, existing=request.session_id is not None) as previous:
        state = {**previous, "text": request.text, "question": request.text,
                 "mode": request.mode, "user_id": user.id, "requester": user.username,
                 "permissions": sorted(user.permissions),
                 "allowed_visibilities": allowed_visibilities(user), "db": db}
        output = router_graph.invoke(state)
        output["active_route"] = "leave" if output.get("pending_leave") else ""
        save_session(session_id, output)
    output["session_id"] = session_id
    return output