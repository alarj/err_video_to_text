import json
from pathlib import Path

from import_jutusta import (
    compare_transcripts,
    load_jutusta,
    normalize_comparison_text,
    render_transcript_markdown,
    semantic_equivalent,
)


def test_jutusta_draft_comparison_is_segment_based(tmp_path: Path) -> None:
    source = tmp_path / "jutusta.json"
    source.write_text(json.dumps({
        "job_id": "job-1",
        "segments": [{
            "start": 10.0, "end": 12.0, "speaker": "Mari Maasikas", "text": "Tere maailm.",
            "words": [
                {"text": "Tere", "start": 10.0, "end": 10.5},
                {"text": "maailm.", "start": 10.6, "end": 11.2},
            ],
        }],
    }), encoding="utf-8")
    payload = load_jutusta(source)
    comparison = compare_transcripts([{
        "version_id": 1, "version_type": "AUTOMATIC_DRAFT", "segment_id": 11,
        "segment_number": 1, "source_segment_id": None, "start": 10.0, "end": 12.0,
        "text": "Tere maailm", "segment_type": "SPEECH", "speaker": "Mari Maasikas",
    }], payload, 0.0, {11}, set(), set())

    assert comparison["items"][0]["text_verdict"] == "SEMANTIC_MATCH"
    assert comparison["items"][0]["speaker_verdict"] == "MATCH"
    assert comparison["items"][0]["review_scope"] == "CANDIDATE"
    assert comparison["summary"]["AUTOMATIC_DRAFT"]["segments"] == 1
    assert b"Jutusta.ee" in render_transcript_markdown(payload, 0.0)


def test_system_notices_are_excluded_from_audio_comparison(tmp_path: Path) -> None:
    source = tmp_path / "jutusta.json"
    source.write_text(json.dumps({
        "segments": [{
            "start": 10.0, "end": 12.0, "speaker": "Mari Maasikas", "text": "Tere.",
            "words": [{"text": "Tere.", "start": 10.0, "end": 10.5}],
        }],
    }), encoding="utf-8")
    payload = load_jutusta(source)
    common = {
        "version_id": 1, "version_type": "AUTOMATIC_DRAFT", "source_segment_id": None,
        "speaker": None,
    }
    comparison = compare_transcripts([
        {**common, "segment_id": 10, "segment_number": 1, "start": 1.0, "end": 3.0,
         "text": "Järgnevale saatele kuvatakse automaatsubtiitrid.", "segment_type": "SYSTEM_NOTICE"},
        {**common, "segment_id": 11, "segment_number": 2, "start": 10.0, "end": 12.0,
         "text": "Tere.", "segment_type": "SPEECH", "speaker": "Mari Maasikas"},
    ], payload, 0.0, set(), set(), set())

    assert [item["segment_id"] for item in comparison["items"]] == [11]
    assert comparison["summary"]["AUTOMATIC_DRAFT"]["segments"] == 1


def test_matching_word_just_outside_boundary_is_aligned(tmp_path: Path) -> None:
    source = tmp_path / "jutusta.json"
    source.write_text(json.dumps({
        "segments": [{
            "start": 10.0, "end": 12.0, "speaker": "Tõnis Lukas", "text": "Mina.",
            "words": [{"text": "Mina.", "start": 10.10, "end": 10.30}],
        }],
    }), encoding="utf-8")
    payload = load_jutusta(source)
    comparison = compare_transcripts([{
        "version_id": 1, "version_type": "REVIEWED_DRAFT", "segment_id": 11,
        "segment_number": 1, "source_segment_id": 10, "start": 10.334, "end": 10.76,
        "text": "Mina.", "segment_type": "SPEECH", "speaker": "Tõnis Lukas",
    }], payload, 0.0, {10}, set(), set())

    item = comparison["items"][0]
    assert item["jutusta_text"] == "Mina."
    assert item["text_verdict"] == "SEMANTIC_MATCH"


def test_different_nearby_word_does_not_rescue_unaligned_segment(tmp_path: Path) -> None:
    source = tmp_path / "jutusta.json"
    source.write_text(json.dumps({
        "segments": [{
            "start": 10.0, "end": 12.0, "speaker": "Yoko Alender", "text": "On tõenäoline.",
            "words": [{"text": "On", "start": 10.90, "end": 11.05}],
        }],
    }), encoding="utf-8")
    payload = load_jutusta(source)
    comparison = compare_transcripts([{
        "version_id": 1, "version_type": "REVIEWED_DRAFT", "segment_id": 11,
        "segment_number": 1, "source_segment_id": 10, "start": 10.20, "end": 10.75,
        "text": "Gaasijaamad?", "segment_type": "SPEECH", "speaker": "Liisu Lass",
    }], payload, 0.0, {10}, set(), set())

    item = comparison["items"][0]
    assert item["jutusta_text"] == ""
    assert item["text_verdict"] == "UNALIGNED"


def test_estonian_digit_and_word_numbers_are_semantically_equal() -> None:
    pairs = [
        ("2 karu", "kaks karu"),
        ("23. aastal", "kahekümne kolmandal aastal"),
        ("2027.-ks aastaks", "kahe tuhande kahekümne seitsmendaks aastaks"),
        ("120 protsenti", "sada kakskümmend protsenti"),
        ("50 60 tundi", "viiskümmend kuuskümmend tundi"),
    ]

    for left, right in pairs:
        assert normalize_comparison_text(left) == normalize_comparison_text(right)


def test_fillers_do_not_create_a_semantic_difference() -> None:
    left = normalize_comparison_text("lihtsalt")
    right = normalize_comparison_text("lihtsalt no, noh")

    assert semantic_equivalent(left, right)


def test_jutusta_version_is_excluded_from_review_workflow() -> None:
    source = Path("backend/app/api/routes.py").read_text(encoding="utf-8")
    migration = Path("db/schema/007_jutusta_ee_draft.sql").read_text(encoding="utf-8")

    assert "version_type IN ('AUTOMATIC_DRAFT', 'REVIEWED_DRAFT')" in source
    assert "JUTUSTA_EE_DRAFT" in migration
    assert "JUTUSTA_EE_DRAFT" not in source


def test_automatic_speaker_labels_use_reviewed_names_for_comparison() -> None:
    source = Path("backend/import_jutusta.py").read_text(encoding="utf-8")

    assert "reviewed_speaker_names.get(str(label))" in source
    assert "tp.mapping_status = 'CONFIRMED'" in source


def test_results_view_has_specific_jutusta_labels() -> None:
    app = Path("frontend_dist/assets/app.js").read_text(encoding="utf-8")
    translations = json.loads(Path("frontend_dist/assets/i18n/et.json").read_text(encoding="utf-8"))

    assert "JUTUSTA_EE_TRANSCRIPT_MARKDOWN" in app
    assert "JUTUSTA_EE_COMPARISON_MARKDOWN" in app
    assert translations["artifacts.transcript_jutusta_ee"] == "Transkriptsioon (Jutusta.ee)"
    assert translations["artifacts.comparison_jutusta_ee"] == "Jutusta.ee võrdlus"
