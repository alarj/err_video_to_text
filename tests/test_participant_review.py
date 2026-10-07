from backend.app.services.participant_review import select_speaker_samples


def _row(segment_id, start, end, confidence):
    return {
        "speaker_label": "SPEAKER_00",
        "segment_id": segment_id,
        "start_second": start,
        "end_second": end,
        "text": str(segment_id),
        "confidence": confidence,
    }


def test_samples_are_distributed_and_prefer_confidence():
    rows = [
        _row(1, 0, 2, 0.9),
        _row(2, 10, 12, 0.8),
        _row(3, 20, 22, 0.95),
        _row(4, 21, 25, 0.5),
    ]

    result = select_speaker_samples(rows)

    assert [item["segment_id"] for item in result["SPEAKER_00"]] == [1, 2, 3]


def test_samples_fill_missing_time_bucket_without_threshold_assumptions():
    rows = [_row(1, 0, 2, 0.9), _row(2, 1, 4, 0.8)]

    result = select_speaker_samples(rows)

    assert [item["segment_id"] for item in result["SPEAKER_00"]] == [1, 2]


def test_samples_are_selected_independently_for_each_speaker():
    rows = [_row(1, 0, 2, 0.9), _row(2, 10, 12, 0.8)]
    second_speaker = _row(3, 20, 23, 0.95)
    second_speaker["speaker_label"] = "SPEAKER_01"
    rows.append(second_speaker)

    result = select_speaker_samples(rows)

    assert [item["segment_id"] for item in result["SPEAKER_00"]] == [1, 2]
    assert [item["segment_id"] for item in result["SPEAKER_01"]] == [3]
