from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse

from app.database.oracle import connection
from app.schemas import (
    CreateJobRequest,
    JobResponse,
    ParticipantCreateRequest,
    ReviewCandidateRequest,
    ParticipantReviewRequest,
    ResolveRequest,
)
from app.services.resolver import resolve
from app.services.participant_review import select_speaker_samples
from err2text.errors import PipelineError
from err2text.sentence_boundary_review.runner import suggest_sentence_split

router = APIRouter()


def _utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@router.post("/resolve")
def resolve_url(request: ResolveRequest) -> dict[str, object]:
    try:
        return resolve(str(request.url))
    except PipelineError as exc:
        raise HTTPException(status_code=422, detail={"error": exc.code.name, "message": exc.message}) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail={"error": type(exc).__name__, "message": str(exc)}) from exc


@router.post("/jobs", response_model=JobResponse, status_code=201)
def create_job(request: CreateJobRequest) -> JobResponse:
    if not request.confirm:
        raise HTTPException(status_code=400, detail="confirm must be true")
    source_url = str(request.source_url)
    media = request.selected_media
    if not media.canonical_url:
        raise HTTPException(status_code=400, detail="selected_media.canonical_url is required")

    with connection() as conn:
        cursor = conn.cursor()
        try:
            source_id = _insert_source(cursor, source_url, request)
            media_id = _get_or_insert_media(cursor, media)
            _insert_assets(cursor, media_id, [*media.assets, *request.assets])
            active_parent = _find_active_process(cursor, media_id)
            finished_parent = None if active_parent else _find_finished_process(cursor, media_id)
            process_var = cursor.var(int)
            if finished_parent is not None:
                cursor.execute(
                    """INSERT INTO processes
                       (parent_process_id, source_id, media_item_id, status, started_at, finished_at)
                       VALUES (:parent_id, :source_id, :media_id, 'FINISHED', SYSTIMESTAMP, SYSTIMESTAMP)
                       RETURNING id INTO :process_id""",
                    {"parent_id": finished_parent, "source_id": source_id, "media_id": media_id, "process_id": process_var},
                )
                process_id = int(process_var.getvalue()[0])
                conn.commit()
                return JobResponse(id=process_id, status="FINISHED", reused=True)

            status = "WAITING_FOR_RESULT" if active_parent is not None else "DOWNLOADING"
            cursor.execute(
                """INSERT INTO processes
                   (parent_process_id, source_id, media_item_id, status, started_at)
                   VALUES (:parent_id, :source_id, :media_id, :status, SYSTIMESTAMP)
                   RETURNING id INTO :process_id""",
                {"parent_id": active_parent, "source_id": source_id, "media_id": media_id,
                 "status": status, "process_id": process_var},
            )
            process_id = int(process_var.getvalue()[0])
            activity_type = "WAITING_FOR_RESULT" if active_parent is not None else "DOWNLOADING"
            cursor.execute(
                """INSERT INTO activities (process_id, activity_type, started_at)
                   VALUES (:process_id, :activity_type, SYSTIMESTAMP)""",
                {"process_id": process_id, "activity_type": activity_type},
            )
            conn.commit()
            return JobResponse(id=process_id, status=status)
        except Exception:
            conn.rollback()
            raise


@router.get("/jobs")
def list_jobs(limit: int = Query(default=100, ge=1, le=200)) -> list[dict[str, object]]:
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT p.id, src.url, NVL(src.title, m.title), p.status, p.created, p.finished_at,
                      (SELECT a.error_code FROM activities a
                       WHERE a.process_id = p.id AND a.result = 'ERROR' AND a.end_date IS NULL
                       ORDER BY a.id DESC FETCH FIRST 1 ROW ONLY),
                      (SELECT a.error_message FROM activities a
                       WHERE a.process_id = p.id AND a.result = 'ERROR' AND a.end_date IS NULL
                       ORDER BY a.id DESC FETCH FIRST 1 ROW ONLY)
                 FROM processes p
                 JOIN sources src ON src.id = p.source_id
                 JOIN media_items m ON m.id = p.media_item_id
                WHERE p.end_date IS NULL AND src.end_date IS NULL AND m.end_date IS NULL
                ORDER BY p.created DESC, p.id DESC
                FETCH FIRST :limit ROWS ONLY""",
            {"limit": limit},
        )
        return [_job_summary(row) for row in cursor.fetchall()]


@router.get("/queue-status")
def get_queue_status() -> dict[str, int]:
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT COUNT(*)
                 FROM activities
                WHERE activity_type = 'DIARIZING'
                  AND execution_started_at IS NOT NULL
                  AND finished_at IS NULL
                  AND end_date IS NULL"""
        )
        running = int(cursor.fetchone()[0])
    maximum = max(1, int(os.getenv("ERR2TEXT_MAX_CONCURRENT_DIARIZATIONS", "1")))
    return {"running_diarizations": running, "max_concurrent_diarizations": maximum}


@router.get("/participants")
def search_participants(query: str = Query(default="", max_length=200), limit: int = Query(default=50, ge=1, le=100)) -> list[dict[str, object]]:
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, name, description, organisation, occupation
                 FROM participants
                WHERE end_date IS NULL
                  AND (:query IS NULL OR LOWER(name) LIKE '%' || LOWER(:query) || '%')
                ORDER BY name, id
                FETCH FIRST :limit ROWS ONLY""",
            {"query": query.strip() or None, "limit": limit},
        )
        return [
            {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "organisation": row[3],
                "occupation": row[4],
            }
            for row in cursor.fetchall()
        ]


@router.post("/participants", status_code=201)
def create_participant(request: ParticipantCreateRequest) -> dict[str, object]:
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Participant name is required")
    with connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT id, name, description, organisation, occupation
                     FROM participants
                    WHERE end_date IS NULL AND LOWER(name) = LOWER(:name)
                    ORDER BY id
                    FETCH FIRST 1 ROW ONLY""",
                {"name": name},
            )
            existing = cursor.fetchone()
            if existing is not None:
                return {
                    "id": existing[0],
                    "name": existing[1],
                    "description": existing[2],
                    "organisation": existing[3],
                    "occupation": existing[4],
                }
            participant_var = cursor.var(int)
            cursor.execute(
                """INSERT INTO participants (name, description, organisation, occupation)
                   VALUES (:name, :description, :organisation, :occupation)
                   RETURNING id INTO :participant_id""",
                {
                    "name": name,
                    "description": request.description,
                    "organisation": request.organisation,
                    "occupation": request.occupation,
                    "participant_id": participant_var,
                },
            )
            participant_id = int(participant_var.getvalue()[0])
            conn.commit()
            return {
                "id": participant_id,
                "name": name,
                "description": request.description,
                "organisation": request.organisation,
                "occupation": request.occupation,
            }
        except Exception:
            conn.rollback()
            raise


@router.get("/jobs/{job_id}")
def get_job(job_id: int) -> dict[str, object]:
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT p.id, p.status, src.url, p.finished_at,
                      src.source_type, src.title, src.description, src.published_date,
                      m.title, m.description, m.media_type, m.canonical_url,
                      m.external_id, m.duration_second,
                      (SELECT a.error_code FROM activities a
                       WHERE a.process_id = p.id AND a.result = 'ERROR' AND a.end_date IS NULL
                       ORDER BY a.id DESC FETCH FIRST 1 ROW ONLY),
                      (SELECT a.error_message FROM activities a
                       WHERE a.process_id = p.id AND a.result = 'ERROR' AND a.end_date IS NULL
                       ORDER BY a.id DESC FETCH FIRST 1 ROW ONLY),
                      p.created
                 FROM processes p
                 JOIN sources src ON src.id = p.source_id
                 JOIN media_items m ON m.id = p.media_item_id
                WHERE p.id = :process_id AND p.end_date IS NULL
                  AND src.end_date IS NULL AND m.end_date IS NULL""",
            {"process_id": job_id},
        )
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Process not found")
        return {
            "id": row[0], "status": row[1], "submitted_url": row[2],
            "title": row[5] or row[8], "error_code": row[14], "error_message": row[15],
            "submitted_at": _utc_iso(row[16]), "resolved_at": _utc_iso(row[3]),
            "source_type": row[4], "source_title": row[5], "source_description": row[6],
            "source_published_date": _utc_iso(row[7]), "media_title": row[8],
            "media_description": row[9], "media_type": row[10], "media_url": row[11],
            "media_external_id": row[12], "duration_second": row[13],
        }


@router.get("/jobs/{job_id}/events")
def get_job_events(job_id: int) -> list[dict[str, object]]:
    with connection() as conn:
        cursor = conn.cursor()
        _require_process(cursor, job_id)
        cursor.execute(
            """SELECT id, activity_type, started_at, finished_at, result, error_code, error_message
                 FROM activities
                WHERE process_id = :process_id AND end_date IS NULL
                ORDER BY started_at, id""",
            {"process_id": job_id},
        )
        result = []
        for row in cursor.fetchall():
            detail = row[6] if row[6] else (f"Tulemus: {row[4]}" if row[4] else "Tegevus käib.")
            result.append({
                "id": row[0], "status": row[1], "event_type": row[1], "detail": detail,
                "event_at": _utc_iso(row[2]), "finished_at": _utc_iso(row[3]),
                "run_status": row[4], "result": row[4], "error_code": row[5],
            })
        return result


@router.get("/jobs/{job_id}/artifacts")
def get_job_artifacts(job_id: int) -> list[dict[str, object]]:
    with connection() as conn:
        cursor = conn.cursor()
        _require_process(cursor, job_id)
        cursor.execute(
            """SELECT tv.id
                 FROM transcript_versions tv
                WHERE tv.process_id = :process_id
                  AND tv.version_type = 'REVIEWED_DRAFT'
                  AND tv.end_date IS NULL
                ORDER BY tv.version_number DESC
                FETCH FIRST 1 ROW ONLY""",
            {"process_id": job_id},
        )
        reviewed = cursor.fetchone()
    if reviewed is not None:
        _regenerate_reviewed_artifacts(job_id, int(reviewed[0]))
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT DISTINCT a.id, a.artifact_type, a.path, a.content_type, a.size_byte, a.sha256
                 FROM processes p
                 JOIN transcript_versions tv ON tv.process_id = p.id OR tv.process_id = p.parent_process_id
                 JOIN transcript_artifacts ta ON ta.transcript_version_id = tv.id
                 JOIN artifacts a ON a.id = ta.artifact_id
                WHERE p.id = :process_id AND a.end_date IS NULL
                  AND tv.end_date IS NULL AND ta.end_date IS NULL
                ORDER BY a.id""",
            {"process_id": job_id},
        )
        return [_artifact(row) for row in cursor.fetchall()]


