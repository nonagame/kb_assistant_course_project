import re
import uuid
from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from modules.leave.repository import create_request, get_request, list_recent


DATE = r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}"
DATE_RANGE = re.compile(rf"({DATE})\s*(?:到|至)\s*({DATE})")

# 节点函数设计：把申请、确认、查询分成三个函数

def _answer(text, status):
    return {"answer": text, "retrieval_status": status, "leave_id": None}

# 工作时间计算
def calculate_days(start, end):
    seconds = 0
    current = start.date()
    while current <= end.date():
        if current.weekday() < 5:
            for begin_hour, end_hour in ((9, 12), (13, 18)):
                begin = max(start, datetime.combine(current, time(begin_hour)))
                finish = min(end, datetime.combine(current, time(end_hour)))
                seconds += max(0, int((finish - begin).total_seconds()))
        current += timedelta(days=1)
    return (Decimal(seconds) / Decimal(28800)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

# 请假申请 产生 `pending_leave`
def apply_node(state):
    if "leave.apply" not in state["permissions"]:
        return _answer("没有请假申请权限。", "permission_denied")
    text = state["text"]
    cleared = {"pending_leave": None, "last_leave_id": None}
    match = DATE_RANGE.search(text)
    types = {"年假": "annual", "病假": "sick", "事假": "personal"}
    leave_type = next((code for name, code in types.items() if name in text), None)
    if not match or not leave_type:
        return {**cleared, **_answer("请填写：年假 2026-10-12 09:00 到 2026-10-12 18:00 原因：休息", "missing_fields")}
    try:
        start, end = (datetime.fromisoformat(value) for value in match.groups())
    except ValueError:
        return {**cleared, **_answer("日期无效，请按示例填写。", "validation_failed")}
    if not start < end <= start + timedelta(days=30):
        return {**cleared, **_answer("开始须早于结束，单次跨度最多 30 天。", "validation_failed")}
    days = calculate_days(start, end)
    if days <= 0:
        return {**cleared, **_answer("所选时间没有工作时段。", "validation_failed")}
    reason = re.search(r"原因[：:]?\s*(.+)$", text)
    pending = {
        "leave_id": f"LV-{uuid.uuid4().hex[:24]}", "leave_type": leave_type,
        "start_time": start.isoformat(sep=" ", timespec="minutes"),
        "end_time": end.isoformat(sep=" ", timespec="minutes"),
        "duration_days": str(days), "reason": reason.group(1).strip() if reason else None,
    }
    answer = (
        f"请确认：{leave_type}，{pending['start_time']} 到 {pending['end_time']}，"
        f"共 {days} 天，原因：{pending['reason'] or '未填写'}。回复“确认”提交。"
    )
    return {**cleared, **_answer(answer, "leave_pending"), "pending_leave": pending}

# 确认提交 使用待办单号创建记录并提交
def confirm_node(state):
    if "leave.apply" not in state["permissions"]:
        return _answer("没有请假申请权限。", "permission_denied")
    pending = state.get("pending_leave")
    if not pending:
        leave_id = state.get("last_leave_id")
        if leave_id:
            return {**_answer(f"该申请已提交：{leave_id}", "leave_already_created"), "leave_id": leave_id}
        return _answer("当前没有待确认申请。", "no_pending_leave")
    leave_id = pending["leave_id"]
    created = get_request(state["db"], leave_id) is None
    if created:
        create_request(
            state["db"], leave_id=leave_id, user_id=state["user_id"],
            requester=state["requester"], pending=pending,
        )
        state["db"].commit()
    return {
        **_answer(f"请假申请已提交：{leave_id}", "leave_created" if created else "leave_already_created"),
        "pending_leave": None, "last_leave_id": leave_id, "leave_id": leave_id,
    }

# 查询记录 复用数据库查询
def list_node(state):
    permissions = state["permissions"]
    if not {"leave.view_self", "leave.view_all"}.intersection(permissions):
        return _answer("没有请假查询权限。", "permission_denied")
    rows = list_recent(state["db"], state["user_id"], "leave.view_all" in permissions)
    if not rows:
        return _answer("暂无请假记录。", "leave_list_empty")
    lines = [f"{row['leave_id']} | {row['requester']} | {row['leave_type']} | {row['status']}" for row in rows]
    return _answer("最近请假记录：\n" + "\n".join(lines), "leave_list")

# 路由分发：入口函数 根据一句话选择函数
def run_leave(state):
    text = state["text"].strip()
    if text in {"确认", "确认提交", "提交"}:
        return confirm_node(state)
    if any(word in text for word in ("查询", "记录", "列表")):
        return list_node(state)
    return apply_node(state)