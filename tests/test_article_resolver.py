from err2text.resolver import article
from err2text.resolver.article import (
    _MEDIA_EMBED,
    _VIDEO_BLOCK,
    article_vtt_url_for,
    resolve_err_article,
    resolve_err_article_sources,
    vtt_url_for,
)
from err2text.models import MediaItem


def test_vtt_url_uses_discovered_vod_id_and_version() -> None:
    item = MediaItem(index=1, vod_id="b4eb8107755029f5c6e92f8cfcf14911")
    assert vtt_url_for(item, "2") == "https://vod.err.ee/dash/vod/b4eb8107755029f5c6e92f8cfcf14911/2/v/sub-f4.vtt"


def test_article_vtt_url_keeps_existing_vod_fallback() -> None:
    item = MediaItem(index=1, vod_id="b4eb8107755029f5c6e92f8cfcf14911")
    assert article_vtt_url_for(item, {item.vod_id: "2"}, {}) == (
        "https://vod.err.ee/dash/vod/b4eb8107755029f5c6e92f8cfcf14911/2/v/sub-f4.vtt"
    )


def test_article_vtt_url_prefers_direct_etvsaated_subtitle() -> None:
    item = MediaItem(index=1, vod_id="2bcf0f7cc196c36275aae42df21a216a")
    direct_url = "https://www.err.ee/subtitles/file/446623/446623_VA.vtt"
    assert article_vtt_url_for(item, {item.vod_id: "5"}, {item.vod_id: direct_url}) == direct_url


def test_article_video_block_reference_is_detected() -> None:
    document = '<div data-html-src="/media/videoBlock/b4eb8107755029f5c6e92f8cfcf14911"></div>'
    assert _VIDEO_BLOCK.findall(document) == ["/media/videoBlock/b4eb8107755029f5c6e92f8cfcf14911"]


def test_article_video_block_reference_keeps_query_parameters() -> None:
    document = (
        '<div data-html-src="/media/videoBlock/2bcf0f7cc196c36275aae42df21a216a'
        '?photoId=3855547&amp;contentId=1610173927"></div>'
    )
    assert _VIDEO_BLOCK.findall(document) == [
        "/media/videoBlock/2bcf0f7cc196c36275aae42df21a216a?photoId=3855547&amp;contentId=1610173927"
    ]


def test_article_media_embed_reference_is_detected() -> None:
    document = '<iframe src="//services.err.ee/media/embed/b4eb8107755029f5c6e92f8cfcf14911"></iframe>'
    assert _MEDIA_EMBED.findall(document) == ["//services.err.ee/media/embed/b4eb8107755029f5c6e92f8cfcf14911"]


def test_etvsaated_fallback_uses_manifest_and_direct_vtt(monkeypatch) -> None:
    source_url = "https://www.err.ee/1610173927/example"
    block = "/media/videoBlock/2bcf0f7cc196c36275aae42df21a216a?contentId=1610173927&amp;photoId=3855547"
    article_page = f'<meta property="og:title" content="Näide"><div data-html-src="{block}"></div>'
    block_page = r'''
        {"src":{"dashNew":"\/\/vod.err.ee\/dash\/etvsaated\/2bcf0f7cc196c36275aae42df21a216a\/5\/v\/manifest.mpd"},
        "subtitles":[{"src":"https:\/\/www.err.ee\/subtitles\/file\/446623\/446623_VA.vtt"}]}
    '''

    def fake_download(url: str) -> str:
        if url == source_url:
            return article_page
        assert url == (
            "https://www.err.ee/media/videoBlock/2bcf0f7cc196c36275aae42df21a216a"
            "?contentId=1610173927&photoId=3855547"
        )
        return block_page

    monkeypatch.setattr(article, "_download_page", fake_download)
    items, versions, vtt_urls = resolve_err_article_sources(source_url)

    assert items[0].canonical_url == (
        "https://vod.err.ee/dash/etvsaated/2bcf0f7cc196c36275aae42df21a216a/5/v/manifest.mpd"
    )
    assert versions == {"2bcf0f7cc196c36275aae42df21a216a": "5"}
    assert vtt_urls == {
        "2bcf0f7cc196c36275aae42df21a216a": "https://www.err.ee/subtitles/file/446623/446623_VA.vtt"
    }


def test_existing_vod_fallback_remains_unchanged(monkeypatch) -> None:
    source_url = "https://www.err.ee/example"
    page = (
        '<meta property="og:title" content="Näide">'
        'https://vod.err.ee/dash/vod/b4eb8107755029f5c6e92f8cfcf14911/2/v/manifest.mpd'
    )
    monkeypatch.setattr(article, "_download_page", lambda url: page)

    items, versions, vtt_urls = resolve_err_article_sources(source_url)

    assert items[0].canonical_url == (
        "https://vod.err.ee/dash/vod/b4eb8107755029f5c6e92f8cfcf14911/2/v/manifest.mpd"
    )
    assert versions == {"b4eb8107755029f5c6e92f8cfcf14911": "2"}
    assert vtt_urls == {}


def test_existing_resolver_return_contract_is_unchanged(monkeypatch) -> None:
    source_url = "https://www.err.ee/example"
    page = "https://vod.err.ee/dash/vod/b4eb8107755029f5c6e92f8cfcf14911/2/v/manifest.mpd"
    monkeypatch.setattr(article, "_download_page", lambda url: page)

    items, versions = resolve_err_article(source_url)

    assert items[0].vod_id == "b4eb8107755029f5c6e92f8cfcf14911"
    assert versions == {"b4eb8107755029f5c6e92f8cfcf14911": "2"}
