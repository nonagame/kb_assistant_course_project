import sys
sys.path.insert(0, r"D:\Code\PythonWorkSpace\kb_assistant_course")

from modules.knowledge.rag.vectorstore import get_embeddings, get_vectorstore

# ✅ 用你项目真实的 embedding 函数
embeddings = get_embeddings()

# 测试单条查询嵌入
query_vec = embeddings.embed_query("如何申请年假？")
print(f"向量维度: {len(query_vec)}")

# 测试向量检索
vs = get_vectorstore()
results = vs.similarity_search("如何申请年假？", k=3)
for doc in results:
    print(f"[{doc.metadata.get('source', '?')}] {doc.page_content[:80]}...")

