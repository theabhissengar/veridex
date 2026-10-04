import json
import shutil
import subprocess
from pathlib import Path

from veridex.domain.errors import DomainError


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise DomainError("ffmpeg_missing", "ffmpeg and ffprobe are required to normalize video")


def probe(path: Path) -> dict:
    require_ffmpeg()
    completed = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise DomainError("ffprobe_failed", completed.stderr.strip() or "ffprobe failed")
    return json.loads(completed.stdout or "{}")


def duration_ms(info: dict) -> int | None:
    raw = (info.get("format") or {}).get("duration")
    if raw is None:
        return None
    return int(float(raw) * 1000)


def extract_frames(source: Path, destination: Path, fps: int = 1) -> list[tuple[int, int, Path]]:
    require_ffmpeg()
    destination.mkdir(parents=True, exist_ok=True)
    pattern = destination / "frame_%04d.jpg"
    completed = subprocess.run(
        ["ffmpeg", "-y", "-i", str(source), "-vf", f"fps={fps}", str(pattern)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise DomainError("ffmpeg_failed", completed.stderr[-500:] or "ffmpeg failed")
    frames = sorted(destination.glob("frame_*.jpg"))
    return [(index, int(index * 1000 / fps), path) for index, path in enumerate(frames)]
