from core.config import settings
from modules.knowledge.rag.vectorstore import get_vectorstore


# 检索函数：从 Chroma 查询、筛掉低相关片段、整理来源
# 根据问题查询charmdb中的数据，如果有，返回字典；如果没有，告诉用户:no_relevant_evidence
def retrieve_knowledge(question: str, allowed_visibilities: list[str], *, k=None) -> dict:
    # 定义返回的数据 docs文档: 查到的答案 scores:分数 sources: 来源
    result = {"docs": [], "scores": [], "sources": [],
              "retrieval_status": "no_relevant_evidence"}
    if not allowed_visibilities:
        return result

    matches = get_vectorstore().similarity_search_with_relevance_scores(
        question, k=k or settings.top_k,
        filter={"visibility": {"$in": allowed_visibilities}},
    )

    # 去重集合：记录已经加入结果的 content 指纹
    seen = set()

    for document, score in matches:
        if score < settings.min_relevance:
            continue
        # 用内容前200字符做指纹去重（足够区分不同段落，又避免全文哈希的开销）
        content_key = document.page_content[:200]
        if content_key in seen:
            continue  # 跳过重复片段（public 版本会被过滤掉）
        seen.add(content_key)
        result["docs"].append(document)
        result["scores"].append(round(min(1.0, max(0.0, score)), 4))
        result["sources"].append({
            "index": len(result["sources"]) + 1,
            "source": document.metadata["source"],
            "page": document.metadata.get("page"),
            "visibility": document.metadata["visibility"],
        })
    if result["docs"]:
        result["retrieval_status"] = "matched"
    return result