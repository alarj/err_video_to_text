from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable

from err2text.config import Settings
from err2text.diarization import MODEL_ID, run as diarize
from err2text.errors import ExitCode, PipelineError
from err2text.media import download_audio, download_bytes, err_vod_items_from_metadata, media_items, subtitle_url, ytdlp_metadata
from err2text.merge.attribution import build_turns, merge_cues
from err2text.models import MediaItem, RunContext, UrlType
from err2text.names.review import build_review
from err2text.output import write_json, write_markdown
from err2text.resolver.classify import classify_url
from err2text.resolver.article import resolve_err_article, vtt_url_for
from err2text.subtitles.normalize import decode_vtt
from err2text.subtitles.parser import parse_vtt


@dataclass
class PreparedMedia:
    output_dir: Path
    work_dir: Path
    audio_path: Path
    selected: MediaItem
    cues: list


def process(
    context: RunContext,
    config: Settings,
    video_index: int | None = None,
    on_stage: Callable[[str], None] | None = None,
) -> Path:
    prepared = prepare_media(context, config, video_index)
    if on_stage is not None:
        on_stage("DIARIZING")
    return complete_diarization(prepared, context, config)


def prepare_media(context: RunContext, config: Settings, video_index: int | None = None) -> PreparedMedia:
    output_dir = Path(context.output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise PipelineError(ExitCode.INVALID_ARGUMENT, "Output directory already contains files", {"output_dir": str(output_dir)})
    output_dir.mkdir(parents=True, exist_ok=True)
    url_type = classify_url(context.source_url)
    article_versions: dict[str, str] = {}
    metadata = ytdlp_metadata(context.source_url)
    if url_type == UrlType.ERR_ARTICLE:
        items, article_versions = err_vod_items_from_metadata(metadata)
        if not items:
            items, article_versions = resolve_err_article(context.source_url)
    else:
        items = media_items(metadata)
    resolver = {"schema_version": "1.0", "source_url": context.source_url, "url_type": url_type,
                "resolver_version": "0.1.0", "media_items": [item.__dict__ for item in items]}
    if not items:
        raise PipelineError(ExitCode.ARTICLE_WITHOUT_MEDIA, "No related media was found")
    if len(items) > 1 and video_index is None:
        write_json(output_dir / "resolver.json", resolver)
        raise PipelineError(ExitCode.INVALID_ARGUMENT, "Multiple media items found; pass --video-index", {"media_items": resolver["media_items"]})
    selection = video_index or 1
    if selection < 1 or selection > len(items):
        raise PipelineError(ExitCode.INVALID_ARGUMENT, "--video-index is outside discovered media item range")
    selected = items[selection - 1]
    resolver["selected_media"] = selected.__dict__
    selected_url = selected.canonical_url or context.source_url
    if url_type == UrlType.ERR_ARTICLE:
        vtt_url = vtt_url_for(selected, article_versions[selected.vod_id or ""])
    else:
        selected_metadata = metadata if len(items) == 1 else ytdlp_metadata(selected_url)
        vtt_url = subtitle_url(selected_metadata)
    resolver["vtt_url"] = vtt_url
    write_json(output_dir / "resolver.json", resolver)

    raw_vtt = download_bytes(vtt_url)
    (output_dir / "original.vtt").write_bytes(raw_vtt)
    normalized = decode_vtt(raw_vtt)
    (output_dir / "normalized.vtt").write_text(normalized, encoding="utf-8")
    cues = parse_vtt(normalized)
    if not cues:
        raise PipelineError(ExitCode.MERGE_FAILED, "VTT contains no usable cues")

    work_key = context.work_key or hashlib.sha256(context.source_url.encode()).hexdigest()[:16]
    work_dir = config.work_root / work_key
    audio_path = work_dir / "audio.wav"
    audio_started = time.monotonic()
    download_audio(selected_url, audio_path)
    audio_duration = round(time.monotonic() - audio_started, 3)
    context.durations["audio_download_seconds"] = audio_duration
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "prepared.json").write_text(json.dumps({"audio_download_seconds": audio_duration}), encoding="utf-8")
    return PreparedMedia(output_dir=output_dir, work_dir=work_dir, audio_path=audio_path, selected=selected, cues=cues)


