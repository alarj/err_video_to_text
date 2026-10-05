from __future__ import annotations

import hashlib
import importlib.metadata
import json
import shutil
import time
from difflib import SequenceMatcher
from pathlib import Path

from err2text.config import Settings, WhisperSettings
from err2text.errors import ExitCode, PipelineError
from err2text.media import download_audio, extract_audio_clip
from err2text.output import write_json
from err2text.whisper_review.candidates import select_candidates


def run_review(output_dir: Path, config: Settings, whisper: WhisperSettings, manual_candidates_path: Path | None = None) -> Path:
    """Create a separate review package without modifying the base transcript."""
    transcript = _load_json(output_dir / "transcript.json")
    speakers = _load_json(output_dir / "speakers.json")
    resolver = _load_json(output_dir / "resolver.json")
    selected_media = resolver.get("selected_media")
    if not isinstance(selected_media, dict) or not selected_media.get("canonical_url"):
        raise PipelineError(ExitCode.WHISPER_REVIEW_FAILED, "resolver.json has no canonical media URL for audio review")

    review_dir = output_dir / "review" / "whisper"
    if review_dir.exists() and any(review_dir.iterdir()):
        raise PipelineError(ExitCode.INVALID_ARGUMENT, "Whisper review directory already contains files", {"review_dir": str(review_dir)})
    manual_candidates = _load_manual_candidates(manual_candidates_path) if manual_candidates_path else []
    candidates = select_candidates(
        transcript, speakers.get("segments", []), whisper.short_segment_seconds,
        whisper.max_candidates, manual_candidates,
    )
    if not candidates:
        raise PipelineError(ExitCode.WHISPER_REVIEW_FAILED, "No review candidates were found")

    review_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    work_dir = config.work_root / "whisper-review" / _work_key(output_dir, transcript)
    audio_path = work_dir / "source.wav"
    try:
        download_audio(str(selected_media["canonical_url"]), audio_path)
        model = _load_model(whisper)
        reviewed = [_review_candidate(candidate, audio_path, work_dir, speakers, model, whisper) for candidate in candidates]
    except PipelineError:
        raise
    except Exception as error:
        raise PipelineError(
            ExitCode.WHISPER_REVIEW_FAILED,
            "Whisper review failed",
            {"type": type(error).__name__, "message": str(error)[:1000]},
        ) from error
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    result = {
        "schema_version": "1.0",
        "status": "REVIEW_REQUIRED",
        "source_url": transcript.get("source_url"),
        "title": transcript.get("title"),
        "base_transcript_sha256": _json_digest(transcript),
        "speakers_sha256": speakers.get("sha256"),
        "model": {
            "id": whisper.model,
            "revision": whisper.revision,
            "device": whisper.device,
            "compute_type": whisper.compute_type,
            "language": whisper.language,
            "cpu_threads": whisper.cpu_threads,
            "faster_whisper_version": importlib.metadata.version("faster-whisper"),
        },
        "selection": {
            "context_seconds": whisper.context_seconds,
            "short_segment_seconds": whisper.short_segment_seconds,
            "max_candidates": whisper.max_candidates,
            "manual_candidates_path": str(manual_candidates_path) if manual_candidates_path else None,
        },
        "duration_seconds": round(time.monotonic() - started, 3),
        "candidates": reviewed,
    }
    write_json(review_dir / "whisper_review.json", result)
    (review_dir / "whisper_review.md").write_text(_render_markdown(result), encoding="utf-8")
    return review_dir


def _load_model(settings: WhisperSettings):
    try:
        from faster_whisper import WhisperModel
    except Exception as error:
        raise PipelineError(ExitCode.WHISPER_REVIEW_FAILED, "Could not initialize faster-whisper", {"type": type(error).__name__}) from error
    return WhisperModel(
        settings.model,
        device=settings.device,
        compute_type=settings.compute_type,
        cpu_threads=settings.cpu_threads,
        num_workers=1,
        download_root=str(settings.hf_home / "hub"),
        revision=settings.revision,
    )


