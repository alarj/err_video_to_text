from __future__ import annotations


def decode_vtt(raw: bytes) -> str:
    """Decode UTF-8 explicitly and repair only clear double-decoding mojibake."""
    text = raw.decode("utf-8-sig", errors="strict")
    if not _looks_like_utf8_mojibake(text):
        return text
    try:
        candidate = text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    return candidate if _mojibake_score(candidate) < _mojibake_score(text) else text


def _looks_like_utf8_mojibake(text: str) -> bool:
    return any(marker in text for marker in ("Ã", "Â", "â€", "ðŸ"))


def _mojibake_score(text: str) -> int:
    return sum(text.count(marker) for marker in ("Ã", "Â", "â€", "ðŸ"))
