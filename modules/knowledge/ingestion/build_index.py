# 实现单文件增量索引和全量重建

import hashlib
import json
from pathlib import Path
from core.config import settings
from modules.knowledge.ingestion.loader import load_docs, load_file, split_docs
from modules.knowledge.rag.vectorstore import get_vectorstore, reset_collection

# 用正文和 metadata 生成稳定 SHA-256 编号，稳定编号可以降低重复数据风险，也方便以后扩展
def _chunk_id(document) -> str:
    payload = {
        "page_content": document.page_content,
        "metadata": document.metadata,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf8")
    return hashlib.sha256(raw).hexdigest()

# 调用 dependencies.py 的嵌入模型，为文本块生成向量，并保存正文、metadata 与向量
def _add_chunks(chunks) -> int:
    if not chunks:
        return 0
    ids = [_chunk_id(document) for document in chunks]
    get_vectorstore().add_documents(documents=chunks, ids=ids)
    return len(ids)

# 只读取一份文件，用于日常上传以及单份文档重新索引
def index_document(path: str | Path) -> int:
    file_path = Path(path).resolve()
    documents = load_file(file_path, settings.docs_dir.resolve())
    chunks = split_docs(documents)
    return _add_chunks(chunks)

# 扫描整个 `DOCS_DIR`，先删除旧 collection，再全量构建，只给显式重建使用
def index_documents() -> int:
    documents = load_docs(settings.docs_dir)
    chunks = split_docs(documents)
    reset_collection()
    return _add_chunks(chunks)