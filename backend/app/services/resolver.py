from __future__ import annotations

from dataclasses import asdict

from err2text.errors import ExitCode, PipelineError
from err2text.media import err_vod_items_from_metadata, media_items, ytdlp_metadata
from err2text.models import UrlType
from err2text.resolver.article import resolve_err_article, vtt_url_for
from err2text.resolver.classify import classify_url


def resolve(url: str) -> dict[str, object]:
    url_type = classify_url(url)
    metadata = ytdlp_metadata(url)
    article_versions: dict[str, str] = {}
    if url_type == UrlType.ERR_ARTICLE:
        items, article_versions = err_vod_items_from_metadata(metadata)
        if not items:
            items, article_versions = resolve_err_article(url)
    else:
        items = media_items(metadata)
    if not items:
        raise PipelineError(ExitCode.ARTICLE_WITHOUT_MEDIA, "No related media was found")
    media_payloads = []
    for item in items:
        payload = asdict(item)
        assets: list[dict[str, str]] = []
        if item.canonical_url:
            canonical = item.canonical_url.lower()
            asset_type = "MANIFEST" if canonical.endswith((".m3u8", ".mpd")) else "VIDEO"
            assets.append({"asset_type": asset_type, "url": item.canonical_url})
        if item.vod_id and item.vod_id in article_versions:
            assets.append({"asset_type": "VTT", "url": vtt_url_for(item, article_versions[item.vod_id])})
        payload["assets"] = assets
        media_payloads.append(payload)
    return {
        "source_url": url,
        "url_type": str(url_type),
        "title": metadata.get("title"),
        "description": metadata.get("description"),
        "published_date": metadata.get("upload_date"),
        "media_items": media_payloads,
        "article_versions": article_versions,
    }
