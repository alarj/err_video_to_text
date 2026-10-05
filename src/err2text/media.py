from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen

from err2text.errors import ExitCode, PipelineError
from err2text.models import MediaItem, UrlType

_VOD_URL = re.compile(r"https?://vod\.err\.ee/(?:hls|dash)/vod/([0-9a-f]{32})/(\d+)/", re.IGNORECASE)


def ytdlp_metadata(url: str) -> dict[str, object]:
    try:
        completed = subprocess.run(["yt-dlp", "--dump-single-json", "--skip-download", url], text=True, capture_output=True, check=True)
    except FileNotFoundError as error:
        raise PipelineError(ExitCode.DOWNLOAD_FAILED, "yt-dlp is not installed") from error
    except subprocess.CalledProcessError as error:
        message = error.stderr.strip()[-1000:]
        if "DRM" in message.upper():
            raise PipelineError(ExitCode.DRM_PROTECTED, "ERR media is DRM protected") from error
        raise PipelineError(ExitCode.MEDIA_NOT_FOUND, "Could not resolve media", {"yt_dlp": message}) from error
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise PipelineError(ExitCode.MEDIA_NOT_FOUND, "yt-dlp returned invalid metadata") from error


def media_items(metadata: dict[str, object]) -> list[MediaItem]:
    entries = metadata.get("entries") or [metadata]
    result = []
    for index, item in enumerate(entries, start=1):
        if not isinstance(item, dict):
            continue
        result.append(MediaItem(index=index, title=item.get("title"), canonical_url=item.get("webpage_url") or item.get("original_url"),
                                vod_id=item.get("id"), duration_seconds=item.get("duration"), media_type=item.get("_type", "video")))
    return result


def err_vod_items_from_metadata(metadata: dict[str, object]) -> tuple[list[MediaItem], dict[str, str]]:
    """Extract ERR VOD identity from yt-dlp format URLs of an article/player."""
    seen: dict[str, tuple[str, str]] = {}
    for value in _walk_strings(metadata):
        match = _VOD_URL.search(value)
        if not match:
            continue
        vod_id, version = match.groups()
        # Prefer a master manifest as canonical media URL when it is available.
        previous = seen.get(vod_id)
        if previous is None or ("master.m3u8" in value and "master.m3u8" not in previous[0]):
            seen[vod_id] = (value.replace("http://", "https://", 1), version)
    title = metadata.get("title") if isinstance(metadata.get("title"), str) else None
    items = [MediaItem(index=index, title=title, canonical_url=url, vod_id=vod_id, media_type="video")
             for index, (vod_id, (url, _)) in enumerate(seen.items(), start=1)]
    return items, {vod_id: version for vod_id, (_, version) in seen.items()}


def _walk_strings(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)


def subtitle_url(metadata: dict[str, object]) -> str:
    candidates = metadata.get("subtitles") or metadata.get("automatic_captions") or {}
    for language in ("et", "et-EE", "live_chat"):
        for entry in candidates.get(language, []):
            if entry.get("ext") == "vtt" and entry.get("url"):
                return str(entry["url"])
    for entries in candidates.values():
        for entry in entries:
            if entry.get("ext") == "vtt" and entry.get("url"):
                return str(entry["url"])
    raise PipelineError(ExitCode.MEDIA_NOT_FOUND, "No ERR VTT subtitle source was found")


def download_bytes(url: str) -> bytes:
    try:
        request = Request(url, headers={"User-Agent": "err2text/0.1"})
        with urlopen(request, timeout=60) as response:
            return response.read()
    except OSError as error:
        raise PipelineError(ExitCode.DOWNLOAD_FAILED, "Could not download source", {"url": url}) from error


def download_audio(url: str, output_wav: Path) -> None:
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["yt-dlp", "-f", "bestaudio", "-x", "--audio-format", "wav", "--postprocessor-args", "ffmpeg:-ac 1 -ar 16000", "-o", str(output_wav.with_suffix(".%(ext)s")), url], check=True, capture_output=True, text=True)
    except FileNotFoundError as error:
        raise PipelineError(ExitCode.DOWNLOAD_FAILED, "yt-dlp is not installed", {"tool": "yt-dlp"}) from error
    except subprocess.CalledProcessError as error:
        raise PipelineError(
            ExitCode.DOWNLOAD_FAILED,
            "Could not download and convert audio",
            {"yt_dlp": error.stderr.strip()[-1000:]},
        ) from error
    generated = next(output_wav.parent.glob(f"{output_wav.stem}.*"), None)
    if generated is None:
        raise PipelineError(ExitCode.DOWNLOAD_FAILED, "yt-dlp did not create an audio file")
    generated.replace(output_wav)


def extract_audio_clip(source_wav: Path, output_wav: Path, start_seconds: float, end_seconds: float) -> None:
    """Create a precise, mono 16 kHz WAV excerpt for ASR review."""
    if end_seconds <= start_seconds:
        raise ValueError("audio clip end must be after its start")
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", str(source_wav), "-ss", f"{start_seconds:.3f}",
            "-t", f"{end_seconds - start_seconds:.3f}", "-ac", "1", "-ar", "16000",
            "-c:a", "pcm_s16le", str(output_wav),
        ], check=True, capture_output=True, text=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise PipelineError(ExitCode.WHISPER_REVIEW_FAILED, "Could not extract Whisper review clip") from error
