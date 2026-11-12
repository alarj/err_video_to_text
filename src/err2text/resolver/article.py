from __future__ import annotations

import html
import re
from urllib.parse import quote
from urllib.request import Request, urlopen

from err2text.errors import ExitCode, PipelineError
from err2text.models import MediaItem

_VOD = re.compile(r"https?://vod\.err\.ee/dash/vod/([0-9a-f]{32})/(\d+)/", re.IGNORECASE)
_ETVSAATED = re.compile(
    r"(?:https?:)?//vod\.err\.ee/dash/etvsaated/([0-9a-f]{32})/(\d+)/v/manifest\.mpd",
    re.IGNORECASE,
)
_DIRECT_VTT = re.compile(
    r"https://(?:www|services)\.err\.ee/subtitles/file/\d+/[^\"'<>]+\.vtt",
    re.IGNORECASE,
)
_VIDEO_BLOCK = re.compile(
    r'''data-html-src=(?:"|')(?P<url>/media/videoBlock/[0-9a-f]+(?:\?[^"']*)?)(?:"|')''',
    re.IGNORECASE,
)
_MEDIA_EMBED = re.compile(r'''<iframe[^>]+src=(?:"|')(?P<url>(?:https?:)?//services\.err\.ee/media/embed/[0-9a-f]{32})(?:"|')''', re.IGNORECASE)
_TITLE = re.compile(r'<meta[^>]+(?:property|name)=["\']og:title["\'][^>]+content=["\']([^"\']+)', re.IGNORECASE)


def resolve_err_article(url: str) -> tuple[list[MediaItem], dict[str, str]]:
    items, versions, _ = resolve_err_article_sources(url)
    return items, versions


def resolve_err_article_sources(url: str) -> tuple[list[MediaItem], dict[str, str], dict[str, str]]:
    """Find ERR VOD manifest references embedded in an article's page data."""
    page = _download_page(url)
    # ERR news pages often defer player markup to these fragment endpoints.
    # Fetch only same-site relative fragments extracted from the source page.
    blocks = list(dict.fromkeys(_VIDEO_BLOCK.findall(page)))
    etvsaated: list[tuple[str, str, str]] = []
    for block in blocks:
        try:
            block_path = quote(html.unescape(block), safe="/?&=%")
            block_page = _download_page(f"https://www.err.ee{block_path}")
            page += "\n" + block_page
            normalized_block = block_page.replace("\\/", "/")
            subtitle_match = _DIRECT_VTT.search(normalized_block)
            if subtitle_match:
                for vod_id, version in _ETVSAATED.findall(normalized_block):
                    candidate = (vod_id.lower(), version, subtitle_match.group(0))
                    if candidate not in etvsaated:
                        etvsaated.append(candidate)
        except PipelineError:
            # Keep looking in other media blocks; a failed non-selected block
            # must not hide a valid one.
            continue
    embeds = list(dict.fromkeys(_MEDIA_EMBED.findall(page)))
    for embed in embeds:
        try:
            page += "\n" + _download_page(f"https:{embed}" if embed.startswith("//") else embed)
        except PipelineError:
            continue
    found: list[tuple[str, str]] = []
    # Player configuration embedded as JSON may escape its URL slashes.
    for vod_id, version in _VOD.findall(page.replace("\\/", "/")):
        key = (vod_id.lower(), version)
        if key not in found:
            found.append(key)
    if not found and not etvsaated:
        raise PipelineError(ExitCode.ARTICLE_WITHOUT_MEDIA, "No ERR VOD media reference found in article")
    title_match = _TITLE.search(page)
    title = html.unescape(title_match.group(1)) if title_match else None
    if found:
        items = [MediaItem(index=index, title=title, vod_id=vod_id, media_type="video",
                           canonical_url=f"https://vod.err.ee/dash/vod/{vod_id}/{version}/v/manifest.mpd")
                 for index, (vod_id, version) in enumerate(found, start=1)]
        vod_versions = {vod_id: version for vod_id, version in found}
        return items, vod_versions, {}
    items = [MediaItem(index=index, title=title, vod_id=vod_id, media_type="video",
                       canonical_url=f"https://vod.err.ee/dash/etvsaated/{vod_id}/{version}/v/manifest.mpd")
             for index, (vod_id, version, _) in enumerate(etvsaated, start=1)]
    vod_versions = {vod_id: version for vod_id, version, _ in etvsaated}
    vtt_urls = {vod_id: vtt_url for vod_id, _, vtt_url in etvsaated}
    return items, vod_versions, vtt_urls


def _download_page(url: str) -> str:
    try:
        request = Request(url, headers={"User-Agent": "err2text/0.1"})
        with urlopen(request, timeout=60) as response:
            return response.read().decode("utf-8", errors="replace")
    except OSError as error:
        raise PipelineError(ExitCode.DOWNLOAD_FAILED, "Could not download ERR article metadata", {"url": url}) from error


def vtt_url_for(item: MediaItem, version: str) -> str:
    if not item.vod_id:
        raise PipelineError(ExitCode.MEDIA_NOT_FOUND, "Selected ERR item lacks a VOD ID")
    return f"https://vod.err.ee/dash/vod/{item.vod_id}/{version}/v/sub-f4.vtt"


def article_vtt_url_for(
    item: MediaItem,
    versions: dict[str, str],
    direct_vtt_urls: dict[str, str],
) -> str:
    vod_id = item.vod_id or ""
    return direct_vtt_urls.get(vod_id) or vtt_url_for(item, versions[vod_id])
