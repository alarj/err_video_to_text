from __future__ import annotations

from collections import defaultdict
from typing import Any


def select_speaker_samples(rows: list[dict[str, Any]], limit: int = 3) -> dict[str, list[dict[str, Any]]]:
    """Choose deterministic, time-distributed speech samples per speaker label.

    Rows must contain ``speaker_label``, ``start_second``, ``end_second``,
    ``confidence`` and the segment payload.  The caller is responsible for
    filtering out system notices and segments with more than one active
    speaker.  No absolute duration or confidence threshold is assumed because
    the pipeline's values depend on the recording.
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["speaker_label"])].append(row)

    selected: dict[str, list[dict[str, Any]]] = {}
    for label, candidates in grouped.items():
        if not candidates:
            selected[label] = []
            continue
        min_start = min(float(row["start_second"]) for row in candidates)
        max_end = max(float(row["end_second"]) for row in candidates)
        span = max(max_end - min_start, 1.0)

        def rank(row: dict[str, Any]) -> tuple[float, float, float, int]:
            confidence = float(row.get("confidence") or 0)
            duration = float(row["end_second"]) - float(row["start_second"])
            return (-confidence, -duration, float(row["start_second"]), int(row["segment_id"]))

        bins: dict[int, list[dict[str, Any]]] = {0: [], 1: [], 2: []}
        for row in candidates:
            midpoint = (float(row["start_second"]) + float(row["end_second"])) / 2
            bucket = min(2, int(((midpoint - min_start) / span) * 3))
            bins[bucket].append(row)

        chosen: list[dict[str, Any]] = []
        for bucket in (0, 1, 2):
            if bins[bucket]:
                chosen.append(sorted(bins[bucket], key=rank)[0])
        if len(chosen) < limit:
            for row in sorted(candidates, key=rank):
                if row not in chosen:
                    chosen.append(row)
                if len(chosen) >= limit:
                    break
        selected[label] = sorted(chosen[:limit], key=lambda row: float(row["start_second"]))
    return selected