def _review_candidate(candidate: dict[str, object], audio_path: Path, work_dir: Path, speakers: dict[str, object], model, settings: WhisperSettings) -> dict[str, object]:
    start, end = float(candidate["start"]), float(candidate["end"])
    clip_start = max(0.0, start - settings.context_seconds)
    clip_end = end + settings.context_seconds
    clip_path = work_dir / "clips" / f"{candidate['id']}.wav"
    extract_audio_clip(audio_path, clip_path, clip_start, clip_end)
    segments, info = model.transcribe(
        str(clip_path), language=settings.language, beam_size=5, word_timestamps=True,
        vad_filter=False, condition_on_previous_text=False,
    )
    whisper_segments = []
    words = []
    for segment in segments:
        segment_words = []
        for word in segment.words or []:
            entry = {"start": round(clip_start + word.start, 3), "end": round(clip_start + word.end, 3), "word": word.word}
            entry["diarization_speaker_id"] = _speaker_for_interval(entry["start"], entry["end"], speakers)
            segment_words.append(entry)
            words.append(entry)
        whisper_segments.append({
            "start": round(clip_start + segment.start, 3),
            "end": round(clip_start + segment.end, 3),
            "text": segment.text.strip(),
            "words": segment_words,
            "avg_logprob": round(segment.avg_logprob, 5),
            "no_speech_prob": round(segment.no_speech_prob, 5),
        })
    whisper_text = " ".join(item["text"] for item in whisper_segments).strip()
    candidate_words = [
        word for word in words
        if max(0.0, min(end, float(word["end"])) - max(start, float(word["start"]))) > 0
    ]
    candidate_text = "".join(str(word["word"]) for word in candidate_words).strip()
    result = dict(candidate)
    result.update({
        "clip_start": round(clip_start, 3),
        "clip_end": round(clip_end, 3),
        "whisper": {
            "detected_language": info.language,
            "language_probability": round(info.language_probability, 5),
            "candidate_text": candidate_text,
            "context_text": whisper_text,
            "text_similarity_to_vtt": round(_text_similarity(str(candidate.get("current_text", "")), candidate_text), 4),
            "segments": whisper_segments,
            "speaker_transitions_at_words": _speaker_transitions(words),
        },
        "decision": "human_review_required",
    })
    return result


def _speaker_for_interval(start: float, end: float, speakers: dict[str, object]) -> str | None:
    choices: dict[str, float] = {}
    for span in speakers.get("segments", []):
        if not isinstance(span, dict) or not span.get("speaker_id"):
            continue
        overlap = max(0.0, min(end, float(span["end"])) - max(start, float(span["start"])))
        if overlap:
            speaker_id = str(span["speaker_id"])
            choices[speaker_id] = choices.get(speaker_id, 0.0) + overlap
    return max(choices, key=choices.get) if choices else None


def _speaker_transitions(words: list[dict[str, object]]) -> list[dict[str, object]]:
    transitions = []
    previous = None
    for word in words:
        speaker = word.get("diarization_speaker_id")
        if speaker and previous and speaker != previous:
            transitions.append({"at": word["start"], "from": previous, "to": speaker, "word": word["word"]})
        if speaker:
            previous = speaker
    return transitions


def _text_similarity(left: str, right: str) -> float:
    normalize = lambda value: " ".join(value.casefold().split())
    return SequenceMatcher(None, normalize(left), normalize(right)).ratio()


def _render_markdown(result: dict[str, object]) -> str:
    lines = [
        f"# Whisperi kontroll: {result.get('title') or 'ERR transkriptsioon'}",
        "",
        "> Kontrollmaterjal. Ükski siin toodud soovitus ei muuda põhitulemuse kõnelejaid automaatselt.",
        "",
    ]
    for candidate in result["candidates"]:
        lines.extend([
            f"## {_format_time(float(candidate['start']))}–{_format_time(float(candidate['end']))}",
            "",
            f"Põhjus: {', '.join(candidate['reasons'])}",
            "",
            f"VTT: {candidate.get('current_text') or '—'}",
            "",
            f"Whisper (sama ajavahemik): {candidate['whisper']['candidate_text'] or '—'}",
            "",
            f"Teksti sarnasus: {candidate['whisper']['text_similarity_to_vtt']}",
            "",
            f"Otsus: {candidate['decision']}",
            "",
        ])
    return "\n".join(lines)


def _format_time(seconds: float) -> str:
    milliseconds = round((seconds % 1) * 1000)
    whole = int(seconds)
    return f"{whole // 3600:02d}:{whole % 3600 // 60:02d}:{whole % 60:02d}.{milliseconds:03d}"


def _load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise PipelineError(ExitCode.WHISPER_REVIEW_FAILED, "Required completed-run artifact is missing", {"path": str(path)})
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise PipelineError(ExitCode.WHISPER_REVIEW_FAILED, "Could not parse completed-run artifact", {"path": str(path)}) from error
    if not isinstance(value, dict):
        raise PipelineError(ExitCode.WHISPER_REVIEW_FAILED, "Completed-run artifact must be a JSON object", {"path": str(path)})
    return value


def _load_manual_candidates(path: Path) -> list[dict[str, object]]:
    data = _load_json(path)
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        raise PipelineError(ExitCode.WHISPER_REVIEW_FAILED, "Manual candidate file must contain a candidates array", {"path": str(path)})
    return candidates


def _work_key(output_dir: Path, transcript: dict[str, object]) -> str:
    return hashlib.sha256(f"{output_dir.resolve()}:{_json_digest(transcript)}".encode()).hexdigest()[:20]


def _json_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
