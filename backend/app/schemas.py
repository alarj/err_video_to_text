from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class ResolveRequest(BaseModel):
    url: HttpUrl


class MediaCandidate(BaseModel):
    index: int = Field(gt=0)
    title: str | None = None
    canonical_url: str | None = None
    vod_id: str | None = None
    duration_seconds: float | None = None
    media_type: str | None = None
    assets: list[dict[str, str]] = Field(default_factory=list)


class CreateJobRequest(BaseModel):
    source_url: HttpUrl
    confirm: bool
    selected_media: MediaCandidate
    title: str | None = None
    description: str | None = None
    published_date: str | None = None
    assets: list[dict[str, str]] = Field(default_factory=list)


class JobResponse(BaseModel):
    id: int
    status: str
    reused: bool = False


class ParticipantCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=4000)
    organisation: str | None = Field(default=None, max_length=500)
    occupation: str | None = Field(default=None, max_length=500)


class SpeakerMapping(BaseModel):
    speaker_label: str = Field(min_length=1, max_length=80)
    participant_id: int | None = Field(default=None, gt=0)
    role: str | None = Field(default=None, max_length=120)
    mapping_status: Literal["UNCONFIRMED", "CONFIRMED", "UNKNOWN"]


class ParticipantReviewRequest(BaseModel):
    mappings: list[SpeakerMapping] = Field(default_factory=list)
    confirm: bool = False


class ReviewCandidateRequest(BaseModel):
    candidate_id: int = Field(gt=0)
    status: Literal["PENDING", "ACCEPTED", "REJECTED", "MODIFIED"]
    decision: str | None = Field(default=None, max_length=30)
    text: str | None = Field(default=None, max_length=4000)
    segment_type: Literal["SPEECH", "SYSTEM_NOTICE"] | None = None
    split_at: int | None = Field(default=None, gt=0)
    left_transcript_participant_id: int | None = Field(default=None, gt=0)
    right_transcript_participant_id: int | None = Field(default=None, gt=0)
    reviewed_segment_id: int | None = Field(default=None, gt=0)
    target_segment_id: int | None = Field(default=None, gt=0)
    relative_position: Literal["PREVIOUS", "NEXT"] | None = None
    merge_segment_group: bool = False
    speaker_assignment: Literal["PARTICIPANT", "UNKNOWN"] | None = None
