from __future__ import annotations

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
