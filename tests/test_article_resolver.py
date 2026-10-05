from err2text.resolver.article import _MEDIA_EMBED, _VIDEO_BLOCK, vtt_url_for
from err2text.models import MediaItem


def test_vtt_url_uses_discovered_vod_id_and_version() -> None:
    item = MediaItem(index=1, vod_id="b4eb8107755029f5c6e92f8cfcf14911")
    assert vtt_url_for(item, "2") == "https://vod.err.ee/dash/vod/b4eb8107755029f5c6e92f8cfcf14911/2/v/sub-f4.vtt"


def test_article_video_block_reference_is_detected() -> None:
    document = '<div data-html-src="/media/videoBlock/b4eb8107755029f5c6e92f8cfcf14911"></div>'
    assert _VIDEO_BLOCK.findall(document) == ["/media/videoBlock/b4eb8107755029f5c6e92f8cfcf14911"]


def test_article_media_embed_reference_is_detected() -> None:
    document = '<iframe src="//services.err.ee/media/embed/b4eb8107755029f5c6e92f8cfcf14911"></iframe>'
    assert _MEDIA_EMBED.findall(document) == ["//services.err.ee/media/embed/b4eb8107755029f5c6e92f8cfcf14911"]
