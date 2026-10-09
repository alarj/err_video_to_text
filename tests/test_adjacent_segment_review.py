from pathlib import Path

import pytest

from backend.app.api.routes import (
    _logical_neighbor_ids,
    _logical_group_edge,
    _merge_text_changed,
    _merge_segment_texts,
    _allocate_split_segment_numbers,
    _validate_logical_neighbor_target,
    _validate_review_target,
    _validate_speaker_assignment_scope,
)
from backend.app.schemas import ReviewCandidateRequest


def test_review_request_supports_an_adjacent_segment_target():
    request = ReviewCandidateRequest.model_validate({
        "candidate_id": 219,
        "status": "PENDING",
        "text": "Muudetud naaberlõik",
        "target_segment_id": 4145,
        "relative_position": "NEXT",
    })

    assert request.target_segment_id == 4145
    assert request.relative_position == "NEXT"


def test_review_request_supports_repeated_split_target():
    request = ReviewCandidateRequest.model_validate({
        "candidate_id": 131,
        "status": "MODIFIED",
        "text": "Valitud alamsegment",
        "reviewed_segment_id": 4631,
        "split_at": 8,
    })

    assert request.reviewed_segment_id == 4631
    assert request.target_segment_id is None


def test_review_request_supports_explicit_neighbor_group_merge():
    request = ReviewCandidateRequest.model_validate({
        "candidate_id": 890,
        "status": "PENDING",
        "target_segment_id": 17626,
        "relative_position": "PREVIOUS",
        "merge_segment_group": True,
    })

    assert request.merge_segment_group is True


def test_review_request_preserves_explicit_speaker_assignment():
    participant = ReviewCandidateRequest.model_validate({
        "candidate_id": 890,
        "status": "PENDING",
        "target_segment_id": 17626,
        "relative_position": "PREVIOUS",
        "merge_segment_group": True,
        "speaker_assignment": "PARTICIPANT",
        "left_transcript_participant_id": 42,
    })
    unknown = ReviewCandidateRequest.model_validate({
        "candidate_id": 890,
        "status": "PENDING",
        "target_segment_id": 17626,
        "relative_position": "PREVIOUS",
        "merge_segment_group": True,
        "speaker_assignment": "UNKNOWN",
    })

    assert participant.speaker_assignment == "PARTICIPANT"
    assert unknown.speaker_assignment == "UNKNOWN"


def test_speaker_assignment_is_rejected_for_normal_candidate_flow():
    request = ReviewCandidateRequest.model_validate({
        "candidate_id": 131,
        "status": "MODIFIED",
        "reviewed_segment_id": 4631,
        "speaker_assignment": "UNKNOWN",
    })

    with pytest.raises(Exception) as error:
        _validate_speaker_assignment_scope(request, False)
    assert error.value.status_code == 422


def test_merge_segment_texts_preserves_all_parts_in_order():
    rows = [
        (17626, 59.94, 61.546, "Urmas Reinsalu Isamaast."),
        (18733, 61.546, 63.42, "Tervist. Ja Lauri Läänemets"),
    ]

    assert _merge_segment_texts(rows) == "Urmas Reinsalu Isamaast.\nTervist. Ja Lauri Läänemets"


def test_merge_text_comparison_uses_complete_group_text():
    merged = "Urmas Reinsalu Isamaast.\nTervist. Ja Lauri Läänemets"

    assert _merge_text_changed(merged, merged) is False
    assert _merge_text_changed("Urmas Reinsalu Isamaast.\nTervist.", merged) is True


def test_repeated_split_requires_modified_decision():
    request = ReviewCandidateRequest.model_validate({
        "candidate_id": 131,
        "status": "ACCEPTED",
        "reviewed_segment_id": 4631,
        "split_at": 8,
    })

    with pytest.raises(Exception) as error:
        _validate_review_target(request)
    assert error.value.status_code == 422


def test_logical_neighbors_skip_all_repeated_split_children():
    ordered_ids = [8177, 8178, 8587, 8588, 8179, 8180]
    group_ids = {8178, 8587, 8588}

    assert _logical_neighbor_ids(ordered_ids, group_ids) == (8177, 8179)


def test_logical_neighbor_target_validation_accepts_previous_and_next():
    previous_id, next_id = _logical_neighbor_ids(
        [8177, 8178, 8587, 8588, 8179, 8180],
        {8178, 8587, 8588},
    )

    _validate_logical_neighbor_target("PREVIOUS", 8177, previous_id, next_id)
    _validate_logical_neighbor_target("NEXT", 8179, previous_id, next_id)


def test_logical_neighbor_target_validation_rejects_distant_next():
    previous_id, next_id = _logical_neighbor_ids(
        [8177, 8178, 8587, 8588, 8179, 8180],
        {8178, 8587, 8588},
    )

    with pytest.raises(Exception) as error:
        _validate_logical_neighbor_target("NEXT", 8180, previous_id, next_id)
    assert error.value.status_code == 422


def test_split_neighbor_group_uses_facing_edge_for_previous_and_next():
    ordered_ids = [8177, 17626, 18733, 8178, 8179]

    assert _logical_group_edge("PREVIOUS", ordered_ids, {17626, 18733}) == 18733
    assert _logical_group_edge("NEXT", ordered_ids, {8179}) == 8179
    assert _logical_group_edge("PREVIOUS", ordered_ids, {17626, 8178}) is None


def test_split_numbers_never_reuse_soft_deleted_history():
    new_number, tail_numbers = _allocate_split_segment_numbers(14, [15, 16])

    assert new_number == 15
    assert tail_numbers == {15: 16, 16: 17}
    assert 14 not in {new_number, *tail_numbers.values()}


def test_repeated_split_allocates_after_new_historical_maximum():
    new_number, tail_numbers = _allocate_split_segment_numbers(1203, [1202, 1204])

    assert new_number == 1204
    assert tail_numbers == {1202: 1205, 1204: 1206}


def test_adjacent_segment_migration_preserves_required_provenance_fields():
    migration = Path("db/schema/004_mvp2_2_adjacent_segment_review.sql").read_text(encoding="utf-8")

    assert "USER_MODIFIED" in migration
    assert "trigger_candidate_id" in migration
    assert "relative_position" in migration
    assert "PREVIOUS" in migration and "NEXT" in migration
    assert "SPEAKER_REASSIGNMENT" in migration
    assert "TEXT_EDIT" in migration
    assert "SPLIT" in migration
    assert "SYSTEM_NOTICE" in migration
