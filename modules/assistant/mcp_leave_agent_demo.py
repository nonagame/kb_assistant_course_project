import asyncio
import json

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from mcp import Client
from mcp.types import TextContent, Tool

from modules.assistant.mcp_leave_client import create_server_parameters
from modules.knowledge.dependencies import get_llm

# DeepSeek 使用 MCP 工具

def to_model_tool(tool: Tool) -> dict:
    # 把MCP工具定义转换为模型能理解的结构
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "预估请假工作日，不提交申请。",
            "parameters": tool.input_schema,
        },
    }

async def ask_with_tool(client: Client, tool: Tool, question: str) -> None:
    llm = get_llm()
    tool_model = llm.bind_tools([to_model_tool(tool)])
    messages = [
        SystemMessage(content=(
            "预估请假时长必须先调用工具，不要自行计算。"
            "取得结果后说明预估天数，并说明未提交申请。"
            "若工具报错，说明错误原因，不要编造天数。"
        )),
        HumanMessage(content=question),
    ]

    first = await tool_model.ainvoke(messages)
    if not first.tool_calls:
        print("未完成：模型没有请求工具，本次不能算 MCP 调用成功。")
        return

    messages.append(first)
    for call in first.tool_calls:
        if call["name"] != tool.name:
            raise RuntimeError("模型请求了未开放的工具。")
        print("模型请求工具：", call["name"], call["args"])
        result = await client.call_tool(tool.name, call["args"])

        if result.is_error:
            detail = "\n".join(
                block.text for block in result.content
                if isinstance(block, TextContent)
            )
            payload = {"error": detail or "工具执行失败。"}
        else:
            payload = result.structured_content

        content = json.dumps(payload, ensure_ascii=False)
        print("MCP 返回：", content)
        messages.append(ToolMessage(
            content=content,
            tool_call_id=call["id"],
        ))

    final = await llm.ainvoke(messages)
    if final.tool_calls or not final.content:
        print("未完成：模型未给出最终回答。")
        return
    print("模型回答：", final.content)

# 发现工具
async def main() -> None:
    async with Client(create_server_parameters()) as client:
        tools = (await client.list_tools()).tools
        tool = next(
            (item for item in tools if item.name == "preview_leave_days"),
            None,
        )
        if tool is None:
            raise RuntimeError("服务端没有提供 preview_leave_days 工具。")
        await ask_with_tool(
            client,
            tool,
            "请预估 2026-10-12 09:00 到 2026-10-12 18:00 的请假时长。",
        )


if __name__ == "__main__":
    asyncio.run(main())