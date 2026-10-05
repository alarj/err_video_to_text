from __future__ import annotations

from err2text.models import Cue, Segment, SpeakerSpan

_HIGH = 0.80
_MEDIUM = 0.50
_LOW = 0.20


def merge_cues(cues: list[Cue], spans: list[SpeakerSpan], time_offset_seconds: float = 0.0) -> list[Segment]:
    """Attribute each complete VTT cue to its dominant overlapping speaker.

    A VTT cue is the smallest readable transcription unit.  Diarization
    boundaries within it must not create multiple copies of its text.
    """
    result: list[Segment] = []
    shifted = [SpeakerSpan(s.speaker_id, s.start + time_offset_seconds, s.end + time_offset_seconds) for s in spans]
    for cue in cues:
        overlaps: dict[str, float] = {}
        for span in shifted:
            overlap = max(0.0, min(cue.end, span.end) - max(cue.start, span.start))
            if overlap:
                overlaps[span.speaker_id] = overlaps.get(span.speaker_id, 0.0) + overlap
        duration = cue.end - cue.start
        speaker_id, amount = max(overlaps.items(), key=lambda item: item[1]) if overlaps else (None, 0.0)
        ratio = amount / duration if duration else 0.0
        if speaker_id is None or ratio < _LOW:
            status, confidence, speaker_id = "unassigned", "unknown", None
        elif ratio >= _HIGH:
            status, confidence = "assigned", "high"
        elif ratio >= _MEDIUM:
            status, confidence = "assigned", "medium"
        else:
            status, confidence = "assigned", "low"
        result.append(Segment(
            id=f"seg_{len(result) + 1:04d}", start=cue.start, end=cue.end,
            speaker_id=speaker_id, speaker_name="UNKNOWN" if speaker_id else None,
            speaker_name_source="unknown" if speaker_id else None,
            attribution_status=status, vtt_cue_ids=[cue.id], overlap_ratio=round(ratio, 4),
            attribution_confidence=confidence, split_estimated=False, text=cue.text,
        ))
    return result


def build_turns(segments: list[Segment]) -> list[dict[str, object]]:
    turns: list[dict[str, object]] = []
    for segment in segments:
        if turns and segment.speaker_id and turns[-1]["speaker_id"] == segment.speaker_id and turns[-1]["end"] == segment.start:
            turns[-1]["end"] = segment.end
            turns[-1]["text"] = f"{turns[-1]['text']} {segment.text}".strip()
            turns[-1]["segment_ids"].append(segment.id)
            continue
        turns.append({"id": f"turn_{len(turns) + 1:04d}", "start": segment.start, "end": segment.end,
                      "speaker_id": segment.speaker_id, "speaker_name": segment.speaker_name,
                      "attribution_status": segment.attribution_status, "segment_ids": [segment.id], "text": segment.text})
    return turns
