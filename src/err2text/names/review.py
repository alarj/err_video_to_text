from __future__ import annotations

from collections import defaultdict

from err2text.models import Segment


def build_review(segments: list[Segment], source_url: str) -> dict[str, object]:
    by_speaker: dict[str, list[Segment]] = defaultdict(list)
    for segment in segments:
        if segment.speaker_id and segment.attribution_confidence in {"high", "medium"}:
            by_speaker[segment.speaker_id].append(segment)
    review = []
    for speaker_id, entries in sorted(by_speaker.items()):
        samples = sorted(entries, key=lambda item: item.end - item.start, reverse=True)[:5]
        review.append({"speaker_id": speaker_id, "total_speech_seconds": round(sum(x.end - x.start for x in entries), 3),
                       "source_url": source_url,
                       "samples": [{"start": x.start, "end": x.end, "text": x.text, "confidence": x.attribution_confidence} for x in samples]})
    return {"schema_version": "1.0", "speakers": review}
