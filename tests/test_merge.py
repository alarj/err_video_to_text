from err2text.merge.attribution import merge_cues
from err2text.models import Cue, SpeakerSpan


def test_cue_crossing_speaker_boundary_is_assigned_once_to_dominant_speaker() -> None:
    segments = merge_cues([Cue("cue_1", 0, 10, "tekst")], [SpeakerSpan("SPEAKER_00", 0, 4), SpeakerSpan("SPEAKER_01", 4, 10)])
    assert [(item.start, item.end, item.speaker_id, item.text) for item in segments] == [(0, 10, "SPEAKER_01", "tekst")]
    assert segments[0].split_estimated is False


def test_cue_without_overlap_is_unassigned() -> None:
    segment = merge_cues([Cue("cue_1", 10, 12, "tekst")], [SpeakerSpan("SPEAKER_00", 0, 2)])[0]
    assert segment.attribution_status == "unassigned"
    assert segment.speaker_id is None
    assert segment.speaker_name is None


def test_time_offset_is_applied() -> None:
    segment = merge_cues([Cue("cue_1", 10, 12, "tekst")], [SpeakerSpan("SPEAKER_00", 8, 10)], time_offset_seconds=2)[0]
    assert segment.speaker_id == "SPEAKER_00"