@router.get("/jobs/{job_id}/review")
def get_review(job_id: int) -> dict[str, object]:
    """Return the current reviewed transcript and its candidate context."""
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT p.id, p.status, p.media_item_id, src.url, src.title,
                      m.canonical_url, m.media_type, m.duration_second
                 FROM processes p
                 JOIN sources src ON src.id = p.source_id
                 JOIN media_items m ON m.id = p.media_item_id
                WHERE p.id = :process_id AND p.end_date IS NULL
                  AND src.end_date IS NULL AND m.end_date IS NULL""",
            {"process_id": job_id},
        )
        process = cursor.fetchone()
        if process is None:
            raise HTTPException(status_code=404, detail="Process not found")
        cursor.execute(
            """SELECT id, version_type, version_number, status
                 FROM transcript_versions
                WHERE process_id = :process_id AND end_date IS NULL
                ORDER BY CASE version_type WHEN 'REVIEWED_DRAFT' THEN 0 WHEN 'AUTOMATIC_DRAFT' THEN 1 ELSE 2 END,
                         version_number DESC""",
            {"process_id": job_id},
        )
        versions = cursor.fetchall()
        if not versions:
            raise HTTPException(status_code=409, detail="No transcript version available")
        version = versions[0]
        version_id = int(version[0])
        cursor.execute(
            """SELECT id, source_segment_id, segment_number, start_second, end_second, text, segment_type
                 FROM transcript_segments
                WHERE transcript_version_id = :version_id AND end_date IS NULL
                ORDER BY segment_number, id""",
            {"version_id": version_id},
        )
        segment_rows = cursor.fetchall()
        segments = [
            {
                "id": int(row[0]),
                "source_segment_id": int(row[1]) if row[1] is not None else None,
                "segment_number": int(row[2]),
                "start_second": float(row[3]),
                "end_second": float(row[4]),
                "text": row[5],
                "segment_type": row[6],
                "speakers": [],
            }
            for row in segment_rows
        ]
        segment_by_id = {item["id"]: item for item in segments}
        segments_by_source: dict[int, list[dict[str, object]]] = {}
        for item in segments:
            if item["source_segment_id"] is not None:
                segments_by_source.setdefault(int(item["source_segment_id"]), []).append(item)
        cursor.execute(
            """SELECT ss.transcript_segment_id, tp.id, tp.speaker_label, tp.participant_id,
                      p.name, ss.start_second, ss.end_second, ss.confidence
                 FROM transcript_segment_speakers ss
                 JOIN transcript_participants tp ON tp.id = ss.transcript_participant_id
                 LEFT JOIN participants p ON p.id = tp.participant_id
                WHERE tp.transcript_version_id = :version_id
                  AND ss.end_date IS NULL AND tp.end_date IS NULL
                ORDER BY ss.transcript_segment_id, ss.start_second, ss.id""",
            {"version_id": version_id},
        )
        for row in cursor.fetchall():
            segment = segment_by_id.get(int(row[0]))
            if segment is not None:
                segment["speakers"].append({
                    "transcript_participant_id": int(row[1]),
                    "speaker_label": row[2],
                    "participant_id": int(row[3]) if row[3] is not None else None,
                    "participant_name": row[4],
                    "start_second": float(row[5]),
                    "end_second": float(row[6]),
                    "confidence": float(row[7]),
                })
        cursor.execute(
            """SELECT rc.id, rc.transcript_segment_id, rc.candidate_type, rc.reason,
                      rc.status, rc.decision, rc.decision_at
                 FROM review_candidates rc
                 JOIN transcript_segments s ON s.id = rc.transcript_segment_id
                WHERE s.transcript_version_id = :version_id AND rc.end_date IS NULL
                ORDER BY s.segment_number, rc.id""",
            {"version_id": version_id if version[1] == "AUTOMATIC_DRAFT" else int(next((item[0] for item in versions if item[1] == "AUTOMATIC_DRAFT"), version_id))},
        )
        candidates = []
        for row in cursor.fetchall():
            source_segment_id = int(row[1])
            direct_segment = segment_by_id.get(source_segment_id)
            if direct_segment is not None:
                # A split child may point at the reviewed parent rather than
                # the automatic source segment. Include that parent and all
                # active children so both halves remain editable together.
                parent_segment = (
                    segment_by_id.get(int(direct_segment["source_segment_id"]))
                    if direct_segment["source_segment_id"] is not None else None
                )
                reviewed_group = [parent_segment] if parent_segment is not None else []
                reviewed_group.append(direct_segment)
                reviewed_group.extend(
                    item for item in segments
                    if item["id"] != direct_segment["id"]
                    and item["source_segment_id"] == direct_segment["id"]
                )
                if direct_segment["source_segment_id"] is not None:
                    reviewed_group.extend(
                        item for item in segments
                        if item["id"] != direct_segment["id"]
                        and item["source_segment_id"] == direct_segment["source_segment_id"]
                        and item not in reviewed_group
                    )
            else:
                reviewed_group = list(segments_by_source.get(source_segment_id, []))
            reviewed_group.sort(key=lambda item: (int(item["segment_number"]), int(item["id"])))
            segment = reviewed_group[0] if reviewed_group else None
            if segment is None:
                continue
            index = segments.index(segment)
            proposal = None
            if row[2] == "SPEAKER_BOUNDARY":
                proposal = suggest_sentence_split(
                    str(segment.get("text") or ""),
                    float(segment["start_second"]),
                    float(segment["end_second"]),
                    [{"speaker_id": item["speaker_label"], "start": item["start_second"], "end": item["end_second"]}
                     for item in segment.get("speakers", [])],
                )
                if proposal:
                    label_to_id = {
                        str(item["speaker_label"]): str(item["transcript_participant_id"])
                        for item in segment.get("speakers", [])
                    }
                    proposal["from_transcript_participant_id"] = label_to_id.get(str(proposal.get("from_speaker_id")))
                    proposal["to_transcript_participant_id"] = label_to_id.get(str(proposal.get("to_speaker_id")))
            candidates.append({
                "id": int(row[0]),
                "segment_id": segment["id"],
                "source_segment_id": source_segment_id,
                "candidate_type": row[2],
                "reason": row[3],
                "status": row[4],
                "decision": row[5],
                "decision_at": _utc_iso(row[6]),
                "segment": segment,
                "reviewed_segments": reviewed_group,
                "previous": segments[index - 1] if index > 0 else None,
                "next": segments[index + 1] if index + 1 < len(segments) else None,
                "proposed_boundary_second": proposal.get("boundary_second") if proposal else None,
                "proposed_split_at": proposal.get("split_at") if proposal else None,
                "proposed_left_speaker": proposal.get("from_transcript_participant_id") if proposal else None,
                "proposed_right_speaker": proposal.get("to_transcript_participant_id") if proposal else None,
            })
        cursor.execute(
            """SELECT asset_type, url
                 FROM media_assets
                WHERE media_item_id = :media_item_id AND end_date IS NULL
                ORDER BY id""",
            {"media_item_id": int(process[2])},
        )
        assets = [{"asset_type": row[0], "url": row[1]} for row in cursor.fetchall()]
        pending = sum(1 for item in candidates if item["status"] == "PENDING")
        return {
            "process": {"id": int(process[0]), "status": process[1]},
            "version": {"id": version_id, "version_type": version[1], "version_number": int(version[2]), "status": version[3]},
            "versions": [{"id": int(row[0]), "version_type": row[1], "version_number": int(row[2]), "status": row[3]} for row in versions],
            "media": {"url": process[5], "media_type": process[6], "duration_second": float(process[7]) if process[7] is not None else None, "assets": assets},
            "segments": segments,
            "candidates": candidates,
            "progress": {"total": len(candidates), "pending": pending, "resolved": len(candidates) - pending},
        }


@router.put("/jobs/{job_id}/review-draft")
def save_review_candidate(job_id: int, request: ReviewCandidateRequest) -> dict[str, object]:
    with connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT status FROM processes
                    WHERE id = :process_id AND end_date IS NULL
                    FOR UPDATE""",
                {"process_id": job_id},
            )
            process = cursor.fetchone()
            if process is None:
                raise HTTPException(status_code=404, detail="Process not found")
            if process[0] != "IN_REVIEW":
                raise HTTPException(status_code=409, detail="Process is not in review")
            decision = request.decision or request.status
            if request.status in {"ACCEPTED", "MODIFIED"}:
                cursor.execute(
                    """SELECT rc.transcript_segment_id, rc.candidate_type
                         FROM review_candidates rc
                         JOIN transcript_segments s ON s.id = rc.transcript_segment_id
                         JOIN transcript_versions v ON v.id = s.transcript_version_id
                        WHERE rc.id = :candidate_id AND rc.end_date IS NULL
                          AND v.process_id = :process_id AND v.version_type = 'AUTOMATIC_DRAFT'
                          AND v.end_date IS NULL""",
                    {"candidate_id": request.candidate_id, "process_id": job_id},
                )
                candidate_row = cursor.fetchone()
                if candidate_row is None:
                    raise HTTPException(status_code=404, detail="Review candidate not found")
                source_segment_id = int(candidate_row[0])
                candidate_type = str(candidate_row[1])
                cursor.execute(
                    """SELECT s.id, s.start_second, s.end_second, s.text, s.source_segment_id,
                              s.segment_number
                         FROM transcript_segments s
                         JOIN transcript_versions v ON v.id = s.transcript_version_id
                        WHERE v.process_id = :process_id AND v.version_type = 'REVIEWED_DRAFT'
                          AND v.end_date IS NULL AND s.end_date IS NULL
                          AND (s.id = :source_segment_id OR s.source_segment_id = :source_segment_id)
                        ORDER BY CASE WHEN s.id = :source_segment_id THEN 0 ELSE 1 END, s.segment_number, s.id""",
                    {"process_id": job_id, "source_segment_id": source_segment_id},
                )
                reviewed_segments = cursor.fetchall()
                if not reviewed_segments:
                    raise HTTPException(status_code=409, detail="Reviewed segment not found")
                segment = reviewed_segments[0]
                segment_id, start_second, end_second, old_text, source_id, segment_number = segment
                new_text = request.text if request.text is not None else old_text
                new_type = request.segment_type or "SPEECH"
                cursor.execute(
                    """SELECT id, transcript_participant_id, start_second, end_second, confidence
                         FROM transcript_segment_speakers
                        WHERE transcript_segment_id = :segment_id AND end_date IS NULL
                        ORDER BY id""",
                    {"segment_id": int(segment_id)},
                )
                old_speakers = cursor.fetchall()

                if request.status == "ACCEPTED":
                    # ACCEPTED is reserved for an unchanged system proposal.
                    # Keep the UI contract small, but reject malformed or
                    # fabricated acceptance requests at the API boundary.
                    if candidate_type != "SPEAKER_BOUNDARY":
                        raise HTTPException(status_code=422, detail="Only speaker-boundary proposals can be accepted")
                    if request.split_at is None or request.left_transcript_participant_id is None or request.right_transcript_participant_id is None:
                        raise HTTPException(status_code=422, detail="Accepted proposal must include both split speakers")
                    speaker_ids = {int(row[1]) for row in old_speakers}
                    if request.left_transcript_participant_id not in speaker_ids or request.right_transcript_participant_id not in speaker_ids:
                        raise HTTPException(status_code=422, detail="Accepted proposal uses an unknown speaker")

                def restore_or_insert_speaker(target_id: int, participant_id: int, target_start: float, target_end: float, confidence: float) -> None:
                    """Reuse a soft-deleted relation before inserting a new one.

                    The speaker uniqueness constraint intentionally ignores end_date,
                    so soft-deleting and immediately reinserting the same relation
                    would raise ORA-00001.
                    """
                    cursor.execute(
                        """SELECT id FROM transcript_segment_speakers
                            WHERE transcript_segment_id = :segment_id
                              AND transcript_participant_id = :participant_id
                              AND start_second = :start_second
                              AND end_second = :end_second
                            ORDER BY CASE WHEN end_date IS NULL THEN 0 ELSE 1 END, id
                            FETCH FIRST 1 ROW ONLY""",
                        {"segment_id": target_id, "participant_id": participant_id,
                         "start_second": target_start, "end_second": target_end},
                    )
                    existing = cursor.fetchone()
                    if existing is not None:
                        cursor.execute(
                            """UPDATE transcript_segment_speakers
                                  SET end_date = NULL, confidence = :confidence,
                                      last_updated = SYSTIMESTAMP
                                WHERE id = :id""",
                            {"id": int(existing[0]), "confidence": confidence},
                        )
                        return
                    cursor.execute("""INSERT INTO transcript_segment_speakers
                        (transcript_segment_id, transcript_participant_id, start_second, end_second, confidence)
                        VALUES (:segment_id, :participant_id, :start_second, :end_second, :confidence)""",
                        {"segment_id": target_id, "participant_id": participant_id,
                         "start_second": target_start, "end_second": target_end, "confidence": confidence})

                if request.split_at is not None:
                    split_at = int(request.split_at)
                    if split_at >= len(new_text):
                        raise HTTPException(status_code=422, detail="split_at must be inside the text")
                    left_text, right_text = new_text[:split_at].rstrip(), new_text[split_at:].lstrip()
                    if not left_text or not right_text:
                        raise HTTPException(status_code=422, detail="Both split parts must contain text")
                    ratio = split_at / len(new_text)
                    boundary = float(start_second) + (float(end_second) - float(start_second)) * ratio
                    cursor.execute("SELECT transcript_version_id, segment_number, source_segment_id FROM transcript_segments WHERE id = :segment_id", {"segment_id": int(segment_id)})
                    version_number_row = cursor.fetchone()
                    existing_followup = next(
                        (item for item in reviewed_segments[1:]
                         if abs(float(item[1]) - float(end_second)) < 0.001),
                        None,
                    )
                    if existing_followup is None:
                        cursor.execute(
                            """UPDATE transcript_segments
                                  SET segment_number = segment_number + 100000, last_updated = SYSTIMESTAMP
                                WHERE transcript_version_id = :version_id AND segment_number > :segment_number
                                  AND end_date IS NULL""",
                            {"version_id": int(version_number_row[0]), "segment_number": int(version_number_row[1])},
                        )
                        cursor.execute(
                            """UPDATE transcript_segments
                                  SET segment_number = segment_number - 99999, last_updated = SYSTIMESTAMP
                                WHERE transcript_version_id = :version_id AND segment_number > :temporary_number
                                  AND end_date IS NULL""",
                            {"version_id": int(version_number_row[0]), "temporary_number": int(version_number_row[1]) + 100000},
                        )
                    else:
                        cursor.execute(
                            """UPDATE transcript_segment_speakers
                                  SET end_date = SYSDATE, last_updated = SYSTIMESTAMP
                                WHERE transcript_segment_id = :segment_id AND end_date IS NULL""",
                            {"segment_id": int(existing_followup[0])},
                        )
                        for extra in reviewed_segments[2:]:
                            cursor.execute(
                                """UPDATE transcript_segment_speakers
                                      SET end_date = SYSDATE, last_updated = SYSTIMESTAMP
                                    WHERE transcript_segment_id = :segment_id AND end_date IS NULL""",
                                {"segment_id": int(extra[0])},
                            )
                            cursor.execute(
                                """UPDATE transcript_segments SET end_date = SYSDATE, last_updated = SYSTIMESTAMP
                                    WHERE id = :segment_id AND end_date IS NULL""",
                                {"segment_id": int(extra[0])},
                            )
                    cursor.execute(
                        "UPDATE transcript_segments SET text = :text, end_second = :end_second, segment_type = :segment_type, last_updated = SYSTIMESTAMP WHERE id = :segment_id",
                        {"text": left_text, "end_second": boundary, "segment_type": new_type, "segment_id": int(segment_id)},
                    )
                    if existing_followup is not None:
                        new_segment_id = int(existing_followup[0])
                        cursor.execute(
                            """UPDATE transcript_segments
                                  SET start_second = :start_second, end_second = :end_second,
                                      text = :text, segment_type = :segment_type, last_updated = SYSTIMESTAMP
                                WHERE id = :segment_id""",
                            {"start_second": boundary, "end_second": end_second, "text": right_text,
                             "segment_type": new_type, "segment_id": new_segment_id},
                        )
                    else:
                        new_segment_var = cursor.var(int)
                        cursor.execute(
                            """INSERT INTO transcript_segments
                               (transcript_version_id, segment_number, start_second, end_second, text, segment_type, source_segment_id)
                               VALUES (:version_id, :segment_number, :start_second, :end_second, :text, :segment_type, :source_segment_id)
                               RETURNING id INTO :new_id""",
                            {"version_id": int(version_number_row[0]), "segment_number": int(version_number_row[1]) + 1,
                             "start_second": boundary, "end_second": end_second, "text": right_text,
                             "segment_type": new_type, "source_segment_id": int(version_number_row[2] or segment_id), "new_id": new_segment_var},
                        )
                        new_segment_id = int(new_segment_var.getvalue()[0])
                    for row in old_speakers:
                        cursor.execute("UPDATE transcript_segment_speakers SET end_date = SYSDATE, last_updated = SYSTIMESTAMP WHERE id = :id AND end_date IS NULL", {"id": int(row[0])})
                        left_pid = request.left_transcript_participant_id or int(row[1])
                        right_pid = request.right_transcript_participant_id or int(row[1])
                        for target_id, target_start, target_end, participant_id in (
                            (int(segment_id), row[2], min(float(row[3]), boundary), left_pid),
                            (new_segment_id, max(float(row[2]), boundary), row[3], right_pid),
                        ):
                            if target_end >= target_start:
                                restore_or_insert_speaker(int(target_id), int(participant_id), float(target_start), float(target_end), float(row[4]))
                else:
                    # Removing a previous split must close every active sibling
                    # belonging to the same automatic source segment.
                    for extra in reviewed_segments[1:]:
                        cursor.execute(
                            """UPDATE transcript_segment_speakers
                                  SET end_date = SYSDATE, last_updated = SYSTIMESTAMP
                                WHERE transcript_segment_id = :segment_id AND end_date IS NULL""",
                            {"segment_id": int(extra[0])},
                        )
                        cursor.execute(
                            """UPDATE transcript_segments
                                  SET end_date = SYSDATE, last_updated = SYSTIMESTAMP
                                WHERE id = :segment_id AND end_date IS NULL""",
                            {"segment_id": int(extra[0])},
                        )
                    cursor.execute(
                        "UPDATE transcript_segments SET text = :text, segment_type = :segment_type, last_updated = SYSTIMESTAMP WHERE id = :segment_id",
                        {"text": new_text, "segment_type": new_type, "segment_id": int(segment_id)},
                    )
                    if new_type == "SYSTEM_NOTICE":
                        cursor.execute("UPDATE transcript_segment_speakers SET end_date = SYSDATE, last_updated = SYSTIMESTAMP WHERE transcript_segment_id = :segment_id AND end_date IS NULL", {"segment_id": int(segment_id)})
                    elif request.left_transcript_participant_id is not None:
                        cursor.execute("UPDATE transcript_segment_speakers SET end_date = SYSDATE, last_updated = SYSTIMESTAMP WHERE transcript_segment_id = :segment_id AND end_date IS NULL", {"segment_id": int(segment_id)})
                        restore_or_insert_speaker(int(segment_id), int(request.left_transcript_participant_id), float(start_second), float(end_second), 1.0)
            cursor.execute(
                """UPDATE review_candidates rc
                      SET status = :status, decision = :decision,
                          decision_at = SYSTIMESTAMP, last_updated = SYSTIMESTAMP
                    WHERE rc.id = :candidate_id AND rc.end_date IS NULL
                      AND EXISTS (
                          SELECT 1 FROM transcript_segments s
                          JOIN transcript_versions v ON v.id = s.transcript_version_id
                           WHERE s.id = rc.transcript_segment_id
                             AND v.process_id = :process_id
                             AND v.version_type = 'AUTOMATIC_DRAFT'
                             AND v.end_date IS NULL
                      )""",
                {"status": request.status, "decision": decision, "candidate_id": request.candidate_id, "process_id": job_id},
            )
            if cursor.rowcount != 1:
                raise HTTPException(status_code=404, detail="Review candidate not found")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    regenerated = _regenerate_reviewed_artifacts(job_id)
    return {"candidate_id": request.candidate_id, "status": request.status, "decision": decision,
            "artifacts_regenerated": regenerated}


