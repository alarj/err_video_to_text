from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from err2text.errors import ExitCode, PipelineError
from err2text.output import format_time, write_json

_WORD_RE = re.compile(r"[0-9A-Za-zÕÄÖÜŠŽõäöüšž]+")
_SENTENCE_END_RE = re.compile(r"[.!?][\"'”’)]*$")
_EDGE_MARGIN_SECONDS = 0.5
_SENTENCE_WINDOW_SECONDS = 2.0


def run_review(output_dir: Path, case_file: Path) -> Path:
    """Evaluate a text-only baseline without audio, CTC, or expected labels."""
    transcript = _load_json(output_dir / "transcript.json")
    speakers = _load_json(output_dir / "speakers.json")
    cases = _load_cases(case_file)
    review_dir = output_dir / "review" / "sentence-boundary" / case_file.stem
    if review_dir.exists() and any(review_dir.iterdir()):
        raise PipelineError(ExitCode.INVALID_ARGUMENT, "Sentence-boundary review directory already contains files", {"review_dir": str(review_dir)})

    by_id = {str(item.get("id")): item for item in _items(transcript.get("segments")) if item.get("id")}
    referenced = [str(item.get(key)) for item in cases for key in ("segment_id", "before_segment_id", "after_segment_id") if item.get(key)]
    missing = sorted({segment_id for segment_id in referenced if segment_id not in by_id})
    if missing:
        raise PipelineError(ExitCode.INVALID_ARGUMENT, "Case file refers to unknown transcript segment", {"segment_ids": missing})

    speaker_spans = sorted(_items(speakers.get("segments")), key=lambda item: (float(item["start"]), float(item["end"])))
    reviewed = [_review_case(case, by_id, speaker_spans) for case in cases]
    result = {
        "schema_version": "1.0",
        "status": "REVIEW_REQUIRED",
        "method": {
            "name": "model_free_sentence_boundary_baseline",
            "uses_audio": False,
            "uses_ctc_alignment": False,
            "uses_human_annotation_for_prediction": False,
            "edge_margin_seconds": _EDGE_MARGIN_SECONDS,
            "sentence_window_seconds": _SENTENCE_WINDOW_SECONDS,
            "sentence_time_estimate": "cue duration distributed linearly across lexical-word positions",
        },
        "source_url": transcript.get("source_url"),
        "title": transcript.get("title"),
        "base_transcript_sha256": _json_digest(transcript),
        "speakers_sha256": speakers.get("sha256"),
        "case_file": str(case_file),
        "cases": reviewed,
        "summary": _summary(reviewed),
        "decision": "human_review_required",
    }
    review_dir.mkdir(parents=True, exist_ok=True)
    write_json(review_dir / "sentence_boundary_review.json", result)
    (review_dir / "sentence_boundary_review.md").write_text(_render_markdown(result), encoding="utf-8")
    return review_dir


def _review_case(case: dict[str, object], by_id: dict[str, dict[str, object]], spans: list[dict[str, object]]) -> dict[str, object]:
    if case.get("verdict") == "clean_transition":
        probes = [_prediction(by_id[str(case[key])], spans) for key in ("before_segment_id", "after_segment_id")]
        return {
            "verdict": "clean_transition",
            "human_annotation": case,
            "segments": probes,
            "decision": "human_review_required",
        }

    segment = by_id[str(case["segment_id"])]
    prediction = _prediction(segment, spans)
    expected_index = _separator_word_index(str(segment.get("text", "")), str(case["separator_after_text"]))
    candidate_index = prediction.get("boundary_after_word_index")
    prediction["evaluation"] = {
        "expected_separator_word_index": expected_index,
        "matches_human_separator": expected_index is not None and candidate_index == expected_index,
    }
    return {
        "verdict": "mixed_cue",
        "human_annotation": case,
        "segment": prediction,
        "decision": "human_review_required",
    }


