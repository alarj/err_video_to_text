from __future__ import annotations

import hashlib
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from err2text.sentence_boundary_review.runner import find_candidates


SYSTEM_NOTICES = {
    "Järgnevale saatele kuvatakse automaatsubtiitrid.",
    "Teksti automaatsel tuvastamisel võib esineda ebatäpsusi.",
}


@dataclass(frozen=True)
class PreparedMaterialization:
    transcript: dict[str, Any]
    speakers: dict[str, Any]
    candidates: list[dict[str, Any]]
    artifacts: list[dict[str, Any]]


def prepare(result_dir: Path, artifact_overrides: dict[str, dict[str, Any]] | None = None) -> PreparedMaterialization:
    transcript = _read_json(result_dir / "transcript.json")
    speakers = _read_json(result_dir / "speakers.json")
    for segment in transcript.get("segments", []):
        text = str(segment.get("text") or "")
        if len(text.encode("utf-8")) > 4000:
            raise ValueError(f"Transcript segment {segment.get('id')} exceeds Oracle VARCHAR2(4000)")
    candidates = find_candidates(transcript, [item for item in speakers.get("segments", []) if isinstance(item, dict)])
    artifacts = []
    for path in sorted(result_dir.iterdir()):
        if not path.is_file():
            continue
        override = (artifact_overrides or {}).get(path.name, {})
        artifacts.append(artifact_metadata(
            path,
            artifact_type=override.get("artifact_type"),
            transcript_artifact=override.get("transcript_artifact"),
        ))
    return PreparedMaterialization(transcript, speakers, candidates, artifacts)


def materialize(cursor: Any, process_id: int, activity_id: int, prepared: PreparedMaterialization) -> None:
    transcript = prepared.transcript
    speakers = prepared.speakers
    version_id = _insert_version(cursor, process_id, activity_id)
    participant_ids = _insert_transcript_participants(cursor, version_id, speakers)
    segment_ids = _insert_segments(cursor, version_id, transcript, participant_ids, speakers)
    _insert_candidates(cursor, segment_ids, prepared.candidates)
    _insert_artifacts(cursor, activity_id, version_id, prepared.artifacts)


def _insert_version(cursor: Any, process_id: int, activity_id: int) -> int:
    value = cursor.var(int)
    cursor.execute(
        """INSERT INTO transcript_versions
               (process_id, activity_id, version_number, version_type, status)
           VALUES (:process_id, :activity_id, 1, 'AUTOMATIC_DRAFT', 'DRAFT')
           RETURNING id INTO :version_id""",
        {"process_id": process_id, "activity_id": activity_id, "version_id": value},
    )
    return int(value.getvalue()[0])


def _insert_transcript_participants(cursor: Any, version_id: int, speakers: dict[str, Any]) -> dict[str, int]:
    result: dict[str, int] = {}
    labels = sorted({str(item["speaker_id"]) for item in speakers.get("segments", []) if item.get("speaker_id")})
    for label in labels:
        value = cursor.var(int)
        cursor.execute(
            """INSERT INTO transcript_participants
                   (transcript_version_id, speaker_label, participant_id, role, mapping_status)
               VALUES (:version_id, :speaker_label, NULL, NULL, 'UNCONFIRMED')
               RETURNING id INTO :participant_id""",
            {"version_id": version_id, "speaker_label": label, "participant_id": value},
        )
        result[label] = int(value.getvalue()[0])
    return result


def _insert_segments(
    cursor: Any,
    version_id: int,
    transcript: dict[str, Any],
    participant_ids: dict[str, int],
    speakers: dict[str, Any],
) -> dict[str, int]:
    spans = [item for item in speakers.get("segments", []) if item.get("speaker_id")]
    result: dict[str, int] = {}
    for number, segment in enumerate(transcript.get("segments", []), start=1):
        text = str(segment.get("text") or "")
        segment_type = "SYSTEM_NOTICE" if _is_system_notice(text) else "SPEECH"
        value = cursor.var(int)
        cursor.execute(
            """INSERT INTO transcript_segments
                   (transcript_version_id, segment_number, start_second, end_second, text, segment_type)
               VALUES (:version_id, :segment_number, :start_second, :end_second, :segment_text, :segment_type)
               RETURNING id INTO :segment_id""",
            {
                "version_id": version_id,
                "segment_number": number,
                "start_second": float(segment["start"]),
                "end_second": float(segment["end"]),
                "segment_text": text,
                "segment_type": segment_type,
                "segment_id": value,
            },
        )
        db_id = int(value.getvalue()[0])
        result[str(segment["id"])] = db_id
        if segment_type == "SYSTEM_NOTICE":
            continue
        start, end = float(segment["start"]), float(segment["end"])
        duration = max(0.0, end - start)
        for span in spans:
            overlap_start = max(start, float(span["start"]))
            overlap_end = min(end, float(span["end"]))
            if overlap_end <= overlap_start:
                continue
            label = str(span["speaker_id"])
            cursor.execute(
                """INSERT INTO transcript_segment_speakers
                       (transcript_segment_id, transcript_participant_id, start_second, end_second, confidence)
                   VALUES (:segment_id, :participant_id, :start_second, :end_second, :confidence)""",
                {
                    "segment_id": db_id,
                    "participant_id": participant_ids[label],
                    "start_second": overlap_start,
                    "end_second": overlap_end,
                    "confidence": round((overlap_end - overlap_start) / duration, 5) if duration else 0,
                },
            )
    return result


