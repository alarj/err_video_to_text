from __future__ import annotations

from collections.abc import Iterable


def select_candidates(
    transcript: dict[str, object],
    speaker_segments: Iterable[dict[str, object]],
    short_segment_seconds: float,
    max_candidates: int,
    manual_candidates: Iterable[dict[str, object]] = (),
) -> list[dict[str, object]]:
    """Return reviewable VTT segments with concrete reasons for selection.

    This function intentionally proposes candidates only.  It never changes a
    speaker label or a transcript.  A raw diarization boundary within one VTT
    cue is useful evidence for review, not proof that the cue must be split.
    """
    segments = [item for item in transcript.get("segments", []) if isinstance(item, dict)]
    raw_spans = [item for item in speaker_segments if isinstance(item, dict)]
    candidates: list[dict[str, object]] = []
    for index, segment in enumerate(segments):
        start, end = float(segment["start"]), float(segment["end"])
        duration = end - start
        reasons: list[str] = []
        confidence = segment.get("attribution_confidence")
        if confidence in {"medium", "low", "unknown"} or segment.get("attribution_status") == "unassigned":
            reasons.append("medium_low_or_unassigned_attribution")
        if _has_internal_speaker_boundary(start, end, raw_spans):
            reasons.append("diarization_boundary_inside_vtt_cue")
        if duration <= short_segment_seconds and _is_short_speaker_flip(segments, index):
            reasons.append("short_speaker_flip")
        if reasons:
            candidates.append(_from_segment(segment, reasons))

    for manual in manual_candidates:
        if not isinstance(manual, dict):
            continue
        reason = str(manual.get("reason") or "manual_candidate")
        segment_id = manual.get("segment_id")
        if segment_id is not None:
            matched = next((segment for segment in segments if segment.get("id") == segment_id), None)
            if matched is None:
                raise ValueError(f"manual candidate refers to an unknown segment_id: {segment_id}")
            candidate = _from_segment(matched, [reason])
            candidate["selection_source"] = "manual"
            candidates.append(candidate)
            continue
        start, end = float(manual["start"]), float(manual["end"])
        if end <= start:
            raise ValueError("manual candidate end must be after its start")
        related = [segment for segment in segments if _overlap(start, end, float(segment["start"]), float(segment["end"])) > 0]
        candidates.append({
            "start": start,
            "end": end,
            "segment_ids": [str(segment["id"]) for segment in related],
            "current_speakers": sorted({str(segment["speaker_id"]) for segment in related if segment.get("speaker_id")}),
            "current_text": " ".join(str(segment.get("text", "")).strip() for segment in related).strip(),
            "reasons": [reason],
            "selection_source": "manual",
        })

    # A Claude/manual candidate can refer to the same VTT cue as an automatic
    # rule. Keep one review clip, preserve every reason, and prioritize the
    # human-selected source when the maximum applies.
    unique: dict[tuple[float, float], dict[str, object]] = {}
    for candidate in candidates:
        key = (float(candidate["start"]), float(candidate["end"]))
        previous = unique.get(key)
        if previous is None:
            unique[key] = candidate
            continue
        previous["reasons"] = list(dict.fromkeys([*previous["reasons"], *candidate["reasons"]]))
        if candidate["selection_source"] == "manual":
            previous["selection_source"] = "manual"
    # Manual candidates have priority. Then preserve timeline order for a
    # repeatable and human-readable review package.
    selected = sorted(unique.values(), key=lambda item: (item["selection_source"] != "manual", float(item["start"]), float(item["end"])))[:max_candidates]
    for index, candidate in enumerate(selected, start=1):
        candidate["id"] = f"candidate_{index:04d}"
    return selected


def _from_segment(segment: dict[str, object], reasons: list[str]) -> dict[str, object]:
    return {
        "start": float(segment["start"]),
        "end": float(segment["end"]),
        "segment_ids": [str(segment["id"])],
        "current_speakers": [str(segment["speaker_id"])] if segment.get("speaker_id") else [],
        "current_text": str(segment.get("text", "")),
        "reasons": reasons,
        "selection_source": "automatic",
    }


def _is_short_speaker_flip(segments: list[dict[str, object]], index: int) -> bool:
    if index == 0 or index == len(segments) - 1:
        return False
    previous, current, following = segments[index - 1], segments[index], segments[index + 1]
    current_speaker = current.get("speaker_id")
    return bool(
        current_speaker
        and previous.get("speaker_id")
        and following.get("speaker_id")
        and current_speaker != previous.get("speaker_id")
        and current_speaker != following.get("speaker_id")
    )


def _has_internal_speaker_boundary(start: float, end: float, spans: list[dict[str, object]]) -> bool:
    overlapping = []
    for span in spans:
        span_start, span_end = float(span["start"]), float(span["end"])
        if _overlap(start, end, span_start, span_end) > 0:
            overlapping.append(span)
    speaker_ids = {str(span["speaker_id"]) for span in overlapping if span.get("speaker_id")}
    if len(speaker_ids) < 2:
        return False
    return any(start < float(span["start"]) < end or start < float(span["end"]) < end for span in overlapping)


def _overlap(left_start: float, left_end: float, right_start: float, right_end: float) -> float:
    return max(0.0, min(left_end, right_end) - max(left_start, right_start))
