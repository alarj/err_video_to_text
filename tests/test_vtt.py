from err2text.subtitles.normalize import decode_vtt
from err2text.subtitles.parser import parse_vtt


def test_correct_estonian_utf8_is_unchanged() -> None:
    source = "WEBVTT\n\n00:00.000 --> 00:01.000\nJärgnevale õäöüšž\n".encode()
    assert decode_vtt(source) == source.decode()


def test_clear_mojibake_is_repaired() -> None:
    assert decode_vtt("JÃ¤rgnevale".encode()) == "Järgnevale"


def test_parser_handles_bom_crlf_note_tags_and_multiline_cues() -> None:
    document = "\ufeffWEBVTT\r\n\r\nNOTE ignore\r\nmetadata\r\n\r\n12\r\n00:01.000 --> 00:03.500 align:start\r\n<c.green>Tere</c>\r\nmaailm\r\n\r\n"
    cues = parse_vtt(document)
    assert len(cues) == 1
    assert cues[0].id == "12"
    assert cues[0].start == 1.0
    assert cues[0].end == 3.5
    assert cues[0].text == "Tere\nmaailm"