@router.api_route("/jobs/{job_id}/participant-review", methods=["GET", "PUT"])
async def get_participant_review(request: Request, job_id: int) -> dict[str, object]:
    """Return the automatic draft and evidence needed to assign speakers."""
    if request.method == "PUT":
        payload = await request.json()
        return save_participant_review(job_id, ParticipantReviewRequest.model_validate(payload))

    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT p.status, p.media_item_id, m.title, m.media_type, m.canonical_url,
                      v.id, v.version_number
                 FROM processes p
                 JOIN media_items m ON m.id = p.media_item_id
                 JOIN transcript_versions v ON v.process_id = p.id
                WHERE p.id = :process_id AND p.end_date IS NULL
                  AND m.end_date IS NULL AND v.end_date IS NULL
                  AND v.version_type = 'AUTOMATIC_DRAFT'
                ORDER BY v.version_number DESC
                FETCH FIRST 1 ROW ONLY""",
            {"process_id": job_id},
        )
        version = cursor.fetchone()
        if version is None:
            raise HTTPException(status_code=409, detail="Automatic draft is not available")

        cursor.execute(
            """SELECT id
                 FROM transcript_versions
                WHERE process_id = :process_id
                  AND version_type = 'REVIEWED_DRAFT'
                  AND end_date IS NULL
                ORDER BY version_number DESC
                FETCH FIRST 1 ROW ONLY""",
            {"process_id": job_id},
        )
        reviewed = cursor.fetchone()
        mapping_version_id = int(reviewed[0]) if reviewed else int(version[5])
        cursor.execute(
            """SELECT tp.id, tp.speaker_label, tp.participant_id, tp.role,
                      tp.mapping_status, p.name
                 FROM transcript_participants tp
                 LEFT JOIN participants p
                   ON p.id = tp.participant_id AND p.end_date IS NULL
                WHERE tp.transcript_version_id = :version_id
                  AND tp.end_date IS NULL
                ORDER BY tp.speaker_label""",
            {"version_id": mapping_version_id},
        )
        participants = cursor.fetchall()

        # A segment is usable as a speaker sample only when one distinct
        # automatic-draft speaker is linked to it.  SYSTEM_NOTICE rows are
        # excluded in SQL, rather than hidden later in the UI.
        cursor.execute(
            """SELECT tp.speaker_label, s.id, s.segment_number,
                      s.start_second, s.end_second, s.text,
                      MAX(ss.confidence) AS confidence
                 FROM transcript_segments s
                 JOIN transcript_segment_speakers ss
                   ON ss.transcript_segment_id = s.id
                 JOIN transcript_participants tp
                   ON tp.id = ss.transcript_participant_id
                WHERE s.transcript_version_id = :version_id
                  AND s.segment_type = 'SPEECH'
                  AND s.end_date IS NULL
                  AND ss.end_date IS NULL
                  AND tp.end_date IS NULL
                GROUP BY tp.speaker_label, s.id, s.segment_number,
                         s.start_second, s.end_second, s.text
               HAVING COUNT(DISTINCT ss.transcript_participant_id) = 1""",
            {"version_id": version[5]},
        )
        sample_rows = [
            {
                "speaker_label": row[0],
                "segment_id": row[1],
                "segment_number": row[2],
                "start_second": float(row[3]),
                "end_second": float(row[4]),
                "text": row[5],
                "confidence": float(row[6]) if row[6] is not None else None,
            }
            for row in cursor.fetchall()
        ]
        samples = select_speaker_samples(sample_rows)
        sample_by_label = defaultdict(list)
        for label, entries in samples.items():
            sample_by_label[label].extend(entries)

        return {
            "process_id": job_id,
            "status": version[0],
            "transcript_version_id": version[5],
            "mapping_version_id": mapping_version_id,
            "media": {
                "title": version[2],
                "media_type": version[3],
                "url": version[4],
            },
            "speakers": [
                {
                    "transcript_participant_id": row[0],
                    "speaker_label": row[1],
                    "participant_id": row[2],
                    "role": row[3],
                    "mapping_status": row[4],
                    "participant_name": row[5],
                    "samples": sample_by_label[row[1]],
                }
                for row in participants
            ],
        }


def save_participant_review(job_id: int, request: ParticipantReviewRequest) -> dict[str, object]:
    labels_in_request = [mapping.speaker_label for mapping in request.mappings]
    if len(labels_in_request) != len(set(labels_in_request)):
        raise HTTPException(status_code=422, detail="Each speaker label may occur only once")
    mappings = {mapping.speaker_label: mapping for mapping in request.mappings}
    with connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT status
                     FROM processes
                    WHERE id = :process_id AND end_date IS NULL
                    FOR UPDATE""",
                {"process_id": job_id},
            )
            process = cursor.fetchone()
            if process is None:
                raise HTTPException(status_code=404, detail="Process not found")
            if process[0] != "WAITING_FOR_PARTICIPANTS":
                raise HTTPException(status_code=409, detail="Process is not waiting for participants")
            cursor.execute(
                """SELECT p.status, a.id, v.id, v.version_type
                     FROM processes p
                     JOIN activities a ON a.process_id = p.id
                     JOIN transcript_versions v ON v.process_id = p.id
                    WHERE p.id = :process_id AND p.end_date IS NULL
                      AND a.finished_at IS NULL AND a.activity_type = 'WAITING_FOR_PARTICIPANTS'
                      AND a.end_date IS NULL AND v.version_type = 'AUTOMATIC_DRAFT'
                      AND v.end_date IS NULL
                    ORDER BY v.version_number DESC
                    FETCH FIRST 1 ROW ONLY""",
                {"process_id": job_id},
            )
            active = cursor.fetchone()
            if active is None:
                raise HTTPException(status_code=409, detail="Process is not waiting for participants")
            process_status, waiting_activity_id, automatic_version_id, _ = active

            cursor.execute(
                """SELECT id, speaker_label, participant_id, role, mapping_status
                     FROM transcript_participants
                    WHERE transcript_version_id = :version_id AND end_date IS NULL
                    ORDER BY speaker_label""",
                {"version_id": automatic_version_id},
            )
            automatic_participants = cursor.fetchall()
            labels = {row[1] for row in automatic_participants}
            unknown_labels = set(mappings) - labels
            if unknown_labels:
                raise HTTPException(status_code=422, detail={"message": "Unknown speaker label", "labels": sorted(unknown_labels)})
            for mapping in mappings.values():
                status = mapping.mapping_status
                if status == "CONFIRMED" and mapping.participant_id is None:
                    raise HTTPException(status_code=422, detail=f"{mapping.speaker_label} requires participant_id")
                if status != "CONFIRMED" and mapping.participant_id is not None:
                    raise HTTPException(status_code=422, detail=f"{mapping.speaker_label} cannot have participant_id for {status}")
                if mapping.role is not None and len(mapping.role) > 120:
                    raise HTTPException(status_code=422, detail=f"{mapping.speaker_label} role is too long")
            for mapping in mappings.values():
                if mapping.participant_id is not None:
                    cursor.execute("SELECT 1 FROM participants WHERE id = :id AND end_date IS NULL", {"id": mapping.participant_id})
                    if cursor.fetchone() is None:
                        raise HTTPException(status_code=422, detail=f"Participant not found: {mapping.participant_id}")

            cursor.execute(
                """SELECT id, version_number
                     FROM transcript_versions
                    WHERE process_id = :process_id AND version_type = 'REVIEWED_DRAFT'
                      AND end_date IS NULL
                    ORDER BY version_number DESC
                    FETCH FIRST 1 ROW ONLY""",
                {"process_id": job_id},
            )
            reviewed = cursor.fetchone()
            if reviewed is None:
                cursor.execute("SELECT NVL(MAX(version_number), 0) + 1 FROM transcript_versions WHERE process_id = :process_id", {"process_id": job_id})
                next_version = int(cursor.fetchone()[0])
                version_var = cursor.var(int)
                cursor.execute(
                    """INSERT INTO transcript_versions
                       (process_id, activity_id, version_number, version_type, status)
                       VALUES (:process_id, :activity_id, :version_number, 'REVIEWED_DRAFT', 'DRAFT')
                       RETURNING id INTO :version_id""",
                    {
                        "process_id": job_id,
                        "activity_id": waiting_activity_id,
                        "version_number": next_version,
                        "version_id": version_var,
                    },
                )
                reviewed_version_id = int(version_var.getvalue()[0])
                cursor.execute(
                    """SELECT id, speaker_label, participant_id, role, mapping_status
                         FROM transcript_participants
                        WHERE transcript_version_id = :version_id AND end_date IS NULL
                        ORDER BY speaker_label""",
                    {"version_id": automatic_version_id},
                )
                participant_id_by_old_id: dict[int, int] = {}
                for old_id, label, participant_id, role, mapping_status in cursor.fetchall():
                    new_participant_var = cursor.var(int)
                    cursor.execute(
                        """INSERT INTO transcript_participants
                           (transcript_version_id, speaker_label, participant_id, role, mapping_status)
                           VALUES (:version_id, :speaker_label, :participant_id, :role, :mapping_status)
                           RETURNING id INTO :participant_id_out""",
                        {
                            "version_id": reviewed_version_id,
                            "speaker_label": label,
                            "participant_id": participant_id,
                            "role": role,
                            "mapping_status": mapping_status,
                            "participant_id_out": new_participant_var,
                        },
                    )
                    participant_id_by_old_id[int(old_id)] = int(new_participant_var.getvalue()[0])
                cursor.execute(
                    """SELECT id, segment_number, start_second, end_second, text, segment_type
                         FROM transcript_segments
                        WHERE transcript_version_id = :version_id AND end_date IS NULL
                        ORDER BY segment_number, id""",
                    {"version_id": automatic_version_id},
                )
                segment_id_map: dict[int, int] = {}
                for old_segment_id, segment_number, start_second, end_second, text, segment_type in cursor.fetchall():
                    new_segment_var = cursor.var(int)
                    cursor.execute(
                        """INSERT INTO transcript_segments
                           (transcript_version_id, segment_number, start_second, end_second, text, segment_type, source_segment_id)
                           VALUES (:version_id, :segment_number, :start_second, :end_second, :text, :segment_type, :source_segment_id)
                           RETURNING id INTO :segment_id""",
                        {
                            "version_id": reviewed_version_id,
                            "segment_number": segment_number,
                            "start_second": start_second,
                            "end_second": end_second,
                            "text": text,
                            "segment_type": segment_type,
                            "source_segment_id": old_segment_id,
                            "segment_id": new_segment_var,
                        },
                    )
                    segment_id_map[int(old_segment_id)] = int(new_segment_var.getvalue()[0])
                cursor.execute(
                    """SELECT ss.transcript_segment_id, ss.transcript_participant_id,
                              ss.start_second, ss.end_second, ss.confidence
                         FROM transcript_segment_speakers ss
                         JOIN transcript_segments s ON s.id = ss.transcript_segment_id
                        WHERE s.transcript_version_id = :version_id AND ss.end_date IS NULL
                        ORDER BY ss.id""",
                    {"version_id": automatic_version_id},
                )
                for old_segment_id, old_participant_id, start_second, end_second, confidence in cursor.fetchall():
                    cursor.execute(
                        """INSERT INTO transcript_segment_speakers
                           (transcript_segment_id, transcript_participant_id, start_second, end_second, confidence)
                           VALUES (:segment_id, :participant_id, :start_second, :end_second, :confidence)""",
                        {
                            "segment_id": segment_id_map[int(old_segment_id)],
                            "participant_id": participant_id_by_old_id[int(old_participant_id)],
                            "start_second": start_second,
                            "end_second": end_second,
                            "confidence": confidence,
                        },
                    )
            else:
                reviewed_version_id = int(reviewed[0])

            cursor.execute(
                """SELECT id, speaker_label
                     FROM transcript_participants
                    WHERE transcript_version_id = :version_id AND end_date IS NULL""",
                {"version_id": reviewed_version_id},
            )
            reviewed_participants = {row[1]: int(row[0]) for row in cursor.fetchall()}
            for label, mapping in mappings.items():
                cursor.execute(
                    """UPDATE transcript_participants
                          SET participant_id = :participant_id,
                              role = :role,
                              mapping_status = :mapping_status,
                              last_updated = SYSTIMESTAMP
                        WHERE id = :id AND end_date IS NULL""",
                    {
                        "participant_id": mapping.participant_id,
                        "role": mapping.role,
                        "mapping_status": mapping.mapping_status,
                        "id": reviewed_participants[label],
                    },
                )

            cursor.execute(
                """SELECT speaker_label, mapping_status
                     FROM transcript_participants
                    WHERE transcript_version_id = :version_id AND end_date IS NULL
                      AND mapping_status = 'UNCONFIRMED'""",
                {"version_id": reviewed_version_id},
            )
            unresolved = [row[0] for row in cursor.fetchall()]
            if request.confirm and unresolved:
                raise HTTPException(status_code=409, detail={"message": "All speakers must be resolved before confirmation", "unresolved_labels": unresolved})
            if request.confirm:
                cursor.execute("SELECT COUNT(*) FROM transcript_participants WHERE transcript_version_id = :version_id AND end_date IS NULL AND mapping_status = 'CONFIRMED' AND participant_id IS NULL", {"version_id": reviewed_version_id})
                if cursor.fetchone()[0]:
                    raise HTTPException(status_code=409, detail="Confirmed speaker mapping requires a participant")
                cursor.execute(
                    """UPDATE activities
                          SET finished_at = SYSTIMESTAMP, result = 'OK', last_updated = SYSTIMESTAMP
                        WHERE id = :activity_id AND finished_at IS NULL""",
                    {"activity_id": waiting_activity_id},
                )
                cursor.execute(
                    """INSERT INTO activities (process_id, previous_activity_id, activity_type, started_at)
                         VALUES (:process_id, :previous_activity_id, 'IN_REVIEW', SYSTIMESTAMP)""",
                    {"process_id": job_id, "previous_activity_id": waiting_activity_id},
                )
                cursor.execute("UPDATE processes SET status = 'IN_REVIEW', last_updated = SYSTIMESTAMP WHERE id = :process_id", {"process_id": job_id})
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    regenerated = _regenerate_reviewed_artifacts(job_id, reviewed_version_id)
    return {
        "process_id": job_id,
        "transcript_version_id": reviewed_version_id,
        "status": "IN_REVIEW" if request.confirm else process_status,
        "unresolved_labels": unresolved,
        "confirmed": bool(request.confirm and not unresolved),
        "artifacts_regenerated": regenerated,
    }


