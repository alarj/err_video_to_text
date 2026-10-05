from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from err2text.config import alignment_settings, ensure_external_output, settings, whisper_settings
from err2text.errors import ExitCode, PipelineError
from err2text.models import RunContext
from err2text.names.apply import apply_names, load_json
from err2text.output import write_json, write_markdown_records


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
    review = sub.add_parser("whisper-review", help="review selected completed-run segments with faster-whisper")
    review.add_argument("--output-dir", required=True)
    review.add_argument("--candidate-file", help="optional JSON file with manually selected candidate time ranges")
    alignment = sub.add_parser("alignment-review", help="align manually marked VTT cues to audio without changing the transcript")
    alignment.add_argument("--output-dir", required=True)
    alignment.add_argument("--case-file", required=True, help="JSON file with manually read mixed-cue cases")
    sentence = sub.add_parser("sentence-boundary-review", help="evaluate a model-free sentence-boundary baseline without changing the transcript")
    sentence.add_argument("--output-dir", required=True)
    sentence.add_argument("--case-file", required=True, help="JSON file with manually read mixed-cue cases")
    return result


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    if raw and raw[0] not in {"process", "apply-names", "whisper-review", "alignment-review", "sentence-boundary-review", "-h", "--help"}:
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
        if args.command == "whisper-review":
            from err2text.whisper_review.runner import run_review
            candidate_path = Path(args.candidate_file).expanduser().resolve() if args.candidate_file else None
            result = run_review(output_dir, config, whisper_settings(), candidate_path)
            print(str(result))
            return ExitCode.SUCCESS
        if args.command == "alignment-review":
            from err2text.alignment_review.runner import run_review
            case_path = Path(args.case_file).expanduser().resolve()
            result = run_review(output_dir, config, alignment_settings(), case_path)
            print(str(result))
            return ExitCode.SUCCESS
        if args.command == "sentence-boundary-review":
            from err2text.sentence_boundary_review.runner import run_review
            case_path = Path(args.case_file).expanduser().resolve()
            result = run_review(output_dir, case_path)
            print(str(result))
            return ExitCode.SUCCESS
        if args.min_speakers and args.max_speakers and args.min_speakers > args.max_speakers:
            raise PipelineError(ExitCode.INVALID_ARGUMENT, "--min-speakers cannot exceed --max-speakers")
        from err2text.pipeline import process
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
