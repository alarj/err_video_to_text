import pytest

from err2text.errors import ExitCode, PipelineError
from err2text.names.apply import apply_names


def test_name_map_is_applied_only_when_run_matches() -> None:
    transcript = {
        "segments": [{"speaker_id": "SPEAKER_00", "speaker_name": "UNKNOWN", "speaker_name_source": "unknown"}],
        "turns": [{"speaker_id": "SPEAKER_00", "speaker_name": "UNKNOWN"}],
    }
    speakers = {"run_id": "run-1", "segments": []}
    mapped = apply_names(transcript, speakers, {"diarization_run_id": "run-1", "SPEAKER_00": {"name": "Mirko Ojakivi", "source": "manual"}})
    assert mapped["segments"][0]["speaker_name"] == "Mirko Ojakivi"
    assert mapped["turns"][0]["speaker_name"] == "Mirko Ojakivi"


def test_name_map_rejects_wrong_run() -> None:
    with pytest.raises(PipelineError) as caught:
        apply_names({"segments": []}, {"run_id": "run-1", "segments": []}, {"diarization_run_id": "run-2"})
    assert caught.value.code == ExitCode.INVALID_SPEAKERS_MAP
