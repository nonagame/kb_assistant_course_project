import json
import subprocess
from pathlib import Path

from core.config import settings

# 媒体转换函数

def _run(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )


def probe_duration_ms(source: Path) -> int:
    result = _run(
        [settings.ffprobe_cmd, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(source)]
    )
    seconds = float(json.loads(result.stdout)["format"]["duration"])
    return max(1, round(seconds * 1000))


def convert_to_wav(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    _run([settings.ffmpeg_cmd, "-y", "-i", str(source), "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(target)])

# 裁剪函数
def clip_to_mp3(source: Path, target: Path, start_ms: int, end_ms: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            settings.ffmpeg_cmd, "-y", "-ss", f"{start_ms / 1000:.3f}", "-i", str(source),
            "-t", f"{(end_ms - start_ms) / 1000:.3f}", "-vn", "-codec:a", "libmp3lame", str(target),
        ]
    )