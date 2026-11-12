from __future__ import annotations

import logging
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from app.database.oracle import connection
from app.services.materializer import materialize, prepare
from app.services.ords import DIARIZATION_JOB_TYPE, OrdsClient, OrdsError, OrdsSettings
from app.services.resolver import resolve
from err2text.config import ensure_external_output, settings
from err2text.errors import PipelineError
from err2text.models import RunContext
from err2text.pipeline import complete_diarization, prepare_media


LOGGER = logging.getLogger("err2text.worker")


class OracleOperationRepository:
    def operation_context(self, operation_id: int) -> dict[str, Any]:
        with connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT bo.operation_id, bo.operation_type, bo.ords_job_id,
                          bo.local_started_at, bo.local_outcome,
                          p.id, p.status, s.url, m.canonical_url,
                          a.id, a.activity_type
                     FROM background_operations bo
                     JOIN processes p ON p.id = bo.process_id
                     JOIN sources s ON s.id = p.source_id
                     JOIN media_items m ON m.id = p.media_item_id
                     JOIN activities a ON a.id = (
                         SELECT MAX(a2.id)
                           FROM activities a2
                          WHERE a2.process_id = p.id AND a2.end_date IS NULL
                     )
                    WHERE bo.operation_id = :operation_id
                      AND bo.end_date IS NULL AND p.end_date IS NULL
                      AND s.end_date IS NULL AND m.end_date IS NULL
                    ORDER BY a.id DESC FETCH FIRST 1 ROW ONLY""",
                {"operation_id": operation_id},
            )
            row = cursor.fetchone()
        if row is None:
            raise KeyError(operation_id)
        return {
            "operation_id": int(row[0]),
            "operation_type": str(row[1]),
            "ords_job_id": int(row[2]) if row[2] is not None else None,
            "local_started_at": row[3],
            "local_outcome": str(row[4]) if row[4] is not None else None,
            "process_id": int(row[5]),
            "process_status": str(row[6]),
            "source_url": str(row[7]),
            "media_url": str(row[8]),
            "activity_id": int(row[9]),
            "activity_type": str(row[10]),
        }

    def bind_ords_job(self, operation_id: int, ords_job_id: int) -> None:
        with connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE background_operations
                      SET ords_job_id = :ords_job_id,
                          ords_registered_at = COALESCE(ords_registered_at, SYSTIMESTAMP),
                          registration_error_code = NULL,
                          registration_error_message = NULL,
                          last_updated = SYSTIMESTAMP
                    WHERE operation_id = :operation_id AND end_date IS NULL
                      AND (ords_job_id IS NULL OR ords_job_id = :ords_job_id)""",
                {"operation_id": operation_id, "ords_job_id": ords_job_id},
            )
            if cursor.rowcount != 1:
                conn.rollback()
                raise ValueError("ORDS job ID does not match the local operation")
            conn.commit()

    def mark_started(self, operation_id: int, activity_id: int) -> None:
        with connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE background_operations
                      SET local_started_at = COALESCE(local_started_at, SYSTIMESTAMP),
                          last_updated = SYSTIMESTAMP
                    WHERE operation_id = :operation_id AND end_date IS NULL
                      AND local_completed_at IS NULL""",
                {"operation_id": operation_id},
            )
            cursor.execute(
                """UPDATE activities
                      SET execution_started_at = COALESCE(execution_started_at, SYSTIMESTAMP),
                          last_updated = SYSTIMESTAMP
                    WHERE id = :activity_id AND finished_at IS NULL AND end_date IS NULL""",
                {"activity_id": activity_id},
            )
            conn.commit()

    def mark_completed(
        self,
        operation_id: int,
        outcome: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        with connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE background_operations
                      SET local_completed_at = SYSTIMESTAMP,
                          local_outcome = :outcome,
                          local_error_code = :error_code,
                          local_error_message = :error_message,
                          last_updated = SYSTIMESTAMP
                    WHERE operation_id = :operation_id AND end_date IS NULL
                      AND local_completed_at IS NULL""",
                {
                    "operation_id": operation_id,
                    "outcome": outcome,
                    "error_code": error_code,
                    "error_message": error_message,
                },
            )
            conn.commit()


class Worker:
    def __init__(
        self,
        repository: Any,
        ords: OrdsClient,
        *,
        sleeper: Callable[[float], None] = time.sleep,
        pipeline_runner: Callable[[dict[str, Any]], None] | None = None,
        boot_id: str | None = None,
    ) -> None:
        self.repository = repository
        self.ords = ords
        self.sleeper = sleeper
        self.pipeline_runner = pipeline_runner or run_diarization_operation
        self.identity = {
            "worker_instance_id": f"err-video-to-text-{uuid.uuid4()}",
            "host_id": ords.settings.host_id,
            "boot_id": boot_id
            or Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip(),
        }

    def run_forever(self) -> None:
        startup = self.ords.worker_startup(self.identity)
        active = startup.get("active_job")
        if isinstance(active, dict):
            self.execute(active, recovered=True)
        while True:
            try:
                job = self.ords.claim(self.identity, str(uuid.uuid4()))
                if job is not None:
                    self.execute(job)
                    continue
            except OrdsError:
                LOGGER.exception("ORDS claim failed")
            self.sleeper(self.ords.settings.claim_interval_seconds)

    def run_once(self) -> None:
        startup = self.ords.worker_startup(self.identity)
        active = startup.get("active_job")
        if isinstance(active, dict):
            self.execute(active, recovered=True)
            return
        job = self.ords.claim(self.identity, str(uuid.uuid4()))
        if job is not None:
            self.execute(job)

    def execute(self, job: dict[str, Any], *, recovered: bool = False) -> None:
        operation_id = _integer(job.get("application_job_id"))
        if operation_id is None:
            self._complete_invalid_job(job, "INVALID_PARAMETERS")
            return
        try:
            context = self.repository.operation_context(operation_id)
        except KeyError:
            self.ords.complete(
                job,
                self.identity,
                outcome="INTERRUPTED",
                exit_code=0,
                end_reason="APPLICATION_OPERATION_NOT_FOUND",
            )
            return

        parameters = job.get("parameters")
        if not isinstance(parameters, dict) or _integer(parameters.get("process_id")) != context["process_id"]:
            self._fail_validation(job, context, "INVALID_PARAMETERS", "process_id does not match")
            return
        if job.get("job_type_code") != context["operation_type"] or context["operation_type"] != DIARIZATION_JOB_TYPE:
            self._fail_validation(job, context, "INVALID_JOB_TYPE", "job_type_code does not match")
            return
        try:
            self.repository.bind_ords_job(operation_id, int(job["job_id"]))
        except (KeyError, TypeError, ValueError) as exc:
            self._fail_validation(job, context, "ORDS_JOB_MISMATCH", str(exc))
            return

        local_outcome = context.get("local_outcome")
        if recovered and local_outcome in {"SUCCEEDED", "FAILED", "INTERRUPTED"}:
            outcome = str(local_outcome)
            self.ords.complete(
                job,
                self.identity,
                outcome=outcome,
                exit_code=0 if outcome == "SUCCEEDED" else 1,
                end_reason="COMPLETED" if outcome == "SUCCEEDED" else "LOCAL_OPERATION_COMPLETED",
            )
            return
        if recovered and context.get("local_started_at") is not None:
            message = "Worker restarted after local diarization had started"
            finish_failure(context["process_id"], context["activity_id"], RuntimeError(message))
            self.repository.mark_completed(operation_id, "INTERRUPTED", "WORKER_RESTART", message)
            self.ords.complete(
                job,
                self.identity,
                outcome="INTERRUPTED",
                exit_code=1,
                end_reason="WORKER_RESTART",
            )
            return

        self.repository.mark_started(operation_id, context["activity_id"])
        try:
            self.ords.start(job, self.identity)
        except OrdsError:
            LOGGER.exception("ORDS start acknowledgement failed; local processing continues")

        stop = threading.Event()
        heartbeat = threading.Thread(
            target=self._heartbeat_loop,
            args=(job, stop),
            name="err2text-ords-heartbeat",
            daemon=True,
        )
        heartbeat.start()
        try:
            self.pipeline_runner(context)
        except Exception as exc:
            LOGGER.exception("Diarization operation failed operation_id=%d", operation_id)
            finish_failure(context["process_id"], _active_activity_id(context["process_id"]), exc)
            code = _error_code(exc)
            message = str(exc)[:2000] or code
            self.repository.mark_completed(operation_id, "FAILED", code, message)
            self.ords.complete(
                job,
                self.identity,
                outcome="FAILED",
                exit_code=1,
                end_reason=code,
            )
        else:
            self.repository.mark_completed(operation_id, "SUCCEEDED")
            self.ords.complete(
                job,
                self.identity,
                outcome="SUCCEEDED",
                exit_code=0,
                end_reason="COMPLETED",
            )
        finally:
            stop.set()
            heartbeat.join(timeout=1)

    def _complete_invalid_job(self, job: dict[str, Any], code: str) -> None:
        self.ords.complete(job, self.identity, outcome="FAILED", exit_code=2, end_reason=code)

    def _fail_validation(
        self, job: dict[str, Any], context: dict[str, Any], code: str, message: str
    ) -> None:
        finish_failure(context["process_id"], context["activity_id"], ValueError(message))
        self.repository.mark_completed(context["operation_id"], "FAILED", code, message[:2000])
        self.ords.complete(job, self.identity, outcome="FAILED", exit_code=2, end_reason=code)

    def _heartbeat_loop(self, job: dict[str, Any], stop: threading.Event) -> None:
        while not stop.wait(self.ords.settings.heartbeat_interval_seconds):
            try:
                self.ords.heartbeat(job, self.identity)
            except OrdsError:
                LOGGER.exception("ORDS heartbeat failed; local processing continues")


