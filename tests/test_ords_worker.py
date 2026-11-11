from __future__ import annotations

from app.services.ords import OrdsSettings
from ords_worker import Worker


class FakeRepository:
    def __init__(self) -> None:
        self.context = {
            "operation_id": 45,
            "operation_type": "diarization",
            "ords_job_id": None,
            "local_started_at": None,
            "local_outcome": None,
            "process_id": 12,
            "process_status": "DIARIZING",
            "source_url": "https://www.err.ee/example",
            "media_url": "https://vod.err.ee/example/master.m3u8",
            "activity_id": 99,
            "activity_type": "DIARIZING",
        }
        self.missing = False
        self.bound = []
        self.started = []
        self.completed = []

    def operation_context(self, operation_id):
        if self.missing:
            raise KeyError(operation_id)
        return dict(self.context)

    def bind_ords_job(self, operation_id, ords_job_id):
        self.bound.append((operation_id, ords_job_id))

    def mark_started(self, operation_id, activity_id):
        self.started.append((operation_id, activity_id))

    def mark_completed(self, *values):
        self.completed.append(values)


class FakeOrds:
    def __init__(self) -> None:
        self.settings = OrdsSettings(
            "https://ords.example/jobs",
            "client",
            "secret",
            heartbeat_interval_seconds=300,
            host_id="host",
        )
        self.started = []
        self.completed = []
        self.heartbeats = []

    def start(self, job, identity):
        self.started.append(job["job_id"])

    def heartbeat(self, job, identity):
        self.heartbeats.append(job["job_id"])

    def complete(self, job, identity, **values):
        self.completed.append((job["job_id"], values))


def job() -> dict[str, object]:
    return {
        "job_id": 321,
        "application_job_id": "45",
        "job_type_code": "diarization",
        "parameters": {"process_id": 12},
        "execution_token": "token",
        "status": "CLAIMED",
    }


def test_claimed_job_runs_only_through_ords_and_completes() -> None:
    repository = FakeRepository()
    ords = FakeOrds()
    executed = []
    worker = Worker(
        repository,
        ords,
        pipeline_runner=lambda context: executed.append(context["process_id"]),
        boot_id="boot",
    )

    worker.execute(job())

    assert repository.bound == [(45, 321)]
    assert repository.started == [(45, 99)]
    assert repository.completed == [(45, "SUCCEEDED")]
    assert executed == [12]
    assert ords.started == [321]
    assert ords.completed == [
        (321, {"outcome": "SUCCEEDED", "exit_code": 0, "end_reason": "COMPLETED"})
    ]


def test_missing_local_operation_interrupts_claim_without_running() -> None:
    repository = FakeRepository()
    repository.missing = True
    ords = FakeOrds()
    worker = Worker(
        repository,
        ords,
        pipeline_runner=lambda _: (_ for _ in ()).throw(AssertionError("must not run")),
        boot_id="boot",
    )

    worker.execute(job())

    assert repository.started == []
    assert ords.completed == [
        (
            321,
            {
                "outcome": "INTERRUPTED",
                "exit_code": 0,
                "end_reason": "APPLICATION_OPERATION_NOT_FOUND",
            },
        )
    ]


def test_invalid_process_parameter_fails_without_pipeline(monkeypatch) -> None:
    repository = FakeRepository()
    ords = FakeOrds()
    failures = []
    monkeypatch.setattr(
        "ords_worker.finish_failure",
        lambda process_id, activity_id, exc: failures.append((process_id, activity_id, str(exc))),
    )
    worker = Worker(
        repository,
        ords,
        pipeline_runner=lambda _: (_ for _ in ()).throw(AssertionError("must not run")),
        boot_id="boot",
    )
    invalid = job()
    invalid["parameters"] = {"process_id": 999}

    worker.execute(invalid)

    assert failures == [(12, 99, "process_id does not match")]
    assert repository.completed == [(45, "FAILED", "INVALID_PARAMETERS", "process_id does not match")]
    assert ords.completed[0][1]["end_reason"] == "INVALID_PARAMETERS"


def test_recovered_completed_operation_only_reconciles_ords() -> None:
    repository = FakeRepository()
    repository.context["local_started_at"] = "2026-11-11T10:00:00Z"
    repository.context["local_outcome"] = "SUCCEEDED"
    ords = FakeOrds()
    worker = Worker(
        repository,
        ords,
        pipeline_runner=lambda _: (_ for _ in ()).throw(AssertionError("must not run")),
        boot_id="boot",
    )

    worker.execute(job(), recovered=True)

    assert repository.started == []
    assert repository.completed == []
    assert ords.started == []
    assert ords.completed == [
        (321, {"outcome": "SUCCEEDED", "exit_code": 0, "end_reason": "COMPLETED"})
    ]
