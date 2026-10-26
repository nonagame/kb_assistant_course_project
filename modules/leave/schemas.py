from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

# 查询需要的数据格式
class LeaveOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    leave_id: str
    user_id: int
    requester: str
    leave_type: str
    start_time: datetime
    end_time: datetime
    duration_days: Decimal
    reason: str | None
    status: str
    approver_user_id: int | None
    decision_reason: str | None
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime


class LeaveListOut(BaseModel):
    items: list[LeaveOut]

# 聊天请求和响应模型
class LeaveChatIn(BaseModel):
    text: str
    session_id: str | None = None


class LeaveChatOut(BaseModel):
    answer: str
    retrieval_status: str
    session_id: str
    leave_id: str | None = None

# 审批接口的数据格式
class DecisionIn(BaseModel):
    reason: str | None = None


class LeaveActionOut(BaseModel):
    leave_id: str
    status: str