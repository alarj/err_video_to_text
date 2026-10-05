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


@dataclass(frozen=True)
class WhisperSettings:
    """Explicit configuration for the optional Whisper review worker."""

    model: str
    revision: str
    device: str
    compute_type: str
    language: str
    cpu_threads: int
    context_seconds: float
    short_segment_seconds: float
    max_candidates: int
    hf_home: Path


@dataclass(frozen=True)
class AlignmentSettings:
    """Explicit configuration for the VTT forced-alignment spike worker."""

    model: str
    revision: str
    device: str
    cpu_threads: int
    sample_rate: int
    hf_home: Path


def settings() -> Settings:
    repo_root = Path(__file__).resolve().parents[2]
    runtime_root = Path(os.environ.get("ERR2TEXT_RUNTIME_ROOT", "/srv/err2text")).resolve()
    threads = int(os.environ.get("ERR2TEXT_PYTORCH_THREADS", "3"))
    return Settings(repo_root=repo_root, runtime_root=runtime_root, torch_threads=max(1, threads))


def whisper_settings() -> WhisperSettings:
    """Load review-worker settings without silently selecting a model or limits."""
    required = (
        "WHISPER_MODEL",
        "WHISPER_MODEL_REVISION",
        "WHISPER_DEVICE",
        "WHISPER_COMPUTE_TYPE",
        "WHISPER_LANGUAGE",
        "WHISPER_CPU_THREADS",
        "WHISPER_REVIEW_CONTEXT_SECONDS",
        "WHISPER_REVIEW_SHORT_SEGMENT_SECONDS",
        "WHISPER_REVIEW_MAX_CANDIDATES",
        "HF_HOME",
    )
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise ValueError(f"Missing Whisper review configuration: {', '.join(missing)}")
    return WhisperSettings(
        model=os.environ["WHISPER_MODEL"],
        revision=os.environ["WHISPER_MODEL_REVISION"],
        device=os.environ["WHISPER_DEVICE"],
        compute_type=os.environ["WHISPER_COMPUTE_TYPE"],
        language=os.environ["WHISPER_LANGUAGE"],
        cpu_threads=max(1, int(os.environ["WHISPER_CPU_THREADS"])),
        context_seconds=max(0.0, float(os.environ["WHISPER_REVIEW_CONTEXT_SECONDS"])),
        short_segment_seconds=max(0.0, float(os.environ["WHISPER_REVIEW_SHORT_SEGMENT_SECONDS"])),
        max_candidates=max(1, int(os.environ["WHISPER_REVIEW_MAX_CANDIDATES"])),
        hf_home=Path(os.environ["HF_HOME"]).resolve(),
    )


def alignment_settings() -> AlignmentSettings:
    """Load forced-alignment settings without a hidden model fallback."""
    required = (
        "ALIGNMENT_MODEL",
        "ALIGNMENT_MODEL_REVISION",
        "ALIGNMENT_DEVICE",
        "ALIGNMENT_CPU_THREADS",
        "ALIGNMENT_SAMPLE_RATE",
        "HF_HOME",
    )
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise ValueError(f"Missing alignment review configuration: {', '.join(missing)}")
    return AlignmentSettings(
        model=os.environ["ALIGNMENT_MODEL"],
        revision=os.environ["ALIGNMENT_MODEL_REVISION"],
        device=os.environ["ALIGNMENT_DEVICE"],
        cpu_threads=max(1, int(os.environ["ALIGNMENT_CPU_THREADS"])),
        sample_rate=max(1, int(os.environ["ALIGNMENT_SAMPLE_RATE"])),
        hf_home=Path(os.environ["HF_HOME"]).resolve(),
    )


def ensure_external_output(output_dir: Path, config: Settings) -> Path:
    resolved = output_dir.expanduser().resolve()
    try:
        resolved.relative_to(config.repo_root)
    except ValueError:
        return resolved
    raise ValueError("--output-dir must be outside the project checkout")