@router.post("/jobs/{job_id}/finalize")
def finalize_job(job_id: int) -> dict[str, object]:
    """Create the immutable FINAL version from the current reviewed draft."""
    created_paths: list[Path] = []
    with connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT status, media_item_id FROM processes
                    WHERE id = :process_id AND end_date IS NULL FOR UPDATE""",
                {"process_id": job_id},
            )
            process = cursor.fetchone()
            if process is None:
                raise HTTPException(status_code=404, detail="Process not found")
            if process[0] != "IN_REVIEW":
                raise HTTPException(status_code=409, detail="Process must be IN_REVIEW before finalization")

            cursor.execute(
                """SELECT id, version_number FROM transcript_versions
                    WHERE process_id = :process_id AND version_type = 'REVIEWED_DRAFT'
                      AND end_date IS NULL ORDER BY version_number DESC
                    FETCH FIRST 1 ROW ONLY""",
                {"process_id": job_id},
            )
            reviewed = cursor.fetchone()
            if reviewed is None:
                raise HTTPException(status_code=409, detail="REVIEWED_DRAFT is not available")
            reviewed_version_id = int(reviewed[0])

            cursor.execute(
                """SELECT COUNT(*) FROM review_candidates rc
                    JOIN transcript_segments s ON s.id = rc.transcript_segment_id
                    WHERE s.transcript_version_id = (
                        SELECT id FROM transcript_versions
                         WHERE process_id = :process_id AND version_type = 'AUTOMATIC_DRAFT'
                           AND end_date IS NULL FETCH FIRST 1 ROW ONLY)
                      AND rc.end_date IS NULL AND rc.status = 'PENDING'""",
                {"process_id": job_id},
            )
            pending = int(cursor.fetchone()[0])
            if pending:
                raise HTTPException(status_code=409, detail={"message": "All review candidates must be resolved", "pending": pending})
            cursor.execute(
                """SELECT COUNT(*) FROM transcript_participants
                    WHERE transcript_version_id = :version_id AND end_date IS NULL
                      AND mapping_status = 'UNCONFIRMED'""",
                {"version_id": reviewed_version_id},
            )
            unresolved = int(cursor.fetchone()[0])
            if unresolved:
                raise HTTPException(status_code=409, detail={"message": "All speakers must be confirmed or marked UNKNOWN", "unresolved": unresolved})

            cursor.execute("SELECT id FROM activities WHERE process_id = :process_id AND activity_type = 'IN_REVIEW' AND finished_at IS NULL AND end_date IS NULL ORDER BY id DESC FETCH FIRST 1 ROW ONLY", {"process_id": job_id})
            activity = cursor.fetchone()
            if activity is None:
                raise HTTPException(status_code=409, detail="Active IN_REVIEW activity is not available")
            activity_id = int(activity[0])

            cursor.execute("SELECT NVL(MAX(version_number), 0) + 1 FROM transcript_versions WHERE process_id = :process_id", {"process_id": job_id})
            next_version = int(cursor.fetchone()[0])
            version_var = cursor.var(int)
            cursor.execute(
                """INSERT INTO transcript_versions
                   (process_id, activity_id, version_number, version_type, status)
                   VALUES (:process_id, :activity_id, :version_number, 'FINAL', 'FINAL')
                   RETURNING id INTO :version_id""",
                {"process_id": job_id, "activity_id": activity_id, "version_number": next_version, "version_id": version_var},
            )
            final_version_id = int(version_var.getvalue()[0])

            cursor.execute("SELECT id, speaker_label, participant_id, role, mapping_status FROM transcript_participants WHERE transcript_version_id = :version_id AND end_date IS NULL ORDER BY id", {"version_id": reviewed_version_id})
            participant_map: dict[int, int] = {}
            for old_id, label, participant_id, role, mapping_status in cursor.fetchall():
                out = cursor.var(int)
                cursor.execute(
                    """INSERT INTO transcript_participants
                       (transcript_version_id, speaker_label, participant_id, role, mapping_status)
                       VALUES (:version_id, :label, :participant_id, :role, :mapping_status)
                       RETURNING id INTO :new_id""",
                    {"version_id": final_version_id, "label": label, "participant_id": participant_id, "role": role, "mapping_status": mapping_status, "new_id": out},
                )
                participant_map[int(old_id)] = int(out.getvalue()[0])

            cursor.execute("SELECT id, segment_number, start_second, end_second, text, segment_type, source_segment_id FROM transcript_segments WHERE transcript_version_id = :version_id AND end_date IS NULL ORDER BY segment_number, id", {"version_id": reviewed_version_id})
            segment_map: dict[int, int] = {}
            for old_id, number, start, end, text_value, segment_type, source_id in cursor.fetchall():
                out = cursor.var(int)
                cursor.execute(
                    """INSERT INTO transcript_segments
                       (transcript_version_id, segment_number, start_second, end_second, text, segment_type, source_segment_id)
                       VALUES (:version_id, :segment_number, :start_second, :end_second, :text_value, :segment_type, :source_id)
                       RETURNING id INTO :new_id""",
                    {"version_id": final_version_id, "segment_number": number, "start_second": start, "end_second": end, "text_value": text_value, "segment_type": segment_type, "source_id": source_id, "new_id": out},
                )
                segment_map[int(old_id)] = int(out.getvalue()[0])

            cursor.execute("""SELECT transcript_segment_id, transcript_participant_id, start_second, end_second, confidence
                              FROM transcript_segment_speakers WHERE transcript_segment_id IN
                              (SELECT id FROM transcript_segments WHERE transcript_version_id = :version_id)
                                AND end_date IS NULL ORDER BY id""", {"version_id": reviewed_version_id})
            for old_segment_id, old_participant_id, start, end, confidence in cursor.fetchall():
                cursor.execute("""INSERT INTO transcript_segment_speakers
                           (transcript_segment_id, transcript_participant_id, start_second, end_second, confidence)
                           VALUES (:segment_id, :participant_id, :start_second, :end_second, :confidence)""",
                               {"segment_id": segment_map[int(old_segment_id)], "participant_id": participant_map[int(old_participant_id)], "start_second": start, "end_second": end, "confidence": confidence})

            cursor.execute("""SELECT a.path FROM transcript_versions tv
                              JOIN transcript_artifacts ta ON ta.transcript_version_id = tv.id
                              JOIN artifacts a ON a.id = ta.artifact_id
                             WHERE tv.process_id = :process_id AND tv.version_type = 'AUTOMATIC_DRAFT'
                               AND tv.end_date IS NULL AND ta.end_date IS NULL AND a.end_date IS NULL
                             ORDER BY a.id FETCH FIRST 1 ROW ONLY""", {"process_id": job_id})
            source = cursor.fetchone()
            if source is None:
                raise HTTPException(status_code=409, detail="Automatic transcript artifact is not available")
            source_path = Path(str(source[0])).resolve()
            source_path.parent.mkdir(parents=True, exist_ok=True)
            markdown_path = source_path.parent / "final.md"
            json_path = source_path.parent / "final.json"
            markdown, json_content = _render_transcript_version(cursor, final_version_id, "FINAL")
            markdown_path.write_bytes(markdown)
            json_path.write_bytes(json_content)
            created_paths.extend((markdown_path, json_path))
            for artifact_type, path, content_type, content in (("FINAL_MARKDOWN", markdown_path, "text/markdown", markdown), ("FINAL_JSON", json_path, "application/json", json_content)):
                digest = sha256(content).hexdigest()
                artifact_var = cursor.var(int)
                cursor.execute("""INSERT INTO artifacts (artifact_type, path, content_type, size_byte, sha256)
                                  VALUES (:artifact_type, :path, :content_type, :size_byte, :sha256)
                                  RETURNING id INTO :artifact_id""", {"artifact_type": artifact_type, "path": str(path), "content_type": content_type, "size_byte": len(content), "sha256": digest, "artifact_id": artifact_var})
                artifact_id = int(artifact_var.getvalue()[0])
                cursor.execute("INSERT INTO transcript_artifacts (transcript_version_id, artifact_id) VALUES (:version_id, :artifact_id)", {"version_id": final_version_id, "artifact_id": artifact_id})
                cursor.execute("INSERT INTO activity_artifacts (activity_id, artifact_id) VALUES (:activity_id, :artifact_id)", {"activity_id": activity_id, "artifact_id": artifact_id})

            cursor.execute("UPDATE activities SET finished_at = SYSTIMESTAMP, result = 'OK', last_updated = SYSTIMESTAMP WHERE id = :activity_id AND finished_at IS NULL", {"activity_id": activity_id})
            cursor.execute("UPDATE processes SET status = 'FINISHED', finished_at = SYSTIMESTAMP, last_updated = SYSTIMESTAMP WHERE id = :process_id AND status = 'IN_REVIEW'", {"process_id": job_id})
            conn.commit()
            return {"process_id": job_id, "status": "FINISHED", "transcript_version_id": final_version_id, "artifacts": [str(markdown_path), str(json_path)]}
        except Exception:
            conn.rollback()
            for path in created_paths:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise


@router.get("/jobs/{job_id}/artifacts/{artifact_id}")
def download_job_artifact(job_id: int, artifact_id: int):
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT DISTINCT a.path, a.content_type
                 FROM processes p
                 JOIN transcript_versions tv ON tv.process_id = p.id OR tv.process_id = p.parent_process_id
                 JOIN transcript_artifacts ta ON ta.transcript_version_id = tv.id
                 JOIN artifacts a ON a.id = ta.artifact_id
                WHERE p.id = :process_id AND a.id = :artifact_id
                  AND a.end_date IS NULL AND tv.end_date IS NULL AND ta.end_date IS NULL""",
            {"process_id": job_id, "artifact_id": artifact_id},
        )
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Artifact not found")
        path = Path(str(row[0])).resolve()
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Artifact file is not available")
        filename = path.name.replace('"', "'").replace("\r", "").replace("\n", "")
        return FileResponse(path, media_type=str(row[1]), headers={"Content-Disposition": f'inline; filename="{filename}"'})


