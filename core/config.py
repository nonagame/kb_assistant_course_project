import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel
from pathlib import Path
# 第一阶段配置：

# 获取项目根路径
PROJECT_ROOT=Path(__file__).resolve().parents[1]
# print(PROJECT_RO0T)
# D:\Code\PythonWorkSpace\kb_assistant_course
load_dotenv(PROJECT_ROOT / ".env")

def _env_bool(name: str, default: bool) -> bool:
    # name:MAIL_STARTTLS
    # value=true
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

def _project_path(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default)).expanduser()
    if not value.is_absolute():
        value = PROJECT_ROOT / value
    return value.resolve()


class Settings(BaseModel):
    # 获取配置
    app_host:str=os.getenv("APP_HOST","127.0.0.1")
    app_port:int=int(os.getenv("APP_PORT","8000"))
    db_host:str=os.getenv("DB_HOST","localhost")
    db_port:int=int(os.getenv("DB_PORT","3306"))
    db_user:str=os.getenv("DB_USER","root")
    db_password:str=os.getenv("DB_PASSWORD","123456")
    db_name:str=os.getenv("DB_NAME","kb_assistant_course")

    # 邮箱配置
    mail_username: str = os.getenv("MAIL_USERNAME", "")
    mail_password: str = os.getenv("MAIL_PASSWORD", "")
    mail_from: str = os.getenv("MAIL_FROM", "")
    mail_port: int = int(os.getenv("MAIL_PORT", "587"))
    mail_server: str = os.getenv("MAIL_SERVER", "smtp.qq.com")
    mail_from_name: str = os.getenv("MAIL_FROM_NAME", "kb_assistant")
    mail_starttls: bool = _env_bool("MAIL_STARTTLS", True)
    mail_ssl_tls: bool = _env_bool("MAIL_SSL_TLS", False)

    # redis配置
    redis_url:str=os.getenv("REDIS_URL", "redis://127.0.0.1:6379")

    # JWT配置
    jwt_secret_key:str=os.getenv("JWT_SECRET_KEY", "classroom-change-this-secret-key-at-least-32-bytes")
    access_token_minutes:int=int(os.getenv("ACCESS_TOKEN_MINUTES", "120"))
    refresh_token_days:int=int(os.getenv("REFRESH_TOKEN_DAYS", "7"))

    # 配置文件存储
    docs_dir:Path=_project_path("DOCS_DIR","./data/docs")

    # chunk配置
    chunk_size:int=int(os.getenv("CHUNK_SIZE", "600"))
    chunk_overlap:int=int(os.getenv("CHUNK_OVERLAP", "100"))

    # Embedding & 向量库配置
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL","http://127.0.0.1:11434")
    ollama_embedding_model: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "qwen3-embedding:4b")
    # 如需换 nomic，请修改 .env 比如：OLLAMA_EMBEDDING_MODEL = nomic-embed-text
    chroma_dir: Path = _project_path("CHROMA_DIR", "./data/chroma")
    collection_name: str = os.getenv("COLLECTION_NAME","enterprise_kb_qwen3_4b_v1")
    embedding_mode: str = "ollama"
    # chroma_mode: str = "embedded"

    # 知识问答相关配置
    llm_fake_mode: bool = _env_bool("LLM_FAKE_MODE", True)
    top_k: int = int(os.getenv("TOP_K", "6"))
    min_relevance: float = float(os.getenv("MIN_RELEVANCE", "0.6"))

    # 请假申请与审批管理相关配置
    # session_backend: str = "memory"
    session_backend: str = os.getenv("SESSION_BACKEND", "memory").strip().lower()
    session_ttl_seconds: int = int(os.getenv("SESSION_TTL_SECONDS", "172800"))

    # ReAct工具智能体相关配置
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")

    # 音频集合的配置
    audio_collection_name: str = os.getenv("AUDIO_COLLECTION_NAME", "enterprise_audio_qwen3_4b_v1")
    # Whisper识别片段和知识库片段
    audio_dir: Path = _project_path("AUDIO_DIR", "./data/audio")
    audio_wav_dir: Path = _project_path("AUDIO_WAV_DIR", "./data/audio_wav")
    audio_max_upload_mb: int = int(os.getenv("AUDIO_MAX_UPLOAD_MB", "100"))
    ffmpeg_cmd: str = os.getenv("FFMPEG_CMD", "ffmpeg")
    ffprobe_cmd: str = os.getenv("FFPROBE_CMD", "ffprobe")
    asr_model: str = os.getenv("ASR_MODEL", "base")
    asr_device: str = os.getenv("ASR_DEVICE", "cpu")
    asr_compute_type: str = os.getenv("ASR_COMPUTE_TYPE", "int8")
    audio_clip_dir: Path = _project_path("AUDIO_CLIP_DIR", "./data/audio_clips")

    # 更新Chroma配置、新增celery配置
    chroma_mode: str = os.getenv("CHROMA_MODE", "embedded").strip().lower()
    chroma_host: str = os.getenv("CHROMA_HOST", "127.0.0.1")
    chroma_port: int = int(os.getenv("CHROMA_PORT", "8001"))
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/1")

    # elasticsearch配置
    elasticsearch_enabled: bool = _env_bool(
        "ELASTICSEARCH_ENABLED", False
    )
    elasticsearch_url: str = os.getenv(
        "ELASTICSEARCH_URL", "http://127.0.0.1:9200"
    ).strip()
    elasticsearch_audio_index: str = os.getenv(
        "ELASTICSEARCH_AUDIO_INDEX", "audio_segments_course_v1"
    ).strip()

    def validate_runtime(self) -> None:
        if not self.db_host or not self.db_user or not self.db_name:
            raise ValueError("DB_HOST、DB_USER、DB_NAME 不能为空")
        if not 1<=self.db_port<=65535:
            raise ValueError("DB_PORT必须在 1 到 65535 之间")
        if self.chunk_size<=0:
            raise ValueError("CHUNK_SIZE 必须大于 0")
        if not 0<=self.chunk_overlap<=self.chunk_size:
            raise ValueError("CHUNK_OVERLAP 必须大于等于 0 且小于 CHUNK_SIZE")
        if self.chroma_mode not in {"embedded", "http"}:
            raise ValueError("CHROMA_MODE 只能为 embedded 或 http")
        if not 1 <= self.chroma_port <= 65535:
            raise ValueError("CHROMA_PORT 必须在 1 到 65535 之间")
        if self.session_backend not in {"memory", "redis"}:
            raise ValueError("SESSION_BACKEND 只能是 memory 或 redis")
        if self.session_ttl_seconds <= 0:
            raise ValueError("SESSION_TTL_SECONDS 必须大于 0")

# 创建配置对象
# setting.app_host
settings = Settings()
settings.validate_runtime()
