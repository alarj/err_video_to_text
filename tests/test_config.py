from pathlib import Path

import pytest

from err2text.config import Settings, ensure_external_output


def test_output_inside_checkout_is_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    settings = Settings(repo, tmp_path / "runtime", 3)
    with pytest.raises(ValueError, match="outside"):
        ensure_external_output(repo / "outputs" / "job", settings)


def test_output_outside_checkout_is_allowed(tmp_path: Path) -> None:
    settings = Settings(tmp_path / "repo", tmp_path / "runtime", 3)
    assert ensure_external_output(tmp_path / "outputs" / "job", settings) == (tmp_path / "outputs" / "job").resolve()
