"""负责选路线"""
import re

from typing import Any, TypedDict
from langgraph.graph import END, START, StateGraph

from modules.knowledge.rag.qa_service import answer_question
from modules.leave.workflow import run_leave
from modules.assistant.react_agent import run_react_agent
from modules.assistant.react_agent import run_knowledge_agent
from modules.assistant.reliability import not_applicable_assessment, review_evidence

class RouterState(TypedDict, total=False):
    # TypedDict列出会用到的字段
    # total = False 表示不要求每一步都有全部字段
    text: str
    question: str
    mode: str
    route: str
    active_route: str
    answer: str
    docs: list
    scores: list[float]
    sources: list[dict]
    retrieval_status: str
    allowed_visibilities: list[str]
    user_id: int
    requester: str
    permissions: list[str]
    pending_leave: dict | None
    leave_id: str | None
    last_leave_id: str | None
    db: Any
    tools_used: list[str]
    # LangGraph新增字段
    plan: str
    knowledge_answer: str
    knowledge_status: str
    leave_answer: str
    leave_status: str
    agents: list[str]
    evidence_assessment: dict | None


def decide_route(state: RouterState) -> str:
    # State是节点间传递的字典
    if state["mode"] != "auto":
        return state["mode"]
    text = state["text"]
    return "leave" if text == "确认" or "申请" in text else "react"


def qa_node(state: RouterState) -> dict:
    return {**answer_question(state["text"], state["allowed_visibilities"]),
            "route": "qa", "leave_id": None}


def leave_node(state: RouterState) -> dict:
    return {**run_leave(state), "route": "leave",
            "docs": [], "scores": [], "sources": []}


def react_node(state: RouterState) -> dict:
    return {**run_react_agent(state), "route": "react", "leave_id": None}

KNOWLEDGE_HINTS = ("制度", "规定", "规则", "政策", "流程", "考勤", "签到", "知识库")
LEAVE_ACTIONS = ("请假记录", "我的请假", "查询请假", "请假列表", "我要请假", "申请请假", "帮我请假")

# 负责选计划
def decide_plan(state: RouterState) -> str:
    mode = state.get("mode", "auto")
    if mode == "qa":
        return "knowledge"
    if mode == "leave":
        return "leave"

    text = state["text"].strip()
    if text in {"确认", "确认提交", "提交"}:
        return "leave"

    asks_knowledge = any(word in text for word in KNOWLEDGE_HINTS)
    asks_leave = any(word in text for word in LEAVE_ACTIONS) or (
        bool(re.search(r"\d{4}-\d{2}-\d{2}", text))
        and any(kind in text for kind in ("年假", "病假", "事假"))
    )
    if asks_knowledge and asks_leave:
        return "both"
    return "leave" if asks_leave else "knowledge"

# 决定计划，清理当次输出
def supervisor_node(state: RouterState) -> dict:
    return {
        "plan": decide_plan(state),
        "answer": "",
        "knowledge_answer": "",
        "knowledge_status": "not_run",
        "leave_answer": "",
        "leave_status": "not_run",
        "docs": [],
        "scores": [],
        "sources": [],
        "tools_used": [],
        "agents": [],
        "leave_id": None,
        "retrieval_status": "routing",
    }


def dispatch_plan(state: RouterState) -> str:
    return state["plan"]

# 复用知识工具，保存独立结果
def knowledge_agent_node(state: RouterState) -> dict:
    result = run_knowledge_agent(state)
    return {
        **result,
        "knowledge_answer": result["answer"],
        "knowledge_status": result["retrieval_status"],
        "agents": [*state["agents"], "knowledge_agent"],
    }


def after_knowledge(state: RouterState) -> str:
    return "leave_agent" if state["plan"] == "both" else "merge"

# 复用请假流程，只更新业务字段
def leave_agent_node(state: RouterState) -> dict:
    own_state = {
        **state,
        "permissions": [
            "leave.view_self" if code == "leave.view_all" else code
            for code in state["permissions"]
        ],
    }
    if state["text"].strip() == "我的请假":
        own_state["text"] = "查询我的请假记录"

    result = run_leave(own_state)
    update = {
        key: result[key]
        for key in ("pending_leave", "last_leave_id", "leave_id", "active_route")
        if key in result
    }
    return {
        **update,
        "leave_answer": result["answer"],
        "leave_status": result["retrieval_status"],
        "agents": [*state["agents"], "leave_agent"],
    }

# 形成对外回答，保留来源
def merge_node(state: RouterState) -> dict:
    plan = state["plan"]
    common = {"active_route": "leave" if state.get("pending_leave") else ""}
    if plan == "leave":
        return {
            **common,
            "answer": state["leave_answer"],
            "route": "leave",
            "retrieval_status": state["leave_status"],
            "evidence_assessment": not_applicable_assessment(),
            "docs": [], "scores": [], "sources": [],
        }
    answer = state["knowledge_answer"]
    if plan == "both":
        answer = f"知识助手：{answer}\n\n请假助手：{state['leave_answer']}"
    return {
        **common,
        "answer": answer,
        "route": "both" if plan == "both" else "qa",
        "retrieval_status": state["knowledge_status"],
    }

def build_router_graph():
    graph = StateGraph(RouterState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("knowledge_agent", knowledge_agent_node)
    graph.add_node("evidence_review", review_evidence)
    graph.add_node("leave_agent", leave_agent_node)
    graph.add_node("merge", merge_node)
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor", dispatch_plan,
        {"knowledge": "knowledge_agent", "both": "knowledge_agent", "leave": "leave_agent"},
    )
    graph.add_edge("knowledge_agent", "evidence_review")
    graph.add_conditional_edges(
        "evidence_review", after_knowledge,
        {"leave_agent": "leave_agent", "merge": "merge"},
    )
    graph.add_edge("leave_agent", "merge")
    graph.add_edge("merge", END)
    return graph.compile()

router_graph = build_router_graph()