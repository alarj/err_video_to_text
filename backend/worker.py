from __future__ import annotations

import hashlib
import mimetypes
import os
import sys
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
load_dotenv(PROJECT_ROOT / ".env")

from app.database.oracle import connection  # noqa: E402
from app.services.resolver import resolve  # noqa: E402
from err2text.config import ensure_external_output, settings  # noqa: E402
from err2text.models import RunContext  # noqa: E402
from err2text.pipeline import complete_diarization, prepare_media, resume_prepared  # noqa: E402


EXECUTABLE_ACTIVITIES = ("DOWNLOADING", "DIARIZING")
TERMINAL_PROCESS_STATUSES = ("FINISHED", "CANCELLED")


def max_workers() -> int:
    return max(1, int(os.getenv("ERR2TEXT_MAX_CONCURRENT_DIARIZATIONS", "1")))


def claim_next_activity(activity_type: str) -> dict[str, object] | None:
    if activity_type not in EXECUTABLE_ACTIVITIES:
        raise ValueError(f"Unsupported activity type: {activity_type}")
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT a.id, a.process_id, a.activity_type, s.url, m.canonical_url
                 FROM activities a
                 JOIN processes p ON p.id = a.process_id
                 JOIN sources s ON s.id = p.source_id
                 JOIN media_items m ON m.id = p.media_item_id
                WHERE a.activity_type = :activity_type
                  AND a.finished_at IS NULL
                  AND a.execution_started_at IS NULL
                  AND p.finished_at IS NULL
                  AND p.status NOT IN ('FINISHED', 'CANCELLED')
                  AND a.end_date IS NULL AND p.end_date IS NULL
                  AND s.end_date IS NULL AND m.end_date IS NULL
                ORDER BY a.started_at, a.id
                FETCH FIRST 1 ROWS ONLY
                FOR UPDATE SKIP LOCKED"""
            , {"activity_type": activity_type}
        )
        row = cursor.fetchone()
        if row is None:
            conn.rollback()
            return None
        cursor.execute(
            "UPDATE activities SET execution_started_at = SYSTIMESTAMP WHERE id = :activity_id",
            {"activity_id": int(row[0])},
        )
        conn.commit()
        return {
            "activity_id": int(row[0]),
            "process_id": int(row[1]),
            "activity_type": str(row[2]),
            "source_url": str(row[3]),
            "media_url": str(row[4]),
        }


def process_one(activity: dict[str, object]) -> None:
    process_id = int(activity["process_id"])
    activity_id = int(activity["activity_id"])
    try:
        output_dir = ensure_external_output(settings().runtime_root / "outputs" / f"process-{process_id}", settings())
        context = RunContext(
            source_url=str(activity["source_url"]),
            output_dir=str(output_dir),
            work_key=f"process-{process_id}",
        )
        if activity["activity_type"] == "DOWNLOADING":
            resolved = resolve(str(activity["source_url"]))
            selected = next(
                (
                    item for item in resolved["media_items"]
                    if item.get("canonical_url") and _same_url(str(item["canonical_url"]), str(activity["media_url"]))
                ),
                None,
            )
            if selected is None and len(resolved["media_items"]) == 1:
                selected = resolved["media_items"][0]
            if selected is None:
                raise RuntimeError("Selected media is no longer present in resolver response")
            prepare_media(context, settings(), int(selected["index"]))
            transition_to_diarizing(process_id, activity_id)
            return
        if activity["activity_type"] == "DIARIZING":
            prepared = resume_prepared(context, settings())
            result_dir = complete_diarization(prepared, context, settings())
            finish_success(process_id, activity_id, result_dir)
            return
        raise RuntimeError(f"Unsupported worker activity: {activity['activity_type']}")
    except Exception as exc:
        finish_failure(process_id, activity_id, exc)


def transition_to_diarizing(process_id: int, previous_activity_id: int) -> int:
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE activities
                  SET finished_at = SYSTIMESTAMP, result = 'OK', last_updated = SYSTIMESTAMP
                WHERE id = :activity_id AND process_id = :process_id
                  AND finished_at IS NULL""",
            {"activity_id": previous_activity_id, "process_id": process_id},
        )
        activity_var = cursor.var(int)
        cursor.execute(
            """INSERT INTO activities
                   (process_id, previous_activity_id, activity_type, started_at)
                VALUES (:process_id, :previous_activity_id, 'DIARIZING', SYSTIMESTAMP)
                RETURNING id INTO :activity_id""",
            {"process_id": process_id, "previous_activity_id": previous_activity_id, "activity_id": activity_var},
        )
        activity_id = int(activity_var.getvalue()[0])
        cursor.execute(
            "UPDATE processes SET status = 'DIARIZING', last_updated = SYSTIMESTAMP WHERE id = :process_id",
            {"process_id": process_id},
        )
        conn.commit()
        return activity_id