def _job_summary(row) -> dict[str, object]:
    return {
        "id": row[0], "submitted_url": row[1], "title": row[2], "status": row[3],
        "submitted_at": _utc_iso(row[4]), "resolved_at": _utc_iso(row[5]),
        "error_code": row[6], "error_message": row[7],
    }


def _require_process(cursor, process_id: int) -> None:
    cursor.execute("SELECT 1 FROM processes WHERE id = :id AND end_date IS NULL", {"id": process_id})
    if cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Process not found")


def _artifact(row) -> dict[str, object]:
    return {"id": row[0], "artifact_type": row[1], "path": row[2], "content_type": row[3], "size_byte": row[4], "sha256": row[5]}


def _upsert_reviewed_artifact(cursor, version_id: int, artifact_type: str, path: Path,
                              content_type: str, content: bytes) -> None:
    digest = sha256(content).hexdigest()
    cursor.execute(
        """SELECT a.id
             FROM transcript_artifacts ta
             JOIN artifacts a ON a.id = ta.artifact_id
            WHERE ta.transcript_version_id = :version_id
              AND a.artifact_type IN ('REVIEWED_DRAFT_MD', 'REVIEWED_TRANSCRIPT_MARKDOWN', 'REVIEWED_DRAFT_JSON')
              AND (a.artifact_type = :artifact_type OR a.artifact_type = 'REVIEWED_TRANSCRIPT_MARKDOWN')
              AND ta.end_date IS NULL AND a.end_date IS NULL
            FETCH FIRST 1 ROW ONLY""",
        {"version_id": version_id, "artifact_type": artifact_type},
    )
    existing = cursor.fetchone()
    if existing is None:
        artifact_var = cursor.var(int)
        cursor.execute(
            """INSERT INTO artifacts (artifact_type, path, content_type, size_byte, sha256)
               VALUES (:artifact_type, :path, :content_type, :size_byte, :sha256)
               RETURNING id INTO :artifact_id""",
            {"artifact_type": artifact_type, "path": str(path), "content_type": content_type,
             "size_byte": len(content), "sha256": digest, "artifact_id": artifact_var},
        )
        artifact_id = int(artifact_var.getvalue()[0])
        cursor.execute(
            "INSERT INTO transcript_artifacts (transcript_version_id, artifact_id) VALUES (:version_id, :artifact_id)",
            {"version_id": version_id, "artifact_id": artifact_id},
        )
    else:
        cursor.execute(
            """UPDATE artifacts
                  SET artifact_type = :artifact_type, path = :path, content_type = :content_type,
                      size_byte = :size_byte, sha256 = :sha256, last_updated = SYSTIMESTAMP
                WHERE id = :artifact_id AND end_date IS NULL""",
            {"artifact_type": artifact_type, "path": str(path), "content_type": content_type,
             "size_byte": len(content), "sha256": digest, "artifact_id": int(existing[0])},
        )


