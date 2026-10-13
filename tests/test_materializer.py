import json

import pytest

from app.services.materializer import materialize, prepare


class _Var:
    def __init__(self, value):
        self.value = value

    def getvalue(self):
        return [self.value]


class _Cursor:
    def __init__(self):
        self.statements = []
        self.next_id = 100

    def var(self, _type):
        self.next_id += 1
        return _Var(self.next_id)

    def execute(self, sql, params=None):
        self.statements.append((sql, params or {}))


def _write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def test_prepare_classifies_generated_artifacts_and_skips_system_notice(tmp_path) -> None:
    _write_json(tmp_path / "transcript.json", {"segments": [
        {"id": "notice", "start": 0.0, "end": 2.0, "text": "Teksti automaatsel tuvastamisel võib esineda ebatäpsusi."},
        {"id": "speech", "start": 2.0, "end": 8.0, "text": "Esimene lause. Teine lause"},
    ]})
    _write_json(tmp_path / "speakers.json", {"segments": [
        {"start": 2.0, "end": 5.0, "speaker_id": "SPEAKER_00"},
        {"start": 5.0, "end": 8.0, "speaker_id": "SPEAKER_01"},
    ]})
    for name in ("original.vtt", "normalized.vtt", "resolver.json", "run_metadata.json", "speaker_review.json"):
        (tmp_path / name).write_text("{}", encoding="utf-8")
    (tmp_path / "saade-transcript.md").write_text("automaatne", encoding="utf-8")

    prepared = prepare(tmp_path)
    assert all("notice" not in candidate.get("segment_ids", []) for candidate in prepared.candidates)
    by_name = {item["name"]: item for item in prepared.artifacts}
    assert by_name["speaker_review.json"]["artifact_type"] == "AUTOMATIC_SPEAKER_REVIEW_JSON"
    assert by_name["saade-transcript.md"]["artifact_type"] == "AUTOMATIC_TRANSCRIPT_MARKDOWN"
    assert by_name["saade-transcript.md"]["transcript_artifact"] is True
    assert by_name["resolver.json"]["transcript_artifact"] is False


def test_prepare_rejects_text_that_does_not_fit_oracle_column(tmp_path) -> None:
    _write_json(tmp_path / "transcript.json", {"segments": [
        {"id": "long", "start": 0, "end": 1, "text": "x" * 4001}
    ]})
    _write_json(tmp_path / "speakers.json", {"segments": []})
    with pytest.raises(ValueError, match="exceeds Oracle VARCHAR2\\(4000\\)"):
        prepare(tmp_path)


def test_prepare_can_mark_preserved_legacy_files_as_manual(tmp_path) -> None:
    _write_json(tmp_path / "transcript.json", {"segments": []})
    _write_json(tmp_path / "speakers.json", {"segments": []})
    (tmp_path / "speaker_review.json").write_text("{}", encoding="utf-8")
    (tmp_path / "legacy-transcript.md").write_text("käsitsi parandatud", encoding="utf-8")
    prepared = prepare(tmp_path, {
        "speaker_review.json": {"artifact_type": "LEGACY_MANUAL_SPEAKER_REVIEW_JSON", "transcript_artifact": False},
        "legacy-transcript.md": {"artifact_type": "LEGACY_MANUAL_TRANSCRIPT_MARKDOWN", "transcript_artifact": False},
    })
    by_name = {item["name"]: item for item in prepared.artifacts}
    assert by_name["speaker_review.json"]["artifact_type"] == "LEGACY_MANUAL_SPEAKER_REVIEW_JSON"
    assert by_name["legacy-transcript.md"]["transcript_artifact"] is False


def test_materialize_rejects_overlong_candidate_reason(tmp_path) -> None:
    _write_json(tmp_path / "transcript.json", {"segments": []})
    _write_json(tmp_path / "speakers.json", {"segments": []})
    prepared = prepare(tmp_path)
    from dataclasses import replace
    overlong = [{"segment_ids": [], "candidate_type": "SPEAKER_BOUNDARY", "reason": "x" * 1001}]
    with pytest.raises(ValueError, match="candidate reason exceeds Oracle VARCHAR2\\(1000\\)"):
        materialize(_Cursor(), 1, 2, replace(prepared, candidates=overlong))


def test_materialize_keeps_system_notice_without_speaker_link(tmp_path) -> None:
    _write_json(tmp_path / "transcript.json", {"segments": [
        {"id": "notice", "start": 0.0, "end": 2.0, "text": "Teksti automaatsel tuvastamisel võib esineda ebatäpsusi."},
        {"id": "speech", "start": 2.0, "end": 8.0, "text": "Esimene lause. Teine lause"},
    ]})
    _write_json(tmp_path / "speakers.json", {"segments": [
        {"start": 2.0, "end": 5.0, "speaker_id": "SPEAKER_00"},
        {"start": 5.0, "end": 8.0, "speaker_id": "SPEAKER_01"},
    ]})
    prepared = prepare(tmp_path)
    cursor = _Cursor()
    materialize(cursor, 1, 2, prepared)
    segment_inserts = [item for item in cursor.statements if "INSERT INTO transcript_segments" in item[0]]
    speaker_inserts = [item for item in cursor.statements if "INSERT INTO transcript_segment_speakers" in item[0]]
    assert len(segment_inserts) == 2
    assert len(speaker_inserts) == 2
    assert any(item[1]["segment_type"] == "SYSTEM_NOTICE" for item in segment_inserts)
    notice_db_id = next(item[1]["segment_id"] for item in segment_inserts if item[1]["segment_type"] == "SYSTEM_NOTICE")
    assert all(item[1]["segment_id"] != notice_db_id for item in speaker_inserts)
