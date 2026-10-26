from datetime import datetime, timedelta

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from modules.leave.workflow import calculate_days

# 创建服务端对象
mcp = MCPServer("kb_leave_preview")

# 注册工具
@mcp.tool()
def preview_leave_days(start: str, end: str) -> dict[str, str]:
    """预估请假工作日。start、end 格式为 2026-10-12 09:00；不提交申请。"""
    try:
        begin = datetime.strptime(start, "%Y-%m-%d %H:%M")
        finish = datetime.strptime(end, "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise ToolError("时间请写成 2026-10-12 09:00 这样的格式。") from exc

    if finish <= begin:
        raise ToolError("结束时间必须晚于开始时间。")
    if finish - begin > timedelta(days=30):
        raise ToolError("单次跨度不能超过 30 天。")

    days = calculate_days(begin, finish)
    if days <= 0:
        raise ToolError("所选时间没有工作时段。")
    return {"duration_days": str(days)}

if __name__ == "__main__":
    mcp.run()