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