def _render_transcript_version(cursor, version_id: int, version_type: str) -> tuple[bytes, bytes]:
    cursor.execute(
        """SELECT s.id, s.segment_number, s.start_second, s.end_second, s.text, s.segment_type,
                  tp.speaker_label, p.name, ss.start_second, ss.end_second, ss.confidence
             FROM transcript_segments s
             LEFT JOIN transcript_segment_speakers ss ON ss.transcript_segment_id = s.id AND ss.end_date IS NULL
             LEFT JOIN transcript_participants tp ON tp.id = ss.transcript_participant_id AND tp.end_date IS NULL
             LEFT JOIN participants p ON p.id = tp.participant_id AND p.end_date IS NULL
            WHERE s.transcript_version_id = :version_id AND s.end_date IS NULL
            ORDER BY s.segment_number, s.id, ss.id""", {"version_id": version_id})
    segments: list[dict[str, object]] = []
    current = None
    for segment_id, number, start, end, text_value, segment_type, label, name, speaker_start, speaker_end, confidence in cursor.fetchall():
        if current is None or int(segment_id) != current["id"]:
            current = {"id": int(segment_id), "segment_number": int(number), "start_second": float(start), "end_second": float(end), "text": text_value, "segment_type": segment_type, "speakers": []}
            segments.append(current)
        if label is not None:
            current["speakers"].append({"speaker_label": label, "participant_name": name, "start_second": float(speaker_start), "end_second": float(speaker_end), "confidence": float(confidence)})
    for segment in segments:
        totals: dict[tuple[object, object], float] = {}
        for speaker in segment["speakers"]:
            key = (speaker.get("speaker_label"), speaker.get("participant_name"))
            totals[key] = totals.get(key, 0.0) + max(0.0, float(speaker["end_second"]) - float(speaker["start_second"]))
        dominant = max(totals.items(), key=lambda item: item[1], default=None)
        segment["dominant_speaker"] = ({"speaker_label": dominant[0][0], "participant_name": dominant[0][1], "duration_second": dominant[1]} if dominant else None)
    lines = ["# Transkriptsioon", ""]
    for segment in segments:
        timestamp = _format_transcript_time(segment["start_second"])
        if segment["segment_type"] == "SYSTEM_NOTICE":
            lines.append(f"*Ekraaniteade ({timestamp}): {segment['text']}*")
        else:
            dominant = segment.get("dominant_speaker") or {}
            speaker = dominant.get("participant_name") or dominant.get("speaker_label")
            lines.append(f"*{timestamp}* {f'**{speaker}** ' if speaker else ''}{segment['text']}")
        lines.append("")
    markdown = ("\n".join(lines).rstrip() + "\n").encode("utf-8")
    return markdown, (json.dumps({"version_id": version_id, "version_type": version_type, "segments": segments}, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _regenerate_reviewed_artifacts(process_id: int, version_id: int | None = None) -> bool:
    """Regenerate the current REVIEWED_DRAFT files after the DB commit.

    The user transaction is already committed when this function runs.  A
    failed file generation therefore cannot undo a valid mapping or decision.
    """
    try:
        with connection() as conn:
            cursor = conn.cursor()
            if version_id is None:
                cursor.execute(
                    """SELECT id FROM transcript_versions
                        WHERE process_id = :process_id AND version_type = 'REVIEWED_DRAFT'
                          AND end_date IS NULL
                        ORDER BY version_number DESC FETCH FIRST 1 ROW ONLY""",
                    {"process_id": process_id},
                )
                row = cursor.fetchone()
                if row is None:
                    return False
                version_id = int(row[0])
            cursor.execute(
                """SELECT a.path
                     FROM transcript_versions tv
                     JOIN transcript_artifacts ta ON ta.transcript_version_id = tv.id
                     JOIN artifacts a ON a.id = ta.artifact_id
                    WHERE tv.process_id = :process_id AND tv.version_type = 'AUTOMATIC_DRAFT'
                      AND a.end_date IS NULL AND tv.end_date IS NULL AND ta.end_date IS NULL
                    ORDER BY a.id FETCH FIRST 1 ROW ONLY""",
                {"process_id": process_id},
            )
            source = cursor.fetchone()
            if source is None:
                return False

            cursor.execute(
                """SELECT s.id, s.segment_number, s.start_second, s.end_second, s.text, s.segment_type,
                          tp.speaker_label, p.name, ss.start_second, ss.end_second, ss.confidence
                     FROM transcript_segments s
                     LEFT JOIN transcript_segment_speakers ss
                       ON ss.transcript_segment_id = s.id AND ss.end_date IS NULL
                     LEFT JOIN transcript_participants tp
                       ON tp.id = ss.transcript_participant_id AND tp.end_date IS NULL
                     LEFT JOIN participants p
                       ON p.id = tp.participant_id AND p.end_date IS NULL
                    WHERE s.transcript_version_id = :version_id AND s.end_date IS NULL
                    ORDER BY s.segment_number, s.id, ss.id""",
                {"version_id": version_id},
            )
            rows = cursor.fetchall()
            segments = []
            current = None
            for segment_id, number, start, end, text_value, segment_type, label, name, speaker_start, speaker_end, confidence in rows:
                if current is None or int(segment_id) != current["id"]:
                    current = {"id": int(segment_id), "segment_number": int(number),
                               "start_second": float(start), "end_second": float(end),
                               "text": text_value, "segment_type": segment_type, "speakers": []}
                    segments.append(current)
                if label is not None:
                    current["speakers"].append({"speaker_label": label,
                                                "participant_name": name,
                                                "start_second": float(speaker_start),
                                                "end_second": float(speaker_end),
                                                "confidence": float(confidence)})

            for segment in segments:
                totals: dict[tuple[object, object], float] = {}
                for speaker in segment["speakers"]:
                    key = (speaker.get("speaker_label"), speaker.get("participant_name"))
                    totals[key] = totals.get(key, 0.0) + max(
                        0.0, float(speaker["end_second"]) - float(speaker["start_second"])
                    )
                dominant = max(totals.items(), key=lambda item: item[1], default=None)
                segment["dominant_speaker"] = (
                    {"speaker_label": dominant[0][0], "participant_name": dominant[0][1],
                     "duration_second": dominant[1]}
                    if dominant is not None else None
                )

            lines = ["# Transkriptsioon", ""]
            for segment in segments:
                timestamp = _format_transcript_time(segment["start_second"])
                if segment["segment_type"] == "SYSTEM_NOTICE":
                    lines.append(f"*Ekraaniteade ({timestamp}): {segment['text']}*")
                else:
                    dominant = segment.get("dominant_speaker") or {}
                    speaker = dominant.get("participant_name") or dominant.get("speaker_label")
                    prefix = f"**{speaker}** " if speaker else ""
                    lines.append(f"*{timestamp}* {prefix}{segment['text']}")
                lines.append("")
            markdown = ("\n".join(lines).rstrip() + "\n").encode("utf-8")
            payload = {"version_id": int(version_id), "version_type": "REVIEWED_DRAFT",
                       "segments": segments}
            json_content = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            source_path = Path(str(source[0])).resolve()
            source_path.parent.mkdir(parents=True, exist_ok=True)
            markdown_path = source_path.parent / "reviewed-draft.md"
            json_path = source_path.parent / "reviewed-draft.json"
            markdown_path.write_bytes(markdown)
            json_path.write_bytes(json_content)
            _upsert_reviewed_artifact(cursor, int(version_id), "REVIEWED_DRAFT_MD",
                                      markdown_path, "text/markdown", markdown)
            _upsert_reviewed_artifact(cursor, int(version_id), "REVIEWED_DRAFT_JSON",
                                      json_path, "application/json", json_content)
            conn.commit()
            return True
    except Exception:
        return False


def _format_transcript_time(value) -> str:
    seconds = max(0, int(float(value or 0)))
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"


def _find_active_process(cursor, media_id: int) -> int | None:
    cursor.execute(
        """SELECT id FROM processes
            WHERE media_item_id = :media_id AND end_date IS NULL
              AND finished_at IS NULL AND status NOT IN ('FINISHED', 'CANCELLED')
            ORDER BY created FETCH FIRST 1 ROW ONLY""",
        {"media_id": media_id},
    )
    row = cursor.fetchone()
    return int(row[0]) if row else None


def _find_finished_process(cursor, media_id: int) -> int | None:
    cursor.execute(
        """SELECT p.id FROM processes p
            WHERE p.media_item_id = :media_id AND p.status = 'FINISHED'
              AND p.finished_at IS NOT NULL AND p.end_date IS NULL
              AND EXISTS (SELECT 1 FROM transcript_versions tv
                            WHERE tv.process_id = p.id AND tv.end_date IS NULL)
            ORDER BY p.finished_at DESC FETCH FIRST 1 ROW ONLY""",
        {"media_id": media_id},
    )
    row = cursor.fetchone()
    return int(row[0]) if row else None


def _insert_source(cursor, url: str, request: CreateJobRequest) -> int:
    source_var = cursor.var(int)
    cursor.execute(
        """INSERT INTO sources (url, source_type, title, description, published_date)
           VALUES (:url, 'ERR_URL', :title, :description, :published_date)
           RETURNING id INTO :source_id""",
        {"url": url, "title": request.title or url, "description": request.description,
         "published_date": _parse_date(request.published_date), "source_id": source_var},
    )
    return int(source_var.getvalue()[0])


def _get_or_insert_media(cursor, media) -> int:
    cursor.execute("SELECT id FROM media_items WHERE canonical_url = :url AND end_date IS NULL", {"url": media.canonical_url})
    row = cursor.fetchone()
    if row:
        return int(row[0])
    media_var = cursor.var(int)
    cursor.execute(
        """INSERT INTO media_items (provider, external_id, canonical_url, media_type, title, duration_second)
           VALUES ('ERR', :external_id, :url, :media_type, :title, :duration)
           RETURNING id INTO :media_id""",
        {"external_id": media.vod_id or media.canonical_url, "url": media.canonical_url,
         "media_type": (media.media_type or "OTHER").upper(), "title": media.title or "ERR media",
         "duration": media.duration_seconds, "media_id": media_var},
    )
    return int(media_var.getvalue()[0])


def _insert_assets(cursor, media_id: int, assets: list[dict[str, str]]) -> None:
    for asset in assets:
        asset_type, url = asset.get("asset_type"), asset.get("url")
        if not asset_type or not url:
            continue
        cursor.execute("SELECT 1 FROM media_assets WHERE media_item_id = :media_id AND url = :url AND end_date IS NULL", {"media_id": media_id, "url": url})
        if cursor.fetchone():
            continue
        cursor.execute(
            """INSERT INTO media_assets (media_item_id, asset_type, url, version)
               VALUES (:media_id, :asset_type, :url, :version)""",
            {"media_id": media_id, "asset_type": asset_type.upper(), "url": url, "version": asset.get("version")},
        )


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
