from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.database.oracle import connection
from app.schemas import CreateJobRequest, JobResponse, ResolveRequest
from app.services.resolver import resolve

router = APIRouter()


def _utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _status_id(cursor, code: str) -> int:
    cursor.execute("SELECT id FROM job_statuses WHERE code = :code AND end_date IS NULL", {"code": code})
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Job status is not configured: {code}")
    return int(row[0])


@router.post("/resolve")
def resolve_url(request: ResolveRequest) -> dict[str, object]:
    try:
        return resolve(str(request.url))
    except Exception as exc:
        raise HTTPException(status_code=422, detail={"error": type(exc).__name__, "message": str(exc)}) from exc


@router.post("/jobs", response_model=JobResponse, status_code=201)
def create_job(request: CreateJobRequest) -> JobResponse:
    if not request.confirm:
        raise HTTPException(status_code=400, detail="confirm must be true")
    media = request.selected_media
    source_url = str(request.source_url)
    with connection() as conn:
        cursor = conn.cursor()
        try:
            source_id = _insert_source(cursor, source_url, request)
            media_id = _get_or_insert_media(cursor, media)
            _insert_assets(cursor, media_id, [*media.assets, *request.assets])
            queued_id = _status_id(cursor, "QUEUED")
            succeeded_id = _status_id(cursor, "SUCCEEDED")
            job_var = cursor.var(int)
            cursor.execute(
                """INSERT INTO jobs (source_id, media_item_id, submitted_url, job_status_id)
                   VALUES (:source_id, :media_id, :url, :status_id)
                   RETURNING id INTO :job_id""",
                {"source_id": source_id, "media_id": media_id, "url": source_url,
                 "status_id": queued_id, "job_id": job_var},
            )
            job_id = int(job_var.getvalue()[0])
            cursor.execute(
                """SELECT r.id FROM runs r
                   JOIN job_runs jr ON jr.run_id = r.id
                   WHERE r.media_item_id = :media_id AND r.status = 'SUCCEEDED'
                     AND jr.relation_type IN ('CREATED', 'REUSED')
                     AND r.end_date IS NULL
                   ORDER BY r.finished_at DESC FETCH FIRST 1 ROW ONLY""",
                {"media_id": media_id},
            )
            existing = cursor.fetchone()
            if existing:
                cursor.execute("UPDATE jobs SET job_status_id = :status_id WHERE id = :job_id",
                               {"status_id": succeeded_id, "job_id": job_id})
                cursor.execute("INSERT INTO job_runs (job_id, run_id, relation_type) VALUES (:job_id, :run_id, 'REUSED')",
                               {"job_id": job_id, "run_id": int(existing[0])})
                conn.commit()
                return JobResponse(id=job_id, status="SUCCEEDED", reused=True)
            conn.commit()
            return JobResponse(id=job_id, status="QUEUED")
        except Exception:
            conn.rollback()
            raise


@router.get("/jobs")
def list_jobs(limit: int = Query(default=100, ge=1, le=200)) -> list[dict[str, object]]:
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT id, submitted_url, title, status, submitted_at, resolved_at,
                                 error_code, error_message
                          FROM (
                              SELECT j.id, j.submitted_url,
                                     NVL(s.title, m.title) AS title,
                                     st.code AS status, j.submitted_at, j.resolved_at,
                                     j.error_code, j.error_message
                              FROM jobs j
                              JOIN sources s ON s.id = j.source_id
                              JOIN media_items m ON m.id = j.media_item_id
                              JOIN job_statuses st ON st.id = j.job_status_id
                              WHERE j.end_date IS NULL
                                AND s.end_date IS NULL
                                AND m.end_date IS NULL
                                AND st.end_date IS NULL
                              ORDER BY j.created DESC, j.id DESC
                          )
                          WHERE ROWNUM <= :limit""", {"limit": limit})
        return [{"id": row[0], "submitted_url": row[1], "title": row[2], "status": row[3],
                 "submitted_at": _utc_iso(row[4]), "resolved_at": _utc_iso(row[5]),
                 "error_code": row[6], "error_message": row[7]}
                for row in cursor.fetchall()]


@router.get("/jobs/{job_id}")
def get_job(job_id: int) -> dict[str, object]:
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT j.id, s.code, j.submitted_url, j.error_code, j.error_message,
                                 j.submitted_at, j.resolved_at
                          FROM jobs j JOIN job_statuses s ON s.id = j.job_status_id
                          WHERE j.id = :job_id AND j.end_date IS NULL""", {"job_id": job_id})
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"id": row[0], "status": row[1], "submitted_url": row[2], "error_code": row[3],
                "error_message": row[4], "submitted_at": _utc_iso(row[5]), "resolved_at": _utc_iso(row[6])}


@router.get("/jobs/{job_id}/events")
def get_job_events(job_id: int) -> list[dict[str, object]]:
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT e.id, s.code, e.event_type, e.detail, e.event_at
                          FROM job_events e JOIN job_statuses s ON s.id = e.job_status_id
                          WHERE e.job_id = :job_id AND e.end_date IS NULL
                          ORDER BY e.event_at, e.id""", {"job_id": job_id})
        return [{"id": r[0], "status": r[1], "event_type": r[2], "detail": r[3], "event_at": _utc_iso(r[4])}
                for r in cursor.fetchall()]


@router.get("/jobs/{job_id}/artifacts")
def get_job_artifacts(job_id: int) -> list[dict[str, object]]:
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT a.id, a.artifact_type, a.path, a.content_type, a.size_byte, a.sha256
                          FROM artifacts a
                          JOIN run_artifacts ra ON ra.artifact_id = a.id
                          JOIN job_runs jr ON jr.run_id = ra.run_id
                          WHERE jr.job_id = :job_id AND a.end_date IS NULL
                          ORDER BY a.id""", {"job_id": job_id})
        return [{"id": r[0], "artifact_type": r[1], "path": r[2], "content_type": r[3],
                 "size_byte": r[4], "sha256": r[5]} for r in cursor.fetchall()]


@router.get("/jobs/{job_id}/artifacts/{artifact_id}")
def download_job_artifact(job_id: int, artifact_id: int):
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT a.path, a.content_type
                          FROM artifacts a
                          JOIN run_artifacts ra ON ra.artifact_id = a.id
                          JOIN job_runs jr ON jr.run_id = ra.run_id
                          WHERE jr.job_id = :job_id AND a.id = :artifact_id
                            AND a.end_date IS NULL""",
                       {"job_id": job_id, "artifact_id": artifact_id})
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Artifact not found")
        path = Path(str(row[0])).resolve()
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Artifact file is not available")
        filename = path.name.replace('"', "'").replace("\r", "").replace("\n", "")
        headers = {"Content-Disposition": f'inline; filename="{filename}"'}
        return FileResponse(path, media_type=str(row[1]), headers=headers)


def _insert_source(cursor, url: str, request: CreateJobRequest) -> int:
    source_var = cursor.var(int)
    binds = {"url": url, "title": request.title or url, "description": request.description,
             "published_date": _parse_date(request.published_date), "source_id": source_var}
    cursor.execute("""INSERT INTO sources (url, source_type, title, description, published_date)
                      VALUES (:url, 'ERR_URL', :title, :description, :published_date)
                      RETURNING id INTO :source_id""",
                   binds)
    return int(source_var.getvalue()[0])


def _get_or_insert_media(cursor, media) -> int:
    cursor.execute("SELECT id FROM media_items WHERE canonical_url = :url AND end_date IS NULL",
                   {"url": media.canonical_url or ""})
    row = cursor.fetchone()
    if row:
        return int(row[0])
    media_var = cursor.var(int)
    cursor.execute("""INSERT INTO media_items
                      (provider, external_id, canonical_url, media_type, title, duration_second)
                      VALUES (:provider, :external_id, :url, :media_type, :title, :duration)
                      RETURNING id INTO :media_id""",
                   {"provider": "ERR", "external_id": media.vod_id or media.canonical_url or "unknown",
                    "url": media.canonical_url or "", "media_type": (media.media_type or "OTHER").upper(),
                    "title": media.title or "ERR media", "duration": media.duration_seconds,
                    "media_id": media_var})
    return int(media_var.getvalue()[0])


def _insert_assets(cursor, media_id: int, assets: list[dict[str, str]]) -> None:
    for asset in assets:
        if not asset.get("asset_type") or not asset.get("url"):
            continue
        cursor.execute("SELECT 1 FROM media_assets WHERE media_item_id = :media_id AND url = :url AND end_date IS NULL",
                       {"media_id": media_id, "url": asset["url"]})
        if cursor.fetchone():
            continue
        cursor.execute("""INSERT INTO media_assets (media_item_id, asset_type, url, version)
                          VALUES (:media_id, :asset_type, :url, :version)""",
                       {"media_id": media_id, "asset_type": asset["asset_type"].upper(),
                        "url": asset["url"], "version": asset.get("version")})


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
