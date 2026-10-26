# scripts/check_duplicates.py
from modules.knowledge.rag.vectorstore import get_vectorstore
from collections import Counter

vs = get_vectorstore()
all_data = vs.get(include=["metadatas"])
sources = [m["source"] for m in all_data["metadatas"]]
dupes = {s: c for s, c in Counter(sources).items() if c > 1}

print(f"总文档数: {len(sources)}, 重复文件: {len(dupes)}")
for s, c in sorted(dupes.items(), key=lambda x: -x[1]):
    print(f"  {s}: {c} 次")