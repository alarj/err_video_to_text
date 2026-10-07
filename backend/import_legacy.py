"""Import the preserved Reinsalu MVP2.2 control output into Oracle.

The importer is deliberately an explicit administrative command.  It never
changes the files under the input directory and is idempotent by the source
URL, selected media URL and transcript artifact path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from app.services.materializer import artifact_metadata, materialize, prepare


OUTPUT_FILES = (
    "resolver.json",
    "original.vtt",
    "normalized.vtt",
    "speakers.json",
    "transcript.json",
    "run_metadata.json",
    "speaker_review.json",
)
OPTIONAL_OUTPUT_SUFFIXES = ("-transcript.md",)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a preserved ERR2TEXT legacy output")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", help="write the import to Oracle")
    args = parser.parse_args()

    from dotenv import load_dotenv
    from app.database.oracle import connection

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    payload = load_payload(args.source_dir.resolve())
    report = inventory(payload)
    if not args.apply:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    _prepare_legacy_artifacts(payload)
    with connection() as conn:
        try:
            process_id, reused = import_payload(conn, payload)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    report.update({"process_id": process_id, "reused": reused, "applied": True})
    print(json.dumps(report, ensure_ascii=False, indent=2))


def load_payload(source_dir: Path) -> dict[str, Any]:
    resolver = _read_json(source_dir / "resolver.json")
    selected = resolver.get("selected_media")
    if not isinstance(selected, dict) or not selected.get("canonical_url"):
        raise ValueError("resolver.json must contain selected_media.canonical_url")
    control_path = source_dir.parent.parent / "review-inputs" / "reinsalu-isamaa-candidates.json"
    alignment_path = source_dir.parent.parent / "review-inputs" / "reinsalu-isamaa-alignment-evaluation-1.json"
    missing_control = [str(path) for path in (control_path, alignment_path) if not path.is_file()]
    if missing_control:
        raise FileNotFoundError("Missing mandatory legacy control files: " + ", ".join(missing_control))
    transcript = _read_json(source_dir / "transcript.json")
    speakers = _read_json(source_dir / "speakers.json")
    prepared = prepare(source_dir)
    candidates = _read_json(control_path)
    alignment = _read_json(alignment_path)
    files = [source_dir / name for name in OUTPUT_FILES if (source_dir / name).is_file()]
    files.extend(sorted(source_dir.glob("*-transcript.md")))
    missing = [name for name in OUTPUT_FILES if not (source_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing required legacy files: {', '.join(missing)}")
    return {
        "source_dir": source_dir,
        "resolver": resolver,
        "selected_media": selected,
        "transcript": transcript,
        "speakers": speakers,
        "candidates": candidates,
        "alignment": alignment,
        "files": files,
        "prepared": prepared,
        "control_path": control_path,
        "alignment_path": alignment_path,
        "evaluation_path": source_dir / "review" / "legacy_control_evaluation.json",
    }


def inventory(payload: dict[str, Any]) -> dict[str, Any]:
    resolver = payload["resolver"]
    selected = payload["selected_media"]
    control_ids = {
        str(item.get("segment_id"))
        for item in payload["candidates"].get("candidates", [])
        if item.get("segment_id")
    }
    baseline_ids = {
        str(segment_id)
        for candidate in payload["prepared"].candidates
        for segment_id in candidate.get("segment_ids", [])
    }
    clean_ids = {
        str(case.get(key))
        for case in payload["alignment"].get("cases", [])
        if case.get("verdict") == "clean_transition"
        for key in ("before_segment_id", "after_segment_id")
        if case.get(key)
    }
    evaluation = {
        "baseline_candidate_count": len(baseline_ids),
        "control_overlap_count": len(control_ids & baseline_ids),
        "control_only_count": len(control_ids - baseline_ids),
        "clean_control_count": len(clean_ids),
        "clean_control_case_count": sum(1 for case in payload["alignment"].get("cases", []) if case.get("verdict") == "clean_transition"),
        "baseline_candidates_in_clean_controls": len(baseline_ids & clean_ids),
        "note": "Puhas kontrollkoht on alignment-evaluation faili clean_transition juhtumi kummagi segmendi ID; kattuvus näitab baseline'i võimalikku valepositiivset kandidaati.",
    }
    return {
        "source_url": resolver["source_url"],
        "media_url": selected["canonical_url"],
        "title": resolver.get("title") or selected.get("title"),
        "control_file": str(payload["control_path"]),
        "control_file_sha256": sha256(payload["control_path"]) if payload["control_path"].is_file() else None,
        "alignment_file": str(payload["alignment_path"]),
        "alignment_file_sha256": sha256(payload["alignment_path"]) if payload["alignment_path"].is_file() else None,
        "files": [
            {"path": str(path), "size_byte": path.stat().st_size, "sha256": sha256(path)}
            for path in payload["files"]
        ],
        "transcript_segments": len(payload["transcript"].get("segments", [])),
        "speaker_labels": sorted({str(item.get("speaker_id")) for item in payload["speakers"].get("segments", []) if item.get("speaker_id")}),
        "candidate_control_count": len(payload["candidates"].get("candidates", [])),
        "candidate_control_evaluation": evaluation,
    }


def _prepare_legacy_artifacts(payload: dict[str, Any]) -> None:
    """Persist legacy provenance and attach it to the imported activity.

    The generated report is deterministic and is never used as prediction input.
    All file metadata and checksums are prepared before the Oracle transaction.
    """
    evaluation_path = payload["evaluation_path"]
    evaluation_path.parent.mkdir(parents=True, exist_ok=True)
    report = inventory(payload)
    evaluation_path.write_text(json.dumps({
        "schema_version": "1.0",
        "control_file": str(payload["control_path"]),
        "control_file_sha256": sha256(payload["control_path"]) if payload["control_path"].is_file() else None,
        "alignment_file": str(payload["alignment_path"]),
        "alignment_file_sha256": sha256(payload["alignment_path"]) if payload["alignment_path"].is_file() else None,
        "evaluation": report["candidate_control_evaluation"],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    overrides: dict[str, dict[str, Any]] = {}
    for path in payload["files"]:
        if path.name.endswith("-transcript.md"):
            overrides[path.name] = {
                "artifact_type": "LEGACY_MANUAL_TRANSCRIPT_MARKDOWN",
                "transcript_artifact": False,
            }
        elif path.name == "speaker_review.json":
            overrides[path.name] = {
                "artifact_type": "LEGACY_MANUAL_SPEAKER_REVIEW_JSON",
                "transcript_artifact": False,
            }
    prepared = prepare(payload["source_dir"], overrides)
    extra = []
    if payload["control_path"].is_file():
        extra.append(artifact_metadata(payload["control_path"], artifact_type="LEGACY_CONTROL_CANDIDATES_JSON", transcript_artifact=False))
    if payload["alignment_path"].is_file():
        extra.append(artifact_metadata(payload["alignment_path"], artifact_type="LEGACY_CONTROL_ALIGNMENT_JSON", transcript_artifact=False))
    extra.append(artifact_metadata(evaluation_path, artifact_type="LEGACY_CONTROL_EVALUATION_JSON", transcript_artifact=False))
    payload["prepared"] = replace(prepared, artifacts=prepared.artifacts + extra)


def import_payload(conn, payload: dict[str, Any]) -> tuple[int, bool]:
    cursor = conn.cursor()
    resolver = payload["resolver"]
    selected = payload["selected_media"]
    source_url = str(resolver["source_url"])
    media_url = str(selected["canonical_url"])
    transcript_path = str(payload["source_dir"] / "transcript.json")
    cursor.execute(
        """SELECT p.id
             FROM processes p
             JOIN sources s ON s.id = p.source_id
             JOIN media_items m ON m.id = p.media_item_id
            WHERE s.url = :source_url
              AND m.canonical_url = :media_url
              AND EXISTS (
                    SELECT 1 FROM transcript_versions tv
                    JOIN transcript_artifacts ta ON ta.transcript_version_id = tv.id
                    JOIN artifacts a ON a.id = ta.artifact_id
                    WHERE tv.process_id = p.id AND a.path = :transcript_path
              )
            FETCH FIRST 1 ROW ONLY""",
        {"source_url": source_url, "media_url": media_url, "transcript_path": transcript_path},
    )
    existing = cursor.fetchone()
    if existing:
        return int(existing[0]), True

    source_id = _insert_source(cursor, resolver, source_url)
    media_id = _get_or_insert_media(cursor, selected)
    _insert_asset(cursor, media_id, "MANIFEST", media_url)
    vtt_url = resolver.get("vtt_url")
    if vtt_url:
        _insert_asset(cursor, media_id, "VTT", str(vtt_url))

    process_id = _insert_process(cursor, source_id, media_id)
    diarizing_id = _insert_activity(cursor, process_id, "DIARIZING", None, "OK")
    materializing_id = _insert_activity(cursor, process_id, "MATERIALIZING_AUTOMATIC_DRAFT", diarizing_id, "OK")
    materialize(cursor, process_id, materializing_id, payload["prepared"])
    waiting_id = _insert_activity(cursor, process_id, "WAITING_FOR_PARTICIPANTS", materializing_id, None)
    cursor.execute(
        "UPDATE processes SET status = 'WAITING_FOR_PARTICIPANTS', last_updated = SYSTIMESTAMP WHERE id = :id",
        {"id": process_id},
    )
    return process_id, False


def _insert_source(cursor, resolver: dict[str, Any], source_url: str) -> int:
    var = cursor.var(int)
    cursor.execute(
        """INSERT INTO sources (url, source_type, title, description, published_date)
           VALUES (:url, :source_type, :title, :description, :published_date)
           RETURNING id INTO :id""",
        {"url": source_url, "source_type": resolver.get("url_type", "ERR_URL"),
         "title": resolver.get("title") or source_url, "description": resolver.get("description"),
         "published_date": None, "id": var},
    )
    return int(var.getvalue()[0])


def _get_or_insert_media(cursor, media: dict[str, Any]) -> int:
    cursor.execute("SELECT id FROM media_items WHERE canonical_url = :url AND end_date IS NULL", {"url": media["canonical_url"]})
    row = cursor.fetchone()
    if row:
        return int(row[0])
    var = cursor.var(int)
    cursor.execute(
        """INSERT INTO media_items (provider, external_id, canonical_url, media_type, title, duration_second)
           VALUES ('ERR', :external_id, :url, :media_type, :title, :duration)
           RETURNING id INTO :id""",
        {"external_id": media.get("vod_id") or media["canonical_url"], "url": media["canonical_url"],
         "media_type": str(media.get("media_type") or "OTHER").upper(), "title": media.get("title") or "ERR media",
         "duration": media.get("duration_seconds"), "id": var},
    )
    return int(var.getvalue()[0])


def _insert_asset(cursor, media_id: int, asset_type: str, url: str) -> None:
    cursor.execute("SELECT 1 FROM media_assets WHERE media_item_id = :id AND url = :url AND end_date IS NULL", {"id": media_id, "url": url})
    if cursor.fetchone():
        return
    cursor.execute("INSERT INTO media_assets (media_item_id, asset_type, url) VALUES (:id, :type, :url)", {"id": media_id, "type": asset_type, "url": url})


def _insert_process(cursor, source_id: int, media_id: int) -> int:
    var = cursor.var(int)
    cursor.execute(
        """INSERT INTO processes (source_id, media_item_id, status, started_at)
           VALUES (:source_id, :media_id, 'DIARIZING', SYSTIMESTAMP)
           RETURNING id INTO :id""",
        {"source_id": source_id, "media_id": media_id, "id": var},
    )
    return int(var.getvalue()[0])


def _insert_activity(cursor, process_id: int, activity_type: str, previous_id: int | None, result: str | None) -> int:
    var = cursor.var(int)
    cursor.execute(
        """INSERT INTO activities
               (process_id, previous_activity_id, activity_type, started_at, finished_at, result, execution_started_at)
           VALUES (:process_id, :previous_id, :activity_type, SYSTIMESTAMP,
                   CASE WHEN :result IS NULL THEN NULL ELSE SYSTIMESTAMP END,
                   :result, CASE WHEN :result IS NULL THEN NULL ELSE SYSTIMESTAMP END)
           RETURNING id INTO :id""",
        {"process_id": process_id, "previous_id": previous_id, "activity_type": activity_type, "result": result, "id": var},
    )
    return int(var.getvalue()[0])


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    main()
