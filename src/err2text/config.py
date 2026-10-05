from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    runtime_root: Path
    torch_threads: int

    @property
    def cache_root(self) -> Path:
        return self.runtime_root / "cache"

    @property
    def work_root(self) -> Path:
        return self.runtime_root / "work"


def settings() -> Settings:
    repo_root = Path(__file__).resolve().parents[2]
    runtime_root = Path(os.environ.get("ERR2TEXT_RUNTIME_ROOT", "/srv/err2text")).resolve()
    threads = int(os.environ.get("ERR2TEXT_PYTORCH_THREADS", "3"))
    return Settings(repo_root=repo_root, runtime_root=runtime_root, torch_threads=max(1, threads))


def ensure_external_output(output_dir: Path, config: Settings) -> Path:
    resolved = output_dir.expanduser().resolve()
    try:
        resolved.relative_to(config.repo_root)
    except ValueError:
        return resolved
    raise ValueError("--output-dir must be outside the project checkout")
