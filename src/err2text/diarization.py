from __future__ import annotations

import hashlib
import os
from pathlib import Path

from err2text.errors import ExitCode, PipelineError
from err2text.models import SpeakerSpan

MODEL_ID = "pyannote/speaker-diarization-community-1"


def run(audio_path: Path, min_speakers: int | None, max_speakers: int | None, threads: int) -> tuple[list[SpeakerSpan], dict[str, object]]:
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise PipelineError(ExitCode.DIARIZATION_FAILED, "HF_TOKEN is required for pyannote diarization")
    try:
        import torch
        from pyannote.audio import Pipeline
    except Exception as error:
        raise PipelineError(ExitCode.DIARIZATION_FAILED, "Could not initialize pyannote.audio", {"type": type(error).__name__}) from error
    try:
        torch.set_num_threads(threads)
        pipeline = Pipeline.from_pretrained(MODEL_ID, token=token)
        output = pipeline(str(audio_path), min_speakers=min_speakers, max_speakers=max_speakers)
        # community-1 returns a DiarizeOutput. Its exclusive diarization is
        # preferable for assigning one speaker to each VTT cue; fall back to
        # the ordinary speaker diarization for compatibility with older APIs.
        annotation = getattr(output, "exclusive_speaker_diarization", None) or getattr(output, "speaker_diarization", output)
        if hasattr(annotation, "itertracks"):
            rows = ((turn, label) for turn, _, label in annotation.itertracks(yield_label=True))
        else:
            rows = iter(annotation)
        spans = [SpeakerSpan(str(label), float(turn.start), float(turn.end)) for turn, label in rows]
    except Exception as error:
        raise PipelineError(ExitCode.DIARIZATION_FAILED, "Diarization failed", {"type": type(error).__name__}) from error
    raw = [{"speaker_id": item.speaker_id, "start": item.start, "end": item.end} for item in spans]
    digest = hashlib.sha256(repr(raw).encode()).hexdigest()
    return spans, {"schema_version": "1.0", "model": MODEL_ID, "segments": raw, "run_id": digest, "sha256": digest}