def _prediction(segment: dict[str, object], spans: list[dict[str, object]]) -> dict[str, object]:
    start, end = float(segment["start"]), float(segment["end"])
    words = _words_with_sentence_end(str(segment.get("text", "")))
    transitions = _internal_transitions(start, end, spans)
    base = {
        "segment_id": str(segment["id"]),
        "start": start,
        "end": end,
        "vtt_text": segment.get("text", ""),
        "lexical_word_count": len(words),
        "internal_pyannote_transitions": transitions,
    }
    if len(transitions) != 1:
        return base | {"status": "no_single_internal_pyannote_transition"}
    if not words:
        return base | {"status": "no_lexical_words"}
    transition = transitions[0]
    sentence_ends = [
        (index, word, start + (end - start) * (index + 1) / len(words))
        for index, (word, sentence_end) in enumerate(words)
        if sentence_end and index < len(words) - 1
    ]
    candidates = [item for item in sentence_ends if abs(item[2] - float(transition["at"])) <= _SENTENCE_WINDOW_SECONDS]
    if not candidates:
        return base | {
            "status": "no_sentence_end_within_2_seconds",
            "pyannote_transition_seconds": transition["at"],
        }
    index, word, estimated_seconds = min(candidates, key=lambda item: abs(item[2] - float(transition["at"])))
    return base | {
        "status": "candidate",
        "pyannote_transition_seconds": transition["at"],
        "boundary_after_word": word,
        "boundary_after_word_index": index,
        "estimated_boundary_seconds": round(estimated_seconds, 3),
        "estimated_distance_seconds": round(abs(estimated_seconds - float(transition["at"])), 3),
    }


def _internal_transitions(start: float, end: float, spans: list[dict[str, object]]) -> list[dict[str, object]]:
    """Return raw speaker changes strictly inside the cue's non-edge interval."""
    inner_start, inner_end = start + _EDGE_MARGIN_SECONDS, end - _EDGE_MARGIN_SECONDS
    current: str | None = None
    transitions: list[dict[str, object]] = []
    for span in spans:
        speaker = str(span.get("speaker_id") or "")
        span_start = float(span["start"])
        if not speaker:
            continue
        if span_start <= inner_start:
            current = speaker
            continue
        if span_start >= inner_end:
            break
        if current is not None and speaker != current:
            transitions.append({"at": round(span_start, 3), "from_speaker_id": current, "to_speaker_id": speaker})
        current = speaker
    return transitions


def _words_with_sentence_end(text: str) -> list[tuple[str, bool]]:
    result: list[tuple[str, bool]] = []
    for raw in re.findall(r"\S+", text):
        words = _WORD_RE.findall(raw)
        for index, word in enumerate(words):
            result.append((word, index == len(words) - 1 and bool(_SENTENCE_END_RE.search(raw))))
    return result


def _separator_word_index(text: str, separator: str) -> int | None:
    expected = [word.casefold() for word in _WORD_RE.findall(separator)]
    words = [word.casefold() for word, _ in _words_with_sentence_end(text)]
    if not expected:
        return None
    for start in range(len(words) - len(expected), -1, -1):
        if words[start:start + len(expected)] == expected:
            return start + len(expected) - 1
    return None


def _summary(items: list[dict[str, object]]) -> dict[str, object]:
    mixed = [item for item in items if item.get("verdict") == "mixed_cue"]
    controls = [item for item in items if item.get("verdict") == "clean_transition"]
    candidates = [item for item in mixed if item["segment"].get("status") == "candidate"]
    matches = [item for item in candidates if item["segment"].get("evaluation", {}).get("matches_human_separator")]
    false_positive_ids = sorted({
        str(segment["segment_id"])
        for item in controls
        for segment in _items(item.get("segments"))
        if segment.get("status") == "candidate"
    })
    return {
        "mixed_cue_count": len(mixed),
        "mixed_cue_candidate_count": len(candidates),
        "mixed_cue_matches_human_separator": len(matches),
        "mixed_cue_without_candidate": len(mixed) - len(candidates),
        "clean_transition_count": len(controls),
        "clean_transition_unique_cue_count": len({str(segment["segment_id"]) for item in controls for segment in _items(item.get("segments"))}),
        "clean_transition_false_positive_count": len(false_positive_ids),
        "clean_transition_false_positive_segment_ids": false_positive_ids,
    }