def finish_success(process_id: int, activity_id: int, result_dir: Path) -> None:
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE activities
                  SET finished_at = SYSTIMESTAMP, result = 'OK', last_updated = SYSTIMESTAMP
                WHERE id = :activity_id AND process_id = :process_id AND finished_at IS NULL""",
            {"activity_id": activity_id, "process_id": process_id},
        )
        next_activity_var = cursor.var(int)
        cursor.execute(
            """INSERT INTO activities (process_id, previous_activity_id, activity_type, started_at)
                VALUES (:process_id, :previous_activity_id, 'WAITING_FOR_PARTICIPANTS', SYSTIMESTAMP)
                RETURNING id INTO :activity_id""",
            {"process_id": process_id, "previous_activity_id": activity_id, "activity_id": next_activity_var},
        )
        cursor.execute(
            "UPDATE processes SET status = 'WAITING_FOR_PARTICIPANTS', last_updated = SYSTIMESTAMP WHERE id = :process_id",
            {"process_id": process_id},
        )
        version_var = cursor.var(int)
        cursor.execute(
            """INSERT INTO transcript_versions
                   (process_id, activity_id, version_number, version_type, status)
                VALUES (:process_id, :activity_id, 1, 'AUTOMATIC_DRAFT', 'DRAFT')
                RETURNING id INTO :version_id""",
            {"process_id": process_id, "activity_id": activity_id, "version_id": version_var},
        )
        version_id = int(version_var.getvalue()[0])
        for path in sorted(result_dir.iterdir()):
            if not path.is_file():
                continue
            artifact_var = cursor.var(int)
            cursor.execute(
                """INSERT INTO artifacts (artifact_type, path, content_type, size_byte, sha256)
                    VALUES (:artifact_type, :path, :content_type, :size_byte, :sha256)
                    RETURNING id INTO :artifact_id""",
                {
                    "artifact_type": path.suffix.lstrip(".").upper() or "FILE",
                    "path": str(path),
                    "content_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                    "size_byte": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "artifact_id": artifact_var,
                },
            )
            artifact_id = int(artifact_var.getvalue()[0])
            cursor.execute(
                "INSERT INTO activity_artifacts (activity_id, artifact_id) VALUES (:activity_id, :artifact_id)",
                {"activity_id": activity_id, "artifact_id": artifact_id},
            )
            if path.suffix.lower() in {".vtt", ".json", ".md"}:
                cursor.execute(
                    "INSERT INTO transcript_artifacts (transcript_version_id, artifact_id) VALUES (:version_id, :artifact_id)",
                    {"version_id": version_id, "artifact_id": artifact_id},
                )
        conn.commit()


def finish_failure(process_id: int, activity_id: int, exc: Exception) -> None:
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE activities
                  SET finished_at = SYSTIMESTAMP, result = 'ERROR',
                      error_code = :error_code, error_message = :error_message,
                      last_updated = SYSTIMESTAMP
                WHERE id = :activity_id AND process_id = :process_id AND finished_at IS NULL""",
            {"activity_id": activity_id, "process_id": process_id,
             "error_code": type(exc).__name__, "error_message": str(exc)[:4000]},
        )
        cursor.execute(
            """UPDATE processes
                  SET status = 'CANCELLED', finished_at = SYSTIMESTAMP, last_updated = SYSTIMESTAMP
                WHERE id = :process_id AND finished_at IS NULL""",
            {"process_id": process_id},
        )
        conn.commit()


def reconcile_waiting_processes() -> None:
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT child.id, child.parent_process_id, parent.status
                 FROM processes child
                 JOIN processes parent ON parent.id = child.parent_process_id
                WHERE child.status = 'WAITING_FOR_RESULT'
                  AND child.finished_at IS NULL
                  AND parent.finished_at IS NOT NULL
                  AND parent.status IN ('FINISHED', 'CANCELLED')
                  AND child.end_date IS NULL AND parent.end_date IS NULL
                FOR UPDATE OF child.id SKIP LOCKED"""
        )
        rows = cursor.fetchall()
        for child_id, _, parent_status in rows:
            result = "OK" if parent_status == "FINISHED" else "CANCELLED"
            cursor.execute(
                """UPDATE activities
                      SET finished_at = SYSTIMESTAMP, result = :result, last_updated = SYSTIMESTAMP
                    WHERE process_id = :process_id AND activity_type = 'WAITING_FOR_RESULT'
                      AND finished_at IS NULL""",
                {"process_id": int(child_id), "result": result},
            )
            cursor.execute(
                """UPDATE processes
                      SET status = :status, finished_at = SYSTIMESTAMP, last_updated = SYSTIMESTAMP
                    WHERE id = :process_id AND finished_at IS NULL""",
                {"process_id": int(child_id), "status": parent_status},
            )
        conn.commit()


def _same_url(left: str, right: str) -> bool:
    return left.rstrip("/") == right.rstrip("/")


def run_loop() -> None:
    diarization_workers = max_workers()
    download_futures: set[Future[None]] = set()
    diarization_futures: set[Future[None]] = set()
    with (ThreadPoolExecutor(thread_name_prefix="err2text-download") as download_executor,
          ThreadPoolExecutor(max_workers=diarization_workers, thread_name_prefix="err2text-diarization") as diarization_executor):
        while True:
            reconcile_waiting_processes()
            while True:
                activity = claim_next_activity("DOWNLOADING")
                if activity is None:
                    break
                download_futures.add(download_executor.submit(process_one, activity))
            while len(diarization_futures) < diarization_workers:
                activity = claim_next_activity("DIARIZING")
                if activity is None:
                    break
                diarization_futures.add(diarization_executor.submit(process_one, activity))
            done_downloads = {future for future in download_futures if future.done()}
            done_diarizations = {future for future in diarization_futures if future.done()}
            for future in done_downloads | done_diarizations:
                future.result()
            download_futures -= done_downloads
            diarization_futures -= done_diarizations
            if not download_futures and not diarization_futures:
                time.sleep(5)
            else:
                time.sleep(1)


if __name__ == "__main__":
    if "--once" in sys.argv:
        activity = claim_next_activity("DOWNLOADING") or claim_next_activity("DIARIZING")
        if activity is not None:
            process_one(activity)
        reconcile_waiting_processes()
    else:
        run_loop()