def resume_prepared(context: RunContext, config: Settings) -> PreparedMedia:
    output_dir = Path(context.output_dir)
    resolver_path = output_dir / "resolver.json"
    normalized_path = output_dir / "normalized.vtt"
    if not resolver_path.is_file() or not normalized_path.is_file():
        raise PipelineError(ExitCode.DOWNLOAD_FAILED, "Prepared media metadata is missing")
    resolver = json.loads(resolver_path.read_text(encoding="utf-8"))
    selected_data = resolver.get("selected_media")
    if not isinstance(selected_data, dict):
        raise PipelineError(ExitCode.DOWNLOAD_FAILED, "Prepared media selection is missing")
    selected = MediaItem(
        index=int(selected_data["index"]), title=selected_data.get("title"),
        canonical_url=selected_data.get("canonical_url"), vod_id=selected_data.get("vod_id"),
        duration_seconds=selected_data.get("duration_seconds"), media_type=selected_data.get("media_type"),
    )
    work_key = context.work_key or hashlib.sha256(context.source_url.encode()).hexdigest()[:16]
    work_dir = config.work_root / work_key
    audio_path = work_dir / "audio.wav"
    if not audio_path.is_file():
        raise PipelineError(ExitCode.DOWNLOAD_FAILED, "Prepared audio is missing")
    state_path = work_dir / "prepared.json"
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        context.durations.update({"audio_download_seconds": float(state.get("audio_download_seconds", 0.0))})
    cues = parse_vtt(normalized_path.read_text(encoding="utf-8"))
    if not cues:
        raise PipelineError(ExitCode.MERGE_FAILED, "VTT contains no usable cues")
    return PreparedMedia(output_dir=output_dir, work_dir=work_dir, audio_path=audio_path, selected=selected, cues=cues)


def complete_diarization(prepared: PreparedMedia, context: RunContext, config: Settings) -> Path:
    started = time.monotonic()
    try:
        diarization_started = time.monotonic()
        spans, speakers_json = diarize(prepared.audio_path, context.min_speakers, context.max_speakers, config.torch_threads)
        context.durations["diarization_seconds"] = round(time.monotonic() - diarization_started, 3)
        write_json(prepared.output_dir / "speakers.json", speakers_json)
    finally:
        if prepared.audio_path.exists() and not context.keep_audio:
            prepared.audio_path.unlink()
        state_path = prepared.work_dir / "prepared.json"
        if state_path.exists():
            state_path.unlink()

    segments = merge_cues(prepared.cues, spans, context.time_offset_seconds)
    transcript = {"schema_version": "1.0", "source_url": context.source_url, "media_id": prepared.selected.vod_id,
                  "language": "et", "pipeline": {"diarization_model": MODEL_ID, "pipeline_version": "0.1.0"},
                  "title": prepared.selected.title, "segments": [segment.json() for segment in segments], "turns": build_turns(segments)}
    write_json(prepared.output_dir / "speaker_review.json", build_review(segments, context.source_url))
    write_json(prepared.output_dir / "transcript.json", transcript)
    slug = _slug(prepared.selected.title or prepared.selected.vod_id or "transcript")
    write_markdown(prepared.output_dir / f"{slug}-transcript.md", prepared.selected.title or "ERR transkriptsioon", segments)
    context.durations["total_seconds"] = round(time.monotonic() - started, 3)
    write_json(prepared.output_dir / "run_metadata.json", {"schema_version": "1.0", "status": "SUCCEEDED", "parameters": {
        "time_offset_seconds": context.time_offset_seconds, "min_speakers": context.min_speakers,
        "max_speakers": context.max_speakers, "no_cache": context.no_cache}, "durations": context.durations,
        "audio_retained": context.keep_audio, "output_dir": str(prepared.output_dir)})
    return prepared.output_dir


def _slug(value: str) -> str:
    import re
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "transcript"
