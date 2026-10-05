from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class ExitCode(IntEnum):
    SUCCESS = 0
    UNSUPPORTED_URL = 20
    ARTICLE_WITHOUT_MEDIA = 21
    MEDIA_NOT_FOUND = 22
    DRM_PROTECTED = 23
    DOWNLOAD_FAILED = 24
    DIARIZATION_FAILED = 25
    MERGE_FAILED = 26
    INVALID_SPEAKERS_MAP = 27
    INVALID_ARGUMENT = 28
    WHISPER_REVIEW_FAILED = 29
    ALIGNMENT_REVIEW_FAILED = 30


@dataclass
class PipelineError(Exception):
    code: ExitCode
    message: str
    details: dict[str, object] | None = None

    def as_json(self) -> dict[str, object]:
        return {"error": self.code.name, "message": self.message, "details": self.details or {}}