def run_diarization_operation(activity: dict[str, Any]) -> None:
    process_id = int(activity["process_id"])
    activity_id = int(activity["activity_id"])
    if activity["activity_type"] not in {"DOWNLOADING", "DIARIZING"}:
        raise RuntimeError(f"Expected DOWNLOADING or DIARIZING activity, got {activity['activity_type']}")
    config = settings()
    output_dir = ensure_external_output(
        config.runtime_root / "outputs" / f"process-{process_id}", config
    )
    context = RunContext(
        source_url=str(activity["source_url"]),
        output_dir=str(output_dir),
        work_key=f"process-{process_id}",
    )
    resolved = resolve(str(activity["source_url"]))
    selected = next(
        (
            item
            for item in resolved["media_items"]
            if item.get("canonical_url")
            and _same_url(str(item["canonical_url"]), str(activity["media_url"]))
        ),
        None,
    )
    if selected is None and len(resolved["media_items"]) == 1:
        selected = resolved["media_items"][0]
    if selected is None:
        raise RuntimeError("Selected media is no longer present in resolver response")

    prepared = prepare_media(context, config, int(selected["index"]))
    if activity["activity_type"] == "DOWNLOADING":
        activity_id = transition_to_diarizing(process_id, activity_id)
    result_dir = complete_diarization(prepared, context, config)
    materializing_id = transition_to_materializing(process_id, activity_id)
    materialize_automatic_draft(process_id, materializing_id, result_dir)


def transition_to_diarizing(process_id: int, previous_activity_id: int) -> int:
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE activities
                  SET finished_at = SYSTIMESTAMP, result = 'OK', last_updated = SYSTIMESTAMP
                WHERE id = :activity_id AND process_id = :process_id AND finished_at IS NULL""",
            {"activity_id": previous_activity_id, "process_id": process_id},
        )
        activity_var = cursor.var(int)
        cursor.execute(
            """INSERT INTO activities
                   (process_id, previous_activity_id, activity_type, started_at, execution_started_at)
                VALUES (:process_id, :previous_activity_id, 'DIARIZING', SYSTIMESTAMP, SYSTIMESTAMP)
                RETURNING id INTO :activity_id""",
            {
                "process_id": process_id,
                "previous_activity_id": previous_activity_id,
                "activity_id": activity_var,
            },
        )
        activity_id = int(activity_var.getvalue()[0])
        cursor.execute(
            """UPDATE processes SET status = 'DIARIZING', last_updated = SYSTIMESTAMP
                WHERE id = :process_id""",
            {"process_id": process_id},
        )
        conn.commit()
        return activity_id


def transition_to_materializing(process_id: int, previous_activity_id: int) -> int:
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE activities
                  SET finished_at = SYSTIMESTAMP, result = 'OK', last_updated = SYSTIMESTAMP
                WHERE id = :activity_id AND process_id = :process_id AND finished_at IS NULL""",
            {"activity_id": previous_activity_id, "process_id": process_id},
        )
        activity_var = cursor.var(int)
        cursor.execute(
            """INSERT INTO activities
                   (process_id, previous_activity_id, activity_type, started_at, execution_started_at)
                VALUES (:process_id, :previous_activity_id,
                        'MATERIALIZING_AUTOMATIC_DRAFT', SYSTIMESTAMP, SYSTIMESTAMP)
                RETURNING id INTO :activity_id""",
            {
                "process_id": process_id,
                "previous_activity_id": previous_activity_id,
                "activity_id": activity_var,
            },
        )
        activity_id = int(activity_var.getvalue()[0])
        cursor.execute(
            """UPDATE processes SET status = 'MATERIALIZING_AUTOMATIC_DRAFT',
                      last_updated = SYSTIMESTAMP WHERE id = :process_id""",
            {"process_id": process_id},
        )
        conn.commit()
        return activity_id


