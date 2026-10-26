from sqlalchemy import select,update

from modules.leave.model import LeaveRequest

from datetime import datetime, timezone

# A 查询数据库
def list_requests(db, user_id, view_all, limit=100):
    statement = select(LeaveRequest).order_by(LeaveRequest.id.desc()).limit(limit)
    if not view_all:
        statement = statement.where(LeaveRequest.user_id == user_id)
    return list(db.scalars(statement).all())

# B 请假申请
def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def list_recent(db, user_id, view_all, limit=10):
    return [
        {"leave_id": row.leave_id, "requester": row.requester,
         "leave_type": row.leave_type, "status": row.status}
        for row in list_requests(db, user_id, view_all, limit)
    ]


def get_request(db, leave_id):
    return db.scalar(select(LeaveRequest).where(LeaveRequest.leave_id == leave_id))


def create_request(db, *, leave_id, user_id, requester, pending):
    request = LeaveRequest(
        leave_id=leave_id, user_id=user_id, requester=requester,
        leave_type=pending["leave_type"],
        start_time=datetime.fromisoformat(pending["start_time"]),
        end_time=datetime.fromisoformat(pending["end_time"]),
        duration_days=pending["duration_days"], reason=pending["reason"],
        status="PENDING", created_at=utc_now(), updated_at=utc_now(),
    )
    db.add(request)
    db.flush()
    return request

# C 状态修改逻辑
# 利用数据库的 WHERE 条件来实现乐观锁和权限校验

# 审批请假
def update_status(db, leave_id, *, new_status, approver_user_id, reason):
    result = db.execute(
        update(LeaveRequest).where(
            LeaveRequest.leave_id == leave_id,
            # 防重复提交
            LeaveRequest.status == "PENDING",
        ).values(
            status=new_status, approver_user_id=approver_user_id,
            decision_reason=reason, decided_at=utc_now(), updated_at=utc_now(),
        )
    )
    return result.rowcount == 1

# 用户撤销请假
def cancel_request(db, leave_id, user_id):
    result = db.execute(
        update(LeaveRequest).where(
            LeaveRequest.leave_id == leave_id,
            LeaveRequest.user_id == user_id,
            LeaveRequest.status == "PENDING",
        ).values(status="CANCELLED", updated_at=utc_now())
    )
    return result.rowcount == 1