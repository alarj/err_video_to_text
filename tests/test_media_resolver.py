from err2text.media import err_vod_items_from_metadata


def test_err_vod_identity_is_extracted_from_ytdlp_format_url() -> None:
    metadata = {"title": "Näide", "formats": [{"url": "http://vod.err.ee/hls/vod/b4eb8107755029f5c6e92f8cfcf14911/2/v/nosub/master.m3u8"}]}
    items, versions = err_vod_items_from_metadata(metadata)
    assert items[0].vod_id == "b4eb8107755029f5c6e92f8cfcf14911"
    assert items[0].canonical_url == "https://vod.err.ee/hls/vod/b4eb8107755029f5c6e92f8cfcf14911/2/v/nosub/master.m3u8"
    assert versions == {"b4eb8107755029f5c6e92f8cfcf14911": "2"}
