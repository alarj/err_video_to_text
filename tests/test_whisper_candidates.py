from err2text.whisper_review.candidates import select_candidates


def test_selects_low_confidence_and_internal_boundary() -> None:
    transcript = {
        "segments": [
            {"id": "seg_0001", "start": 0.0, "end": 3.0, "speaker_id": "SPEAKER_00", "text": "Tere", "attribution_confidence": "high", "attribution_status": "assigned"},
            {"id": "seg_0002", "start": 3.0, "end": 6.0, "speaker_id": "SPEAKER_01", "text": "Vastus", "attribution_confidence": "low", "attribution_status": "assigned"},
        ]
    }
    speakers = [
        {"speaker_id": "SPEAKER_00", "start": 0.0, "end": 4.0},
        {"speaker_id": "SPEAKER_01", "start": 4.0, "end": 6.0},
    ]

    candidates = select_candidates(transcript, speakers, short_segment_seconds=2.0, max_candidates=10)

    assert [item["segment_ids"] for item in candidates] == [["seg_0002"]]
    assert set(candidates[0]["reasons"]) == {"medium_low_or_unassigned_attribution", "diarization_boundary_inside_vtt_cue"}


def test_selects_manual_segment_id_without_guessing_its_time_range() -> None:
    transcript = {
        "segments": [
            {"id": "seg_0007", "start": 12.3, "end": 15.4, "speaker_id": "SPEAKER_01", "text": "Kontroll", "attribution_confidence": "high", "attribution_status": "assigned"},
        ]
    }

    candidates = select_candidates(
        transcript, [], short_segment_seconds=2.0, max_candidates=10,
        manual_candidates=[{"segment_id": "seg_0007", "reason": "claude_review"}],
    )

    assert candidates[0]["start"] == 12.3
    assert candidates[0]["end"] == 15.4
    assert candidates[0]["selection_source"] == "manual"
    assert candidates[0]["reasons"] == ["claude_review"]
