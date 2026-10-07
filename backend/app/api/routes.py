from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.database.oracle import connection
from app.schemas import CreateJobRequest, JobResponse, ResolveRequest
from app.services.resolver import resolve
from err2text.errors import PipelineError

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
