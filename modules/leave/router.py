from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.connection import get_session
from modules.leave import service
from modules.leave.schemas import LeaveListOut
from modules.user.dependencies import get_current_user
from modules.user.schemas import CurrentUser

import uuid

from core.session_store import save_session, session_scope
from modules.leave.schemas import LeaveChatIn, LeaveChatOut
from modules.leave.workflow import run_leave

from modules.leave.schemas import DecisionIn, LeaveActionOut


router = APIRouter(prefix="/leave", tags=["请假流程"])


# 阶段A 查询接口
@router.get("/requests", response_model=LeaveListOut)
def requests(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    return service.get_requests(db, user)


# 阶段B 填写申请，确认后写入
@router.post("/chat", response_model=LeaveChatOut)
def leave_chat(
    request: LeaveChatIn,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    session_id = request.session_id or f"sid-{uuid.uuid4().hex}"
    with session_scope(session_id, user.id, existing=request.session_id is not None) as previous:
        output = run_leave({
            **previous, "text": request.text, "db": db,
            "user_id": user.id, "requester": user.username, "permissions": user.permissions,
        })
        state = {**previous, **output, "user_id": user.id, "requester": user.username}
        state["active_route"] = "leave" if state.get("pending_leave") else ""
        save_session(session_id, state)
    return {**output, "session_id": session_id}


# 阶段 C：批准、驳回、本人撤销
@router.post("/{leave_id}/approve", response_model=LeaveActionOut)
def approve(
    leave_id: str, data: DecisionIn,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    return service.decide_request(db, leave_id, user, new_status="APPROVED", reason=data.reason)


@router.post("/{leave_id}/reject", response_model=LeaveActionOut)
def reject(
    leave_id: str, data: DecisionIn,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    return service.decide_request(db, leave_id, user, new_status="REJECTED", reason=data.reason)


@router.post("/{leave_id}/cancel", response_model=LeaveActionOut)
def cancel(
    leave_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    return service.cancel_request(db, leave_id, user)