from __future__ import annotations

import json
from pathlib import Path

from err2text.models import Segment


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, title: str, segments: list[Segment]) -> None:
    lines = [f"# {title}", "", "> Automaatne, kontrollimata kõneleja omistus.", ""]
    for segment in segments:
        speaker = segment.speaker_id if segment.speaker_name in (None, "UNKNOWN") else segment.speaker_name
        speaker = speaker or "OMISTAMATA"
        lines.extend([_markdown_line(speaker, segment.start, segment.end, segment.text), ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_markdown_records(path: Path, title: str, segments: list[dict[str, object]]) -> None:
    """Render persisted transcript data without re-running audio processing."""
    lines = [f"# {title}", "", "> Automaatne, kontrollimata kõneleja omistus.", ""]
    for segment in segments:
        speaker_name = segment.get("speaker_name")
        speaker = segment.get("speaker_id") if speaker_name in (None, "UNKNOWN") else speaker_name
        speaker = speaker or "OMISTAMATA"
        lines.extend([_markdown_line(speaker, float(segment["start"]), float(segment["end"]), str(segment.get("text", ""))), ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _markdown_line(speaker: object, start: float, end: float, text: str) -> str:
    readable_text = " ".join(text.split())
    return f"**{speaker}** (*{format_time(start)}–{format_time(end)}*): {readable_text}"


def format_time(seconds: float) -> str:
    milliseconds = round((seconds % 1) * 1000)
    whole = int(seconds)
    return f"{whole // 3600:02d}:{whole % 3600 // 60:02d}:{whole % 60:02d}.{milliseconds:03d}"
