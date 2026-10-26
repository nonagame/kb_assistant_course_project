import re


MIN_RELEVANCE = 0.45
HIGH_RELEVANCE = 0.65


def not_applicable_assessment() -> dict:
    return {
        "level": "not_applicable",
        "matched_chunks": 0,
        "distinct_sources": 0,
        "top_relevance": None,
        "citation_valid": False,
        "needs_human_review": False,
        "reasons": ["当前结果来自请假业务规则，不使用向量证据评分"],
    }

def has_valid_citations(answer: str, sources: list[dict]) -> bool:
    cited = {int(number) for number in re.findall(r"\[(\d+)\]", answer)}
    indexes = {source.get("index") for source in sources}
    return bool(cited) and cited.issubset(indexes)

def review_evidence(state: dict) -> dict:
    # 1. 读取知识助手本次输出，并检查引用与权限。
    sources = state["sources"]
    scores = state["scores"]
    status = state["knowledge_status"]
    citation_valid = has_valid_citations(state["knowledge_answer"], sources)
    allowed = set(state["allowed_visibilities"])
    permission_valid = all(source.get("visibility") in allowed for source in sources)

    # 2. 收集所有证据合法性问题。
    problems = []
    if status != "matched":
        problems.append(f"知识工具未取得证据：{status}")
    if not sources:
        problems.append("没有检索到可用证据")
    if not permission_valid:
        problems.append("存在当前用户不可见的来源")
    if not citation_valid:
        problems.append("回答缺少有效来源引用")
    if len(scores) != len(sources):
        problems.append("相似度与来源数量不一致")

    # MIN_RELEVANCE 属于检索层；这里只验证上游是否遵守最低召回约定。
    if scores and any(score < MIN_RELEVANCE for score in scores):
        problems.append("检索结果违反最低相关度约定")

    # 3. 计算统计值。合法性通过后，只用 HIGH_RELEVANCE 区分 high / medium。
    top = max(scores) if scores else None
    distinct = len({source["source"] for source in sources if source.get("source")})

    if problems:
        level = "low"
    elif top is not None and top >= HIGH_RELEVANCE:
        level = "high"
    else:
        level = "medium"

    if problems:
        reasons = problems
    elif level == "high":
        reasons = ["证据合法性检查通过，且相关度达到高可靠性门槛"]
    else:
        reasons = ["证据合法性检查通过，相关度未达到 high 门槛"]

    if distinct >= 2:
        reasons.append(f"检索到 {distinct} 个不同来源，可作为辅助交叉参考")

    assessment = {
        "level": level,
        "matched_chunks": len(sources),
        "distinct_sources": distinct,
        "top_relevance": round(top, 4) if top is not None else None,
        "citation_valid": citation_valid,
        "needs_human_review": level == "low",
        "reasons": reasons,
    }

    # 4. 只有合法性审核失败时才拒答并清空证据。
    update = {
        "evidence_assessment": assessment,
        "agents": [*state["agents"], "evidence_reviewer"],
    }
    if level == "low":
        refusal = "当前证据未通过校验，暂无法可靠回答；请补充问题或联系人工核对。"
        update.update({
            "answer": refusal,
            "knowledge_answer": refusal,
            "docs": [],
            "scores": [],
            "sources": [],
            "knowledge_status": "review_rejected",
            "retrieval_status": "review_rejected",
        })
    return update