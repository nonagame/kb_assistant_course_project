from fastapi import HTTPException

from modules.leave import repository

# 当前用户查询权限
def get_requests(db, user):
    if not {"leave.view_self", "leave.view_all"}.intersection(user.permissions):
        raise HTTPException(status_code=403, detail="缺少请假查询权限")
    return {"items": repository.list_requests(db, user.id, "leave.view_all" in user.permissions)}

# 审批/拒绝接口
def decide_request(db, leave_id, user, *, new_status, reason):
    required = {"APPROVED": "leave.approve", "REJECTED": "leave.reject"}[new_status]
    if required not in user.permissions:
        raise HTTPException(status_code=403, detail="缺少审批权限")
    changed = repository.update_status(
        db, leave_id, new_status=new_status, approver_user_id=user.id, reason=reason,
    )
    if not changed:
        raise HTTPException(status_code=409, detail="请假单不存在或状态不是 PENDING")
        # 409：资源冲突
    db.commit()
    return {"leave_id": leave_id, "status": new_status}

# 撤销接口
def cancel_request(db, leave_id, user):
    if "leave.cancel" not in user.permissions:
        raise HTTPException(status_code=403, detail="缺少撤销权限")
    if not repository.cancel_request(db, leave_id, user.id):
        raise HTTPException(status_code=409, detail="只能撤销自己的 PENDING 请假单")
    db.commit()
    return {"leave_id": leave_id, "status": "CANCELLED"}