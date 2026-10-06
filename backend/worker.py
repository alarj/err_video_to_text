from __future__ import annotations

import hashlib
import mimetypes
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
load_dotenv(PROJECT_ROOT / ".env")

from app.database.oracle import connection  # noqa: E402
from app.services.resolver import resolve  # noqa: E402
from err2text.config import ensure_external_output, settings  # noqa: E402
from err2text.models import RunContext  # noqa: E402
from err2text.pipeline import process  # noqa: E402


def claim_next_job() -> dict[str, object] | None:
    with connection() as conn:
        cursor = conn.cursor()
        queued_id = _status_id(cursor, "QUEUED")
        downloading_id = _status_id(cursor, "DOWNLOADING")
        cursor.execute("""SELECT id, submitted_url, media_item_id
                          FROM jobs
                          WHERE job_status_id = :queued_id AND end_date IS NULL
                          ORDER BY created, id
                          FETCH FIRST 1 ROWS ONLY
                          FOR UPDATE SKIP LOCKED""", {"queued_id": queued_id})
        row = cursor.fetchone()
        if row is None:
            conn.rollback()
            return None
        cursor.execute("UPDATE jobs SET job_status_id = :status_id WHERE id = :job_id",
                       {"status_id": downloading_id, "job_id": int(row[0])})
        _event(cursor, int(row[0]), downloading_id, "WORK_STARTED", "Worker võttis töö järjekorrast.")
        conn.commit()
        return {"id": int(row[0]), "source_url": str(row[1]), "media_item_id": int(row[2])}


def process_one() -> bool:
    job = claim_next_job()
    if job is None:
        return False
    job_id = int(job["id"])
    run_id = None
    try:
        with connection() as conn:
            cursor = conn.cursor()
            started_id = _status_id(cursor, "DIARIZING")
            run_var = cursor.var(int)
            cursor.execute("""INSERT INTO runs
                (origin_job_id, media_item_id, status, attempt_number, input_fingerprint, started_at)
                VALUES (:job_id, :media_id, 'STARTED',
                        (SELECT COUNT(*) + 1 FROM runs WHERE origin_job_id = :job_id),
                        :fingerprint, SYSTIMESTAMP)
                RETURNING id INTO :run_id""",
                {"job_id": job_id, "media_id": int(job["media_item_id"]),
                 "fingerprint": hashlib.sha256(str(job["source_url"]).encode()).hexdigest(),
                 "run_id": run_var})
            run_id = int(run_var.getvalue()[0])
            cursor.execute("UPDATE jobs SET job_status_id = :status_id WHERE id = :job_id",
                           {"status_id": started_id, "job_id": job_id})
            cursor.execute("INSERT INTO job_runs (job_id, run_id, relation_type) VALUES (:job_id, :run_id, 'CREATED')",
                           {"job_id": job_id, "run_id": run_id})
            _event(cursor, job_id, started_id, "RUN_STARTED", "Töötlemiskatse algas.")
            conn.commit()

        resolved = resolve(str(job["source_url"]))
        selected = next((item for item in resolved["media_items"]
                         if item.get("canonical_url") and _same_url(item["canonical_url"], _media_url(job_id))), None)
        # If the resolver returns only one item, it is unambiguously selected.
        if selected is None and len(resolved["media_items"]) == 1:
            selected = resolved["media_items"][0]
        if selected is None:
            raise RuntimeError("Selected media is no longer present in resolver response")
        output_dir = ensure_external_output(settings().runtime_root / "outputs" / f"job-{job_id}", settings())
        result_dir = process(RunContext(source_url=str(job["source_url"]), output_dir=str(output_dir)), settings(), int(selected["index"]))
        _finish_success(job_id, int(run_id), result_dir)
    except Exception as exc:
        _finish_failure(job_id, run_id, exc)
    return True