def materialize_automatic_draft(process_id: int, activity_id: int, result_dir: Path) -> None:
    prepared = prepare(result_dir)
    with connection() as conn:
        cursor = conn.cursor()
        materialize(cursor, process_id, activity_id, prepared)
        cursor.execute(
            """UPDATE activities SET finished_at = SYSTIMESTAMP, result = 'OK',
                      last_updated = SYSTIMESTAMP
                WHERE id = :activity_id AND process_id = :process_id AND finished_at IS NULL""",
            {"activity_id": activity_id, "process_id": process_id},
        )
        next_activity_var = cursor.var(int)
        cursor.execute(
            """INSERT INTO activities
                   (process_id, previous_activity_id, activity_type, started_at)
                VALUES (:process_id, :previous_activity_id, 'WAITING_FOR_PARTICIPANTS', SYSTIMESTAMP)
                RETURNING id INTO :activity_id""",
            {
                "process_id": process_id,
                "previous_activity_id": activity_id,
                "activity_id": next_activity_var,
            },
        )
        cursor.execute(
            """UPDATE processes SET status = 'WAITING_FOR_PARTICIPANTS',
                      last_updated = SYSTIMESTAMP WHERE id = :process_id""",
            {"process_id": process_id},
        )
        conn.commit()


def finish_failure(process_id: int, activity_id: int, exc: Exception) -> None:
    error_code = _error_code(exc)
    error_message = str(exc)[:4000] or error_code
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE activities SET finished_at = SYSTIMESTAMP, result = 'ERROR',
                      error_code = :error_code, error_message = :error_message,
                      last_updated = SYSTIMESTAMP
                WHERE id = :activity_id AND process_id = :process_id AND finished_at IS NULL""",
            {
                "activity_id": activity_id,
                "process_id": process_id,
                "error_code": error_code,
                "error_message": error_message,
            },
        )
        cursor.execute(
            """UPDATE processes SET status = 'CANCELLED', finished_at = SYSTIMESTAMP,
                      last_updated = SYSTIMESTAMP
                WHERE id = :process_id AND finished_at IS NULL""",
            {"process_id": process_id},
        )
        _finish_waiting_children(cursor, process_id)
        conn.commit()


def _finish_waiting_children(cursor: Any, parent_process_id: int) -> None:
    cursor.execute(
        """UPDATE activities SET finished_at = SYSTIMESTAMP, result = 'CANCELLED',
                  last_updated = SYSTIMESTAMP
            WHERE activity_type = 'WAITING_FOR_RESULT' AND finished_at IS NULL
              AND process_id IN (
                  SELECT id FROM processes WHERE parent_process_id = :parent_process_id
                    AND finished_at IS NULL AND end_date IS NULL
              )""",
        {"parent_process_id": parent_process_id},
    )
    cursor.execute(
        """UPDATE processes SET status = 'CANCELLED', finished_at = SYSTIMESTAMP,
                  last_updated = SYSTIMESTAMP
            WHERE parent_process_id = :parent_process_id AND status = 'WAITING_FOR_RESULT'
              AND finished_at IS NULL AND end_date IS NULL""",
        {"parent_process_id": parent_process_id},
    )


def _active_activity_id(process_id: int) -> int:
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id FROM activities WHERE process_id = :process_id
                 AND finished_at IS NULL AND end_date IS NULL
               ORDER BY id DESC FETCH FIRST 1 ROW ONLY""",
            {"process_id": process_id},
        )
        row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Process {process_id} has no active activity")
    return int(row[0])


def _same_url(left: str, right: str) -> bool:
    return left.rstrip("/") == right.rstrip("/")


def _integer(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _error_code(exc: Exception) -> str:
    return exc.code.name if isinstance(exc, PipelineError) else type(exc).__name__


def main() -> int:
    logging.basicConfig(level="INFO")
    worker = Worker(OracleOperationRepository(), OrdsClient(OrdsSettings.from_env()))
    if "--once" in sys.argv:
        worker.run_once()
    else:
        worker.run_forever()
    return 0
