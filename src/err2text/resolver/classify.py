from __future__ import annotations

from urllib.parse import urlparse

from err2text.errors import ExitCode, PipelineError
from err2text.models import UrlType


def classify_url(url: str) -> UrlType:
    parsed = urlparse(url)
    host = parsed.hostname.lower() if parsed.hostname else ""
    path = parsed.path.lower()
    if parsed.scheme not in {"http", "https"}:
        raise PipelineError(ExitCode.UNSUPPORTED_URL, "URL must use http or https")
    if host == "vod.err.ee" and (path.endswith(".vtt") or path.endswith(".mpd")):
        return UrlType.DIRECT_TECHNICAL_URL
    if host in {"www.err.ee", "err.ee"}:
        return UrlType.ERR_ARTICLE
    if host == "jupiter.err.ee" or host.endswith(".jupiter.err.ee"):
        return UrlType.JUPITER_MEDIA
    if host == "arhiiv.err.ee" or host.endswith(".arhiiv.err.ee"):
        return UrlType.ERR_ARCHIVE_MEDIA
    raise PipelineError(ExitCode.UNSUPPORTED_URL, "Only ERR/Jupiter URLs are supported", {"host": host})
