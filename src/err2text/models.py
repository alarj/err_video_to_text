from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum


class UrlType(StrEnum):
    ERR_ARTICLE = "ERR_ARTICLE"
    JUPITER_MEDIA = "JUPITER_MEDIA"
    ERR_ARCHIVE_MEDIA = "ERR_ARCHIVE_MEDIA"
    DIRECT_TECHNICAL_URL = "DIRECT_TECHNICAL_URL"


@dataclass(frozen=True)
class MediaItem:
    index: int
    title: str | None = None
    canonical_url: str | None = None
    vod_id: str | None = None
    duration_seconds: float | None = None
    media_type: str | None = None


@dataclass(frozen=True)
class Cue:
    id: str
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class SpeakerSpan:
    speaker_id: str
    start: float
    end: float


@dataclass
class Segment:
    id: str
    start: float
    end: float
    speaker_id: str | None
    speaker_name: str | None
    speaker_name_source: str | None
    attribution_status: str
    vtt_cue_ids: list[str]
    overlap_ratio: float
    attribution_confidence: str
    split_estimated: bool
    text: str

    def json(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class RunContext:
    source_url: str
    output_dir: str
    work_key: str | None = None
    time_offset_seconds: float = 0.0
    min_speakers: int | None = None
    max_speakers: int | None = None
    no_cache: bool = False
    keep_audio: bool = False
    durations: dict[str, float] = field(default_factory=dict)
