import json
import subprocess
from dataclasses import dataclass

from app.core.platform_specs import PlatformVideoSpec


class VideoProcessingError(Exception):
    pass


@dataclass(frozen=True)
class VideoProbeResult:
    duration_seconds: float
    width: int
    height: int


def probe_video(path: str) -> VideoProbeResult:
    """Reads container/stream metadata via ffprobe. Raises VideoProcessingError on
    anything that isn't a readable video (corrupt upload, wrong format, etc.) so the
    caller can mark the asset FAILED with a useful message instead of crashing.
    """
    args = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        path,
    ]
    try:
        result = subprocess.run(args, capture_output=True, check=True, timeout=60)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace") if getattr(exc, "stderr", None) else str(exc)
        raise VideoProcessingError(f"ffprobe failed: {stderr}") from exc

    try:
        data = json.loads(result.stdout)
        stream = data["streams"][0]
        duration = float(data["format"]["duration"])
        return VideoProbeResult(duration_seconds=duration, width=int(stream["width"]), height=int(stream["height"]))
    except (KeyError, IndexError, ValueError) as exc:
        raise VideoProcessingError(f"Could not parse ffprobe output: {result.stdout!r}") from exc


def transcode_for_platform(input_path: str, output_path: str, spec: PlatformVideoSpec) -> VideoProbeResult:
    """Crops/scales to the platform's target aspect ratio (center-crop after an
    aspect-preserving upscale, so no letterboxing) and hard-trims to its max
    duration. Runs as an argument list (never shell=True) so nothing in a
    filename or path can be interpreted as a shell command.
    """
    scale_crop = f"scale={spec.width}:{spec.height}:force_original_aspect_ratio=increase,crop={spec.width}:{spec.height}"
    args = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-t",
        str(spec.max_duration_seconds),
        "-vf",
        scale_crop,
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-b:v",
        f"{spec.video_bitrate_kbps}k",
        "-c:a",
        "aac",
        "-b:a",
        f"{spec.audio_bitrate_kbps}k",
        "-movflags",
        "+faststart",
        output_path,
    ]
    try:
        subprocess.run(args, capture_output=True, check=True, timeout=300)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace") if getattr(exc, "stderr", None) else str(exc)
        raise VideoProcessingError(f"ffmpeg transcode failed: {stderr}") from exc

    return probe_video(output_path)
