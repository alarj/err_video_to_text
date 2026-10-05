from __future__ import annotations

import hashlib
import time
from pathlib import Path

from err2text.config import Settings
from err2text.diarization import MODEL_ID, run as diarize
from err2text.errors import ExitCode, PipelineError
from err2text.media import download_audio, download_bytes, err_vod_items_from_metadata, media_items, subtitle_url, ytdlp_metadata
from err2text.merge.attribution import build_turns, merge_cues
from err2text.models import RunContext, UrlType
from err2text.names.review import build_review
from err2text.output import write_json, write_markdown
from err2text.resolver.classify import classify_url
from err2text.resolver.article import resolve_err_article, vtt_url_for
from err2text.subtitles.normalize import decode_vtt
from err2text.subtitles.parser import parse_vtt


def process(context: RunContext, config: Settings, video_index: int | None = None) -> Path:
    started = time.monotonic()
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

    work_dir = config.work_root / hashlib.sha256(context.source_url.encode()).hexdigest()[:16]
    audio_path = work_dir / "audio.wav"
    try:
        audio_started = time.monotonic()
        download_audio(selected_url, audio_path)
        context.durations["audio_download_seconds"] = round(time.monotonic() - audio_started, 3)
        diarization_started = time.monotonic()
        spans, speakers_json = diarize(audio_path, context.min_speakers, context.max_speakers, config.torch_threads)
        context.durations["diarization_seconds"] = round(time.monotonic() - diarization_started, 3)
        write_json(output_dir / "speakers.json", speakers_json)
    finally:
        if audio_path.exists() and not context.keep_audio:
            audio_path.unlink()

    segments = merge_cues(cues, spans, context.time_offset_seconds)
    transcript = {"schema_version": "1.0", "source_url": context.source_url, "media_id": selected.vod_id,
                  "language": "et", "pipeline": {"diarization_model": MODEL_ID, "pipeline_version": "0.1.0"},
                  "title": selected.title, "segments": [segment.json() for segment in segments], "turns": build_turns(segments)}
    write_json(output_dir / "speaker_review.json", build_review(segments, context.source_url))
    write_json(output_dir / "transcript.json", transcript)
    slug = _slug(selected.title or selected.vod_id or "transcript")
    write_markdown(output_dir / f"{slug}-transcript.md", selected.title or "ERR transkriptsioon", segments)
    context.durations["total_seconds"] = round(time.monotonic() - started, 3)
    write_json(output_dir / "run_metadata.json", {"schema_version": "1.0", "status": "SUCCEEDED", "parameters": {
        "time_offset_seconds": context.time_offset_seconds, "min_speakers": context.min_speakers,
        "max_speakers": context.max_speakers, "no_cache": context.no_cache}, "durations": context.durations,
        "audio_retained": context.keep_audio, "output_dir": str(output_dir)})
    return output_dir


def _slug(value: str) -> str:
    import re
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "transcript"