def _insert_candidates(cursor: Any, segment_ids: dict[str, int], candidates: list[dict[str, Any]]) -> None:
    for candidate in candidates:
        reason = str(candidate["reason"])
        if len(reason.encode("utf-8")) > 1000:
            raise ValueError("Review candidate reason exceeds Oracle VARCHAR2(1000)")
        for source_id in candidate.get("segment_ids", []):
            segment_id = segment_ids.get(str(source_id))
            if segment_id is None:
                continue
            cursor.execute(
                """INSERT INTO review_candidates
                       (transcript_segment_id, candidate_type, reason, status)
                   VALUES (:segment_id, :candidate_type, :reason, 'PENDING')""",
                {
                    "segment_id": segment_id,
                    "candidate_type": str(candidate["candidate_type"]),
                    "reason": reason,
                },
            )


def _insert_artifacts(cursor: Any, activity_id: int, version_id: int, artifacts: list[dict[str, Any]]) -> None:
    for artifact in artifacts:
        value = cursor.var(int)
        cursor.execute(
            """INSERT INTO artifacts (artifact_type, path, content_type, size_byte, sha256)
               VALUES (:artifact_type, :path, :content_type, :size_byte, :sha256)
               RETURNING id INTO :artifact_id""",
            {
                "artifact_type": artifact["artifact_type"],
                "path": artifact["path"],
                "content_type": artifact["content_type"],
                "size_byte": artifact["size_byte"],
                "sha256": artifact["sha256"],
                "artifact_id": value,
            },
        )
        artifact_id = int(value.getvalue()[0])
        cursor.execute(
            "INSERT INTO activity_artifacts (activity_id, artifact_id) VALUES (:activity_id, :artifact_id)",
            {"activity_id": activity_id, "artifact_id": artifact_id},
        )
        if artifact.get("transcript_artifact", False):
            cursor.execute(
                "INSERT INTO transcript_artifacts (transcript_version_id, artifact_id) VALUES (:version_id, :artifact_id)",
                {"version_id": version_id, "artifact_id": artifact_id},
            )


def _is_system_notice(text: str) -> bool:
    return " ".join(text.split()) in SYSTEM_NOTICES


def _read_json(path: Path) -> dict[str, Any]:
    import json

    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_metadata(
    path: Path,
    *,
    artifact_type: str | None = None,
    transcript_artifact: bool | None = None,
) -> dict[str, Any]:
    """Prepare immutable file metadata before opening a database transaction."""
    if not path.is_file():
        raise FileNotFoundError(path)
    if transcript_artifact is None:
        transcript_artifact = path.name in {
            "original.vtt", "normalized.vtt", "speakers.json", "transcript.json", "speaker_review.json",
        } or path.name.endswith("-transcript.md")
    return {
        "path": str(path),
        "name": path.name,
        "artifact_type": artifact_type or _artifact_type(path),
        "transcript_artifact": transcript_artifact,
        "content_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        "size_byte": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _artifact_type(path: Path) -> str:
    names = {
        "original.vtt": "ORIGINAL_VTT",
        "normalized.vtt": "NORMALIZED_VTT",
        "speakers.json": "DIARIZATION_JSON",
        "transcript.json": "AUTOMATIC_TRANSCRIPT_JSON",
        "resolver.json": "RESOLVER_JSON",
        "run_metadata.json": "RUN_METADATA_JSON",
        "speaker_review.json": "AUTOMATIC_SPEAKER_REVIEW_JSON",
    }
    return names.get(path.name, "AUTOMATIC_TRANSCRIPT_MARKDOWN" if path.name.endswith("-transcript.md") else "FILE")
