from __future__ import annotations

import json

from app.services.ords import OrdsClient, OrdsSettings


class Response:
    def __init__(self, payload: dict[str, object], status: int = 200) -> None:
        self.payload = json.dumps(payload).encode("utf-8")
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self) -> bytes:
        return self.payload


class FakeOpener:
    def __init__(self) -> None:
        self.requests = []
        self.token_count = 0

    def __call__(self, request, timeout):
        self.requests.append(request)
        if request.full_url.endswith("/oauth/token"):
            self.token_count += 1
            return Response({"access_token": f"token-{self.token_count}", "expires_in": 3600})
        return Response({"job_id": 321, "status": "QUEUED"}, status=201)


def settings() -> OrdsSettings:
    return OrdsSettings("https://ords.example/jobs", "client", "secret", host_id="host")


def test_registration_uses_operation_id_and_dated_media_title() -> None:
    opener = FakeOpener()
    client = OrdsClient(settings(), opener=opener, clock=lambda: 100.0, sleeper=lambda _: None)

    result = client.register_diarization(
        operation_id=45,
        process_id=12,
        idempotency_key="err_video_to_text:diarization:uuid",
        media_title="2026-11-04 — Esimene stuudio",
        media_published_date="2026-11-04T00:00:00Z",
    )

    assert result == {"job_id": 321, "status": "QUEUED"}
    assert opener.token_count == 1
    payload = json.loads(opener.requests[1].data.decode("utf-8"))
    assert payload == {
        "application_code": "err_video_to_text",
        "job_type_code": "diarization",
        "application_job_id": "45",
        "idempotency_key": "err_video_to_text:diarization:uuid",
        "previous_job_id": None,
        "parameters": {
            "process_id": 12,
            "media_title": "2026-11-04 — Esimene stuudio",
            "media_published_date": "2026-11-04T00:00:00Z",
        },
    }


def test_token_is_reused_for_job_status() -> None:
    opener = FakeOpener()
    client = OrdsClient(settings(), opener=opener, clock=lambda: 100.0, sleeper=lambda _: None)

    client.register_diarization(
        operation_id=45,
        process_id=12,
        idempotency_key="key",
        media_title="2026-11-04 — Saade",
        media_published_date="2026-11-04T00:00:00Z",
    )
    client.job_status(321)

    assert opener.token_count == 1
    assert opener.requests[2].get_header("Authorization") == "Bearer token-1"
