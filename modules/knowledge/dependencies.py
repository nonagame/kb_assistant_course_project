from functools import lru_cache
from langchain_ollama import OllamaEmbeddings
from core.config import settings

@lru_cache(maxsize=1)
def get_embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(
        model=settings.ollama_embedding_model,
        base_url=settings.ollama_base_url,
    )

@lru_cache(maxsize=1)
def get_llm():
    from langchain_deepseek import ChatDeepSeek

    return ChatDeepSeek(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        api_base="https://api.deepseek.com",
        temperature=0,
        timeout=60,
        max_retries=0,
        extra_body={"thinking": {"type": "disabled"}},
    )

def clear_dependency_cache() -> None:
    get_embeddings.cache_clear()
    get_llm.cache_clear()
    from modules.knowledge.rag.vectorstore import clear_vectorstore_cache
    clear_vectorstore_cache()
