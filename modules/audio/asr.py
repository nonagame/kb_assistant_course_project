# === 环境与兼容性补丁（必须在所有其他 import 之前执行） ===
import os
import av
import functools

# 1. 设置 HuggingFace 国内镜像源，避免下载模型时连接超时
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# 2. 禁用 Xet 存储后端，防止 401 Unauthorized 错误
os.environ["HF_HUB_DISABLE_XET"] = "1"

# 3. 修复 PyAV 19.x 与 faster-whisper 1.2.1 的 metadata_errors 冲突
# 原理：拦截 av.open，在传参前移除不兼容的 metadata_errors 参数
_original_av_open = av.open

@functools.wraps(_original_av_open)
def _patched_av_open(*args, **kwargs):
    kwargs.pop("metadata_errors", None)
    return _original_av_open(*args, **kwargs)

av.open = _patched_av_open

# 备用补丁：防止 faster-whisper 内部直接调用底层函数绕过上面的拦截
try:
    from av import container
    _original_core_open = container.core.open

    @functools.wraps(_original_core_open)
    def _patched_core_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _original_core_open(*args, **kwargs)

    container.core.open = _patched_core_open
except Exception:
    pass
# ============================================================

from functools import lru_cache
from pathlib import Path

from core.config import settings

# ASR 函数

@lru_cache(maxsize=1)
def get_asr_model():
    # 文本入库、查询和裁剪不需要加载 Whisper 或下载模型。
    from faster_whisper import WhisperModel

    return WhisperModel(
        settings.asr_model,
        device=settings.asr_device,
        compute_type=settings.asr_compute_type,
    )


def transcribe(wav_path: Path) -> tuple[list[dict], str | None]:
    raw_segments, info = get_asr_model().transcribe(str(wav_path), vad_filter=True, beam_size=5)
    segments: list[dict] = []
    for raw in raw_segments:
        text = raw.text.strip()
        start_ms = max(0, round(raw.start * 1000))
        end_ms = max(start_ms + 1, round(raw.end * 1000))
        if text:
            segments.append(
                {
                    "segment_idx": len(segments),
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "text": text,
                }
            )
    return segments, info.language