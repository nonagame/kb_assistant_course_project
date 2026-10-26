import asyncio
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters
from mcp.types import TextContent

# 服务端的启动参数
def create_server_parameters() -> StdioServerParameters:
    project_root = Path(__file__).resolve().parents[2]
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "modules.assistant.mcp_leave_server"],
        cwd=str(project_root),
    )

# 发现工具
async def main() -> None:
    async with Client(create_server_parameters()) as client:
        tools = (await client.list_tools()).tools
        print("工具：", [tool.name for tool in tools])

        # list_tools()只取得工具定义
        # call_tool()传入工具名和参数，服务端才执行计算

        good = await client.call_tool("preview_leave_days", {
            "start": "2026-10-12 09:00",
            "end": "2026-10-12 18:00",
        })
        print("正常调用是否错误：", good.is_error)
        print("正常结果：", good.structured_content)

        bad = await client.call_tool("preview_leave_days", {
            "start": "2026-10-12 18:00",
            "end": "2026-10-12 09:00",
        })
        print("倒置时间是否错误：", bad.is_error)
        for block in bad.content:
            if isinstance(block, TextContent):
                print("错误说明：", block.text)


if __name__ == "__main__":
    asyncio.run(main())