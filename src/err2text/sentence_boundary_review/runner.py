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
MICRO_SPEAKER_SECONDS = 0.100
EDGE_ONLY_SPEAKER_SECONDS = 0.500
EDGE_TOUCH_SECONDS = 0.050
SENTENCE_BOUNDARY_WINDOW_SECONDS = 2.000
_EDGE_MARGIN_SECONDS = EDGE_ONLY_SPEAKER_SECONDS
_SENTENCE_WINDOW_SECONDS = SENTENCE_BOUNDARY_WINDOW_SECONDS


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


def find_candidates(transcript: dict[str, object], speakers: list[dict[str, object]]) -> list[dict[str, object]]:
    """Return production review candidates from baseline plus speaker evidence.

    Human case annotations are intentionally not accepted here. They are
    evaluation input, never prediction input.
    """
    result: list[dict[str, object]] = []
    spans = sorted(_items(speakers), key=lambda item: (float(item["start"]), float(item["end"])))
    for segment in _items(transcript.get("segments")):
        if _is_system_notice(str(segment.get("text") or "")):
            continue
        prediction = _prediction(segment, spans)
        segment_spans = _segment_spans(segment, spans)
        labels = sorted({str(item.get("speaker_id")) for item in segment_spans if item.get("speaker_id")})
        durations = _speaker_durations(segment_spans)
        if len(labels) < 2:
            continue
        dominant = max(durations, key=durations.get)
        secondary = {label: duration for label, duration in durations.items() if label != dominant}
        micro_labels = sorted(label for label, duration in secondary.items() if duration < MICRO_SPEAKER_SECONDS)
        substantive = {label for label, duration in durations.items() if duration >= MICRO_SPEAKER_SECONDS}
        edge_labels = {label for label in secondary if _is_edge_only(label, segment, segment_spans)}
        all_secondary_edge = bool(secondary) and set(secondary) <= edge_labels
        edge_only_short = all_secondary_edge and sum(secondary.values()) < EDGE_ONLY_SPEAKER_SECONDS
        edge_only_conflict = all_secondary_edge and not edge_only_short
        baseline_candidate = prediction.get("status") == "candidate"
        # Micro-spans are diagnostic evidence, not a review obligation. A
        # short edge leak is only promoted when the text baseline supports it.
        if len(substantive) < 2 and not baseline_candidate:
            continue
        overlapping = _has_cross_speaker_overlap(segment_spans)
        if overlapping:
            candidate_type = "OVERLAPPING_SPEECH"
        elif baseline_candidate:
            candidate_type = "SPEAKER_BOUNDARY"
        elif edge_only_conflict:
            candidate_type = "SPEAKER_ATTRIBUTION_CONFLICT"
        elif set(secondary) - edge_labels:
            candidate_type = "MULTI_SPEAKER_SEGMENT"
        else:
            continue
        features = [f"speaker_labels={','.join(sorted(substantive))}", f"dominant_speaker={dominant}"]
        features.append("speaker_intervals_overlapping=true" if overlapping else "speaker_intervals_sequential=true")
        if micro_labels:
            features.append("micro_labels=" + ",".join(micro_labels))
        if edge_labels:
            features.append("edge_only_labels=" + ",".join(sorted(edge_labels)))
        if edge_only_short:
            features.append("short_edge_leakage=true")
        if edge_only_conflict:
            features.append("edge_attribution_conflict=true")
        if baseline_candidate:
            features.append("sentence_boundary_baseline=true")
        result.append({
            "segment_ids": [str(segment["id"])],
            "start": float(segment["start"]),
            "end": float(segment["end"]),
            "candidate_type": candidate_type,
            "reason": "model_free_sentence_boundary_baseline; " + "; ".join(features) if features else "model_free_sentence_boundary_baseline",
            "details": prediction | {
                "speaker_labels": labels,
                "speaker_durations": {label: round(duration, 3) for label, duration in durations.items()},
                "dominant_speaker": dominant,
                "micro_labels": micro_labels,
                "edge_only_labels": sorted(edge_labels),
                "edge_only_short": edge_only_short,
                "edge_only_conflict": edge_only_conflict,
                "speaker_intervals": segment_spans,
                "cross_speaker_overlap": overlapping,
            },
        })
    return result


