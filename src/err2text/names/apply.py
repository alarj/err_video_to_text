from __future__ import annotations

import hashlib
import json
from pathlib import Path

from err2text.errors import ExitCode, PipelineError


def json_sha256(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def apply_names(transcript: dict[str, object], speakers: dict[str, object], speaker_map: dict[str, object]) -> dict[str, object]:
    expected = speaker_map.get("speakers_sha256") or speaker_map.get("diarization_run_id")
    actual = speakers.get("sha256") or speakers.get("run_id") or json_sha256(speakers.get("segments", []))
    if expected != actual:
        raise PipelineError(ExitCode.INVALID_SPEAKERS_MAP, "Speaker map does not match this diarization run")
    entries = speaker_map.get("speakers", speaker_map)
    for collection in ("segments", "turns"):
        for record in transcript.get(collection, []):
            if not (speaker_id := record.get("speaker_id")) or speaker_id not in entries:
                continue
            name_info = entries[speaker_id]
            if not isinstance(name_info, dict) or not name_info.get("name"):
                continue
            record["speaker_name"] = name_info["name"]
            record["speaker_name_source"] = name_info.get("source", "manual")
    return transcript


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))