def _render_markdown(result: dict[str, object]) -> str:
    summary = result["summary"]
    lines = [
        f"# Mudelivaba lauselõpu-võrdlustest: {result.get('title') or 'ERR transkriptsioon'}",
        "",
        "> Ennustus kasutab ainult cue teksti, cue aega ja Pyannote'i toorintervalle. Audio, CTC joondus ja inimese märgendus ei sisene ennustusse.",
        "",
        f"- Segacue'sid: **{summary['mixed_cue_count']}**; kandidaate: **{summary['mixed_cue_candidate_count']}**; inimese tekstipiiriga kokkulangevaid kandidaate: **{summary['mixed_cue_matches_human_separator']}**.",
        f"- Puhtaid kontrollüleminekuid: **{summary['clean_transition_count']}**; unikaalseid kontrollcue'sid: **{summary['clean_transition_unique_cue_count']}**; valepositiivseid kandidaatcue'sid: **{summary['clean_transition_false_positive_count']}**.",
        "",
    ]
    for item in _items(result.get("cases")):
        if item.get("verdict") == "clean_transition":
            annotation = item["human_annotation"]
            statuses = ", ".join(f"{segment['segment_id']}: `{segment['status']}`" for segment in _items(item.get("segments")))
            lines.extend([f"## Puhas kontrollüleminek · {annotation['before_segment_id']} → {annotation['after_segment_id']}", "", statuses, ""])
            continue
        segment = item["segment"]
        annotation = item["human_annotation"]
        boundary = segment.get("boundary_after_word", "—")
        estimate = segment.get("estimated_boundary_seconds")
        estimate_text = format_time(float(estimate)) if estimate is not None else "—"
        lines.extend([
            f"## {format_time(float(segment['start']))}–{format_time(float(segment['end']))} · {segment['segment_id']}",
            "",
            f"VTT: {segment['vtt_text']}",
            "",
            f"Lugemiskonteksti märgendus (ainult hilisemaks mõõtmiseks): pärast „{annotation['separator_after_text']}”",
            "",
            f"Süsteemi tulemus: `{segment['status']}`; pakutud lõpp: **{boundary}**; hinnanguline aeg: {estimate_text}; inimese tekstipiiriga kokkulangevus: `{segment.get('evaluation', {}).get('matches_human_separator')}`.",
            "",
        ])
    return "\n".join(lines)


def _load_cases(path: Path) -> list[dict[str, object]]:
    data = _load_json(path)
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise PipelineError(ExitCode.INVALID_ARGUMENT, "Sentence-boundary case file must contain a non-empty cases array", {"path": str(path)})
    mixed_required = {"segment_id", "before_separator_speaker", "after_separator_speaker", "separator_after_text"}
    control_required = {"before_segment_id", "after_segment_id", "before_speaker", "after_speaker"}
    invalid = [index for index, item in enumerate(cases) if not isinstance(item, dict) or ((control_required if item.get("verdict") == "clean_transition" else mixed_required) - set(item))]
    if invalid:
        raise PipelineError(ExitCode.INVALID_ARGUMENT, "Sentence-boundary case is missing required fields", {"indexes": invalid})
    return [dict(item) for item in cases]


def _load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise PipelineError(ExitCode.ALIGNMENT_REVIEW_FAILED, "Required completed-run artifact is missing", {"path": str(path)})
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise PipelineError(ExitCode.ALIGNMENT_REVIEW_FAILED, "Could not parse JSON", {"path": str(path)}) from error
    if not isinstance(value, dict):
        raise PipelineError(ExitCode.ALIGNMENT_REVIEW_FAILED, "JSON artifact must be an object", {"path": str(path)})
    return value


def _items(value: object) -> list[dict[str, object]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _json_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