def suggest_sentence_split(text: str, start: float, end: float, speakers: list[dict[str, object]]) -> dict[str, object] | None:
    """Return the editable text split suggested for a stable speaker boundary."""
    prediction = _prediction({"id": "api", "start": start, "end": end, "text": text}, speakers)
    if prediction.get("status") != "candidate":
        return None
    words = list(re.finditer(r"\S+", text))
    index = prediction.get("boundary_after_word_index")
    if not isinstance(index, int) or index < 0 or index >= len(words) - 1:
        return None
    transition = prediction.get("internal_pyannote_transitions") or prediction.get("raw_pyannote_transitions") or []
    if not transition:
        return None
    split_at = words[index].end()
    return {
        "split_at": split_at,
        "boundary_second": prediction.get("pyannote_transition_seconds"),
        "from_speaker_id": transition[0].get("from_speaker_id"),
        "to_speaker_id": transition[0].get("to_speaker_id"),
    }


def _speaker_durations(spans: list[dict[str, object]]) -> dict[str, float]:
    durations: dict[str, float] = {}
    for span in spans:
        label = str(span.get("speaker_id") or "")
        duration = max(0.0, float(span["end"]) - float(span["start"]))
        if label and duration > 0:
            durations[label] = durations.get(label, 0.0) + duration
    return durations


def _is_edge_only(label: str, segment: dict[str, object], spans: list[dict[str, object]]) -> bool:
    start, end = float(segment["start"]), float(segment["end"])
    label_spans = [span for span in spans if str(span.get("speaker_id")) == label]
    if not label_spans:
        return False
    return all(
        float(span["start"]) <= start + EDGE_TOUCH_SECONDS
        or float(span["end"]) >= end - EDGE_TOUCH_SECONDS
        for span in label_spans
    )


def _segment_spans(segment: dict[str, object], spans: list[dict[str, object]]) -> list[dict[str, object]]:
    start, end = float(segment["start"]), float(segment["end"])
    result = []
    for span in spans:
        overlap_start = max(start, float(span["start"]))
        overlap_end = min(end, float(span["end"]))
        if overlap_end <= overlap_start or not span.get("speaker_id"):
            continue
        result.append({
            **span,
            "start": round(overlap_start, 3),
            "end": round(overlap_end, 3),
        })
    return result


def _has_cross_speaker_overlap(spans: list[dict[str, object]]) -> bool:
    ordered = sorted(spans, key=lambda item: (float(item["start"]), float(item["end"])))
    for index, left in enumerate(ordered):
        for right in ordered[index + 1:]:
            if float(right["start"]) >= float(left["end"]):
                break
            if str(left.get("speaker_id")) != str(right.get("speaker_id")):
                return True
    return False


def _is_system_notice(text: str) -> bool:
    return " ".join(text.split()) in {
        "Järgnevale saatele kuvatakse automaatsubtiitrid.",
        "Teksti automaatsel tuvastamisel võib esineda ebatäpsusi.",
    }


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
    raw_transitions = _speaker_transitions(start, end, spans)
    base = {
        "segment_id": str(segment["id"]),
        "start": start,
        "end": end,
        "vtt_text": segment.get("text", ""),
        "lexical_word_count": len(words),
        "internal_pyannote_transitions": transitions,
        "raw_pyannote_transitions": raw_transitions,
    }
    transition_set = transitions
    edge_transition = False
    if len(transition_set) != 1:
        if len(raw_transitions) == 1:
            transition_set = raw_transitions
            edge_transition = True
        else:
            return base | {"status": "no_single_internal_pyannote_transition"}
    if not words:
        return base | {"status": "no_lexical_words"}
    transition = transition_set[0]
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
        "edge_transition": edge_transition,
        "pyannote_transition_seconds": transition["at"],
        "boundary_after_word": word,
        "boundary_after_word_index": index,
        "estimated_boundary_seconds": round(estimated_seconds, 3),
        "estimated_distance_seconds": round(abs(estimated_seconds - float(transition["at"])), 3),
    }


def _internal_transitions(start: float, end: float, spans: list[dict[str, object]]) -> list[dict[str, object]]:
    """Return raw speaker changes strictly inside the cue's non-edge interval."""
    inner_start, inner_end = start + _EDGE_MARGIN_SECONDS, end - _EDGE_MARGIN_SECONDS
    return _speaker_transitions(inner_start, inner_end, spans, strict=True)


def _speaker_transitions(start: float, end: float, spans: list[dict[str, object]], strict: bool = False) -> list[dict[str, object]]:
    current: str | None = None
    transitions: list[dict[str, object]] = []
    for span in spans:
        speaker = str(span.get("speaker_id") or "")
        span_start = float(span["start"])
        if not speaker:
            continue
        if span_start <= start:
            current = speaker
            continue
        if span_start >= end:
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
