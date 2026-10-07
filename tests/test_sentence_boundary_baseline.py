from err2text.sentence_boundary_review.runner import find_candidates


def test_find_candidates_uses_sentence_boundary_and_skips_system_notice() -> None:
    transcript = {
        "segments": [
            {"id": "seg_notice", "start": 0.0, "end": 2.0, "text": "Järgnevale saatele\nkuvatakse automaatsubtiitrid."},
            {"id": "seg_1", "start": 10.0, "end": 16.0, "text": "See on lause. Järgmine vastus", "speaker_id": "SPEAKER_00"},
        ]
    }
    speakers = [
        {"speaker_id": "SPEAKER_00", "start": 10.0, "end": 12.0},
        {"speaker_id": "SPEAKER_01", "start": 12.5, "end": 16.0},
    ]

    candidates = find_candidates(transcript, speakers)

    assert [item["segment_ids"] for item in candidates] == [["seg_1"]]
    assert candidates[0]["candidate_type"] == "SPEAKER_BOUNDARY"


def test_distinct_speakers_always_create_one_candidate_without_sentence_end() -> None:
    transcript = {"segments": [{"id": "seg_1", "start": 10.0, "end": 14.0, "text": "üks kaks kolm neli"}]}
    speakers = [
        {"speaker_id": "SPEAKER_00", "start": 10.5, "end": 11.5},
        {"speaker_id": "SPEAKER_01", "start": 11.5, "end": 14.0},
    ]

    candidates = find_candidates(transcript, speakers)

    assert len(candidates) == 1
    assert candidates[0]["candidate_type"] == "MULTI_SPEAKER_SEGMENT"


def test_repeated_same_speaker_intervals_do_not_create_candidate() -> None:
    transcript = {"segments": [{"id": "seg_1", "start": 10.0, "end": 14.0, "text": "üks kaks kolm neli"}]}
    speakers = [
        {"speaker_id": "SPEAKER_00", "start": 10.0, "end": 11.0},
        {"speaker_id": "SPEAKER_00", "start": 11.0, "end": 12.0},
        {"speaker_id": "SPEAKER_00", "start": 12.0, "end": 14.0},
    ]

    assert find_candidates(transcript, speakers) == []


def test_overlapping_distinct_speakers_get_overlap_candidate() -> None:
    transcript = {"segments": [{"id": "seg_1", "start": 10.0, "end": 14.0, "text": "üks kaks kolm neli"}]}
    speakers = [
        {"speaker_id": "SPEAKER_00", "start": 10.0, "end": 12.0},
        {"speaker_id": "SPEAKER_01", "start": 11.5, "end": 14.0},
    ]

    candidates = find_candidates(transcript, speakers)

    assert len(candidates) == 1
    assert candidates[0]["candidate_type"] == "OVERLAPPING_SPEECH"


def test_micro_secondary_label_is_diagnostic_only() -> None:
    transcript = {"segments": [{"id": "seg_1", "start": 10.0, "end": 14.0, "text": "üks kaks kolm neli"}]}
    speakers = [
        {"speaker_id": "SPEAKER_00", "start": 10.0, "end": 13.95},
        {"speaker_id": "SPEAKER_01", "start": 13.95, "end": 14.0},
    ]

    assert find_candidates(transcript, speakers) == []


def test_long_edge_only_secondary_without_text_boundary_is_attribution_conflict() -> None:
    transcript = {"segments": [{"id": "seg_1", "start": 10.0, "end": 14.0, "text": "üks kaks kolm neli"}]}
    speakers = [
        {"speaker_id": "SPEAKER_00", "start": 10.0, "end": 11.0},
        {"speaker_id": "SPEAKER_01", "start": 11.0, "end": 14.0},
    ]

    candidates = find_candidates(transcript, speakers)

    assert len(candidates) == 1
    assert candidates[0]["candidate_type"] == "SPEAKER_ATTRIBUTION_CONFLICT"


def test_short_edge_secondary_with_sentence_evidence_is_boundary_candidate() -> None:
    transcript = {"segments": [{"id": "seg_1", "start": 10.0, "end": 14.0, "text": "See on lause. Nii"}]}
    speakers = [
        {"speaker_id": "SPEAKER_00", "start": 10.0, "end": 13.6},
        {"speaker_id": "SPEAKER_01", "start": 13.6, "end": 14.0},
    ]

    candidates = find_candidates(transcript, speakers)

    assert len(candidates) == 1
    assert candidates[0]["candidate_type"] == "SPEAKER_BOUNDARY"
