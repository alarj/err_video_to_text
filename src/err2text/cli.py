from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from err2text.config import ensure_external_output, settings
from err2text.errors import ExitCode, PipelineError
from err2text.models import RunContext
from err2text.names.apply import apply_names, load_json
from err2text.output import write_json, write_markdown_records
from err2text.pipeline import process


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="process.py")
    sub = result.add_subparsers(dest="command")
    run = sub.add_parser("process", help="resolve, diarize and merge an ERR URL")
    run.add_argument("url")
    run.add_argument("--output-dir", required=True)
    run.add_argument("--video-index", type=int)
    run.add_argument("--speakers-map")
    run.add_argument("--time-offset", type=float, default=0.0)
    run.add_argument("--min-speakers", type=int)
    run.add_argument("--max-speakers", type=int)
    run.add_argument("--no-cache", action="store_true")
    run.add_argument("--keep-audio", action="store_true")
    names = sub.add_parser("apply-names", help="apply a verified manual speaker map")
    names.add_argument("--output-dir", required=True)
    names.add_argument("--speakers-map", required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    if raw and raw[0] not in {"process", "apply-names", "-h", "--help"}:
        raw.insert(0, "process")
    args = parser().parse_args(raw)
    if not getattr(args, "command", None):
        parser().print_help()
        return ExitCode.INVALID_ARGUMENT
    config = settings()
    try:
        output_dir = ensure_external_output(Path(args.output_dir), config)
        if args.command == "apply-names":
            transcript_path, speakers_path = output_dir / "transcript.json", output_dir / "speakers.json"
            transcript = apply_names(load_json(transcript_path), load_json(speakers_path), load_json(Path(args.speakers_map)))
            write_json(transcript_path, transcript)
            markdown = next(output_dir.glob("*-transcript.md"), output_dir / "transcript.md")
            write_markdown_records(markdown, str(transcript.get("title") or "ERR transkriptsioon"), transcript.get("segments", []))
            print(str(output_dir))
            return ExitCode.SUCCESS
        if args.min_speakers and args.max_speakers and args.min_speakers > args.max_speakers:
            raise PipelineError(ExitCode.INVALID_ARGUMENT, "--min-speakers cannot exceed --max-speakers")
        result = process(RunContext(source_url=args.url, output_dir=str(output_dir), time_offset_seconds=args.time_offset,
                                   min_speakers=args.min_speakers, max_speakers=args.max_speakers,
                                   no_cache=args.no_cache, keep_audio=args.keep_audio), config, args.video_index)
        if args.speakers_map:
            transcript_path, speakers_path = result / "transcript.json", result / "speakers.json"
            transcript = apply_names(load_json(transcript_path), load_json(speakers_path), load_json(Path(args.speakers_map)))
            write_json(transcript_path, transcript)
            markdown = next(result.glob("*-transcript.md"), result / "transcript.md")
            write_markdown_records(markdown, str(transcript.get("title") or "ERR transkriptsioon"), transcript.get("segments", []))
        print(str(result))
        return ExitCode.SUCCESS
    except ValueError as error:
        problem = PipelineError(ExitCode.INVALID_ARGUMENT, str(error))
    except PipelineError as error:
        problem = error
    print(json.dumps(problem.as_json(), ensure_ascii=False), file=sys.stderr)
    return int(problem.code)
