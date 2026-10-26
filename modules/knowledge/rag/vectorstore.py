# Chroma的打开、计数和按来源删除函数

import chromadb
from functools import lru_cache
from langchain_chroma import Chroma
from core.config import settings
from modules.knowledge.dependencies import get_embeddings

@lru_cache(maxsize=1)

# 项目同时支持 embedded / http 两种 Chroma 模式
def get_chroma_client():
    if settings.chroma_mode == "http":
        return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(settings.chroma_dir))

def _collection_names() -> set[str]:
    names: set[str] = set()
    for item in get_chroma_client().list_collections():
        names.add(item if isinstance(item, str) else item.name)
    return names

def _get_existing_collection():
    client = get_chroma_client()
    if settings.collection_name not in _collection_names():
        return None
    return client.get_collection(settings.collection_name)

# 与计数、删除函数共用同一个 Chroma client
def get_vectorstore() -> Chroma:
    return Chroma(
        client=get_chroma_client(),
        collection_name=settings.collection_name,
        embedding_function=get_embeddings(),
        collection_metadata={"hnsw:space": "cosine"},
    )

# 只给后面的显式全量重建使用，日常上传、修改可见范围和删除文档不再清空整个集合
def reset_collection() -> None:
    client = get_chroma_client()
    if settings.collection_name in _collection_names():
        client.delete_collection(settings.collection_name)

# 查询整个集合的文本块数
def collection_count() -> int:
    collection = _get_existing_collection()
    return 0 if collection is None else collection.count()

# 只统计某个 `source_path` 的块数
def source_count(source_path: str) -> int:
    collection = _get_existing_collection()
    if collection is None:
        return 0
    result = collection.get(where={"source_path": source_path}, include=[])
    return len(result["ids"])

# 先按元数据找到该来源的全部块编号，再只删除这些块，因此不会影响其他已索引文档
def delete_source(source_path: str) -> int:
    collection = _get_existing_collection()
    if collection is None:
        return 0
    result = collection.get(where={"source_path": source_path}, include=[])
    ids = result["ids"]
    if ids:
        collection.delete(ids=ids)
    return len(ids)

def clear_vectorstore_cache() -> None:
    get_chroma_client.cache_clear()


# 音频向量函数
def get_audio_vectorstore() -> Chroma:
    return Chroma(
        client=get_chroma_client(),
        collection_name=settings.audio_collection_name,
        embedding_function=get_embeddings(),
        collection_metadata={"hnsw:space": "cosine"},
    )


def delete_audio_vectors(audio_id: str) -> None:
    if settings.audio_collection_name in _collection_names():
        get_chroma_client().get_collection(settings.audio_collection_name).delete(
            where={"audio_id": audio_id}
        )


def audio_collection_count() -> int:
    if settings.audio_collection_name not in _collection_names():
        return 0
    return get_chroma_client().get_collection(settings.audio_collection_name).count()