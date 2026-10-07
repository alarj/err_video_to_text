import json

import pytest


def _make_legacy_tree(tmp_path):
    from import_legacy import inventory, load_payload

    root = tmp_path / "runtime"
    output = root / "outputs" / "reinsalu-isamaa"
    review_inputs = root / "review-inputs"
    output.mkdir(parents=True)
    review_inputs.mkdir()
    (output / "resolver.json").write_text(json.dumps({
        "source_url": "https://www.err.ee/test",
        "title": "Test",
        "selected_media": {"canonical_url": "https://vod.err.ee/test", "title": "Test"},
    }), encoding="utf-8")
    (output / "transcript.json").write_text(json.dumps({"segments": []}), encoding="utf-8")
    (output / "speakers.json").write_text(json.dumps({"segments": []}), encoding="utf-8")
    for name in ("original.vtt", "normalized.vtt", "run_metadata.json", "speaker_review.json"):
        (output / name).write_text("{}", encoding="utf-8")
    (review_inputs / "reinsalu-isamaa-candidates.json").write_text(
        json.dumps({"candidates": [{"segment_id": "seg_1", "reason": "control"}]}), encoding="utf-8"
    )
    (review_inputs / "reinsalu-isamaa-alignment-evaluation-1.json").write_text(
        json.dumps({"cases": [{"verdict": "clean_transition", "before_segment_id": "a", "after_segment_id": "b"}]}), encoding="utf-8"
    )
    return output, load_payload, inventory


def test_legacy_inventory_requires_both_control_files(tmp_path) -> None:
    output, load_payload, inventory = _make_legacy_tree(tmp_path)
    payload = load_payload(output)
    report = inventory(payload)
    assert report["candidate_control_count"] == 1
    assert report["candidate_control_evaluation"]["clean_control_case_count"] == 1

    (output.parent.parent / "review-inputs" / "reinsalu-isamaa-alignment-evaluation-1.json").unlink()
    with pytest.raises(FileNotFoundError, match="mandatory legacy control files"):
        load_payload(output)