def _media_url(job_id: int) -> str:
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT m.canonical_url FROM jobs j JOIN media_items m ON m.id = j.media_item_id WHERE j.id = :id", {"id": job_id})
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("Job media was not found")
        return str(row[0])


def _finish_success(job_id: int, run_id: int, result_dir: Path) -> None:
    with connection() as conn:
        cursor = conn.cursor()
        succeeded_id = _status_id(cursor, "SUCCEEDED")
        cursor.execute("UPDATE runs SET status = 'SUCCEEDED', finished_at = SYSTIMESTAMP WHERE id = :id", {"id": run_id})
        cursor.execute("UPDATE jobs SET job_status_id = :status_id, resolved_at = SYSTIMESTAMP WHERE id = :job_id",
                       {"status_id": succeeded_id, "job_id": job_id})
        _event(cursor, job_id, succeeded_id, "RUN_FINISHED", "Töötlus valmis.")
        version_var = cursor.var(int)
        cursor.execute("""INSERT INTO transcript_versions
            (run_id, version_number, version_type, status)
            VALUES (:run_id, 1, 'AUTOMATIC_DRAFT', 'DRAFT')
            RETURNING id INTO :version_id""", {"run_id": run_id, "version_id": version_var})
        version_id = int(version_var.getvalue()[0])
        for path in sorted(result_dir.iterdir()):
            if not path.is_file():
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            artifact_var = cursor.var(int)
            cursor.execute("""INSERT INTO artifacts
                (artifact_type, path, content_type, size_byte, sha256)
                VALUES (:type, :path, :content_type, :size_byte, :sha256)
                RETURNING id INTO :artifact_id""",
                {"type": path.suffix.lstrip(".").upper() or "FILE", "path": str(path),
                 "content_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                 "size_byte": path.stat().st_size, "sha256": digest, "artifact_id": artifact_var})
            artifact_id = int(artifact_var.getvalue()[0])
            cursor.execute("INSERT INTO run_artifacts (run_id, artifact_id) VALUES (:run_id, :artifact_id)",
                           {"run_id": run_id, "artifact_id": artifact_id})
            if path.suffix.lower() in {".vtt", ".json", ".md"}:
                cursor.execute("""INSERT INTO transcript_artifacts
                    (transcript_version_id, artifact_id)
                    VALUES (:version_id, :artifact_id)""",
                               {"version_id": version_id, "artifact_id": artifact_id})
        conn.commit()


def _finish_failure(job_id: int, run_id: int | None, exc: Exception) -> None:
    with connection() as conn:
        cursor = conn.cursor()
        failed_id = _status_id(cursor, "FAILED")
        if run_id is not None:
            cursor.execute("UPDATE runs SET status = 'FAILED', finished_at = SYSTIMESTAMP WHERE id = :id", {"id": run_id})
        cursor.execute("UPDATE jobs SET job_status_id = :status_id, error_code = :code, error_message = :message WHERE id = :job_id",
                       {"status_id": failed_id, "code": type(exc).__name__, "message": str(exc)[:2000], "job_id": job_id})
        _event(cursor, job_id, failed_id, "RUN_FAILED", f"{type(exc).__name__}: {exc}"[:4000])
        conn.commit()


def _status_id(cursor, code: str) -> int:
    cursor.execute("SELECT id FROM job_statuses WHERE code = :code AND end_date IS NULL", {"code": code})
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Missing job status: {code}")
    return int(row[0])


def _event(cursor, job_id: int, status_id: int, event_type: str, detail: str) -> None:
    cursor.execute("INSERT INTO job_events (job_id, job_status_id, event_type, detail) VALUES (:job_id, :status_id, :event_type, :detail)",
                   {"job_id": job_id, "status_id": status_id, "event_type": event_type, "detail": detail})


def _same_url(left: str, right: str) -> bool:
    return left.rstrip("/") == right.rstrip("/")


if __name__ == "__main__":
    if "--once" in sys.argv:
        process_one()
    else:
        while True:
            if not process_one():
                time.sleep(5)
