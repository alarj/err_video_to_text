from __future__ import annotations

import re

from err2text.models import Cue

_TIMING = re.compile(
    r"^(?P<start>\d{2}:\d{2}:\d{2}\.\d{3}|\d{2}:\d{2}\.\d{3})\s+-->\s+"
    r"(?P<end>\d{2}:\d{2}:\d{2}\.\d{3}|\d{2}:\d{2}\.\d{3})(?:\s+.*)?$"
)
_TAG = re.compile(r"<[^>]+>")


def parse_timestamp(value: str) -> float:
    parts = value.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    hours, minutes, seconds = parts
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def parse_vtt(text: str) -> list[Cue]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cues: list[Cue] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip("\ufeff")
        if not line or line == "WEBVTT":
            index += 1
            continue
        if line.startswith("NOTE"):
            index += 1
            while index < len(lines) and lines[index].strip():
                index += 1
            continue
        cue_id: str | None = None
        timing = _TIMING.match(line)
        if not timing:
            cue_id = line.strip()
            index += 1
            if index >= len(lines):
                break
            timing = _TIMING.match(lines[index].strip())
        if not timing:
            index += 1
            continue
        index += 1
        text_lines: list[str] = []
        while index < len(lines) and lines[index].strip():
            text_lines.append(lines[index].strip())
            index += 1
        cue_number = len(cues) + 1
        cue_text = _TAG.sub("", "\n".join(text_lines)).strip()
        cues.append(Cue(
            id=cue_id or f"cue_{cue_number:04d}",
            start=parse_timestamp(timing.group("start")),
            end=parse_timestamp(timing.group("end")),
            text=cue_text,
        ))
    return cues
