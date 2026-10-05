from __future__ import annotations

import hashlib
import importlib.metadata
import json
import re
import shutil
import time
import wave
from collections import Counter
from pathlib import Path
from typing import Any

from err2text.config import AlignmentSettings, Settings
from err2text.errors import ExitCode, PipelineError
from err2text.media import download_audio, extract_audio_clip
from err2text.output import format_time, write_json

_WORD_RE = re.compile(r"[0-9A-Za-zÕÄÖÜŠŽõäöüšž]+")


def run_review(output_dir: Path, config: Settings, alignment: AlignmentSettings, case_file: Path) -> Path:
    """Align only explicit human-marked VTT cues; never rewrite base artifacts."""
    transcript = _load_json(output_dir / "transcript.json")
    speakers = _load_json(output_dir / "speakers.json")
    resolver = _load_json(output_dir / "resolver.json")
    cases = _load_cases(case_file)
    selected_media = resolver.get("selected_media")
    if not isinstance(selected_media, dict) or not selected_media.get("canonical_url"):
        raise PipelineError(ExitCode.ALIGNMENT_REVIEW_FAILED, "resolver.json has no canonical media URL for alignment review")

    review_dir = output_dir / "review" / "alignment" / case_file.stem
    if review_dir.exists() and any(review_dir.iterdir()):
        raise PipelineError(ExitCode.INVALID_ARGUMENT, "Alignment review directory already contains files", {"review_dir": str(review_dir)})
    by_id = {str(item.get("id")): item for item in _items(transcript.get("segments")) if item.get("id")}
    referenced = [str(item.get(key)) for item in cases for key in ("segment_id", "before_segment_id", "after_segment_id") if item.get(key)]
    missing = [segment_id for segment_id in referenced if segment_id not in by_id]
    if missing:
        raise PipelineError(ExitCode.INVALID_ARGUMENT, "Case file refers to unknown transcript segment", {"segment_ids": missing})

    review_dir.mkdir(parents=True, exist_ok=True)
    work_dir = config.work_root / "alignment-review" / _work_key(output_dir, transcript)
    audio_path = work_dir / "source.wav"
    started = time.monotonic()
    try:
        download_audio(str(selected_media["canonical_url"]), audio_path)
        model, processor = _load_model(alignment)
        _set_threads(alignment.cpu_threads)
        speaker_names = _speaker_names(transcript)
        ordered_segments = sorted(by_id.values(), key=lambda item: float(item["start"]))
        reviewed = [_review_item(case, by_id, ordered_segments, audio_path, work_dir, speakers, speaker_names, model, processor, alignment) for case in cases]
    except PipelineError:
        raise
    except Exception as error:
        raise PipelineError(
            ExitCode.ALIGNMENT_REVIEW_FAILED,
            "Alignment review failed",
            {"type": type(error).__name__, "message": str(error)[:1000]},
        ) from error
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    result = {
        "schema_version": "1.0",
        "status": "REVIEW_REQUIRED",
        "source_url": transcript.get("source_url"),
        "title": transcript.get("title"),
        "base_transcript_sha256": _json_digest(transcript),
        "speakers_sha256": speakers.get("sha256"),
        "case_file": str(case_file),
        "model": {
            "id": alignment.model,
            "revision": alignment.revision,
            "device": alignment.device,
            "cpu_threads": alignment.cpu_threads,
            "sample_rate": alignment.sample_rate,
            "transformers_version": importlib.metadata.version("transformers"),
        },
        "duration_seconds": round(time.monotonic() - started, 3),
        "cases": reviewed,
        "summary": _summary(reviewed),
        "decision": "human_review_required",
    }
    write_json(review_dir / "alignment_review.json", result)
    (review_dir / "alignment_review.md").write_text(_render_markdown(result), encoding="utf-8")
    return review_dir


def _review_item(case, by_id, ordered_segments, audio_path, work_dir, speakers, speaker_names, model, processor, settings):
    if case.get("verdict") != "clean_transition":
        return _review_case(case, by_id[str(case["segment_id"])], ordered_segments, audio_path, work_dir, speakers, speaker_names, model, processor, settings)
    results = []
    for key, expected in (("before_segment_id", case["before_speaker"]), ("after_segment_id", case["after_speaker"])):
        segment = by_id[str(case[key])]
        probe = {"before_separator_speaker": expected, "after_separator_speaker": expected, "separator_after_text": str(segment.get("text", ""))}
        results.append(_review_case(probe, segment, ordered_segments, audio_path, work_dir, speakers, speaker_names, model, processor, settings))
    return {"verdict": "clean_transition", "human_annotation": case, "segments": results,
            "internal_speaker_transitions": [_internal_transitions(item["alignment"]["words"]) for item in results], "decision": "human_review_required"}


def _internal_transitions(words):
    return [{"at": item["start"], "from": previous, "to": item.get("diarization_speaker_name"), "word": item["word"]}
            for previous, item in zip([None] + [word.get("diarization_speaker_name") for word in words[:-1]], words)
            if previous and item.get("diarization_speaker_name") and previous != item.get("diarization_speaker_name")]


def _summary(items):
    mixed = [item for item in items if item.get("human_annotation", {}).get("verdict") == "mixed_cue"]
    controls = [item for item in items if item.get("verdict") == "clean_transition"]
    false_positive_segments = {result["segment_id"] for item in controls for result, transitions in zip(item["segments"], item["internal_speaker_transitions"], strict=True) if transitions}
    return {"mixed_cue_count": len(mixed), "mixed_word_assignment_matches": sum(bool(item["alignment"].get("expected_sequence_matches")) for item in mixed),
            "clean_transition_count": len(controls), "clean_transition_with_internal_transition": len(false_positive_segments),
            "clean_transition_false_positive_segment_ids": sorted(false_positive_segments)}


def _load_model(settings: AlignmentSettings):
    try:
        import torch
        from transformers import AutoModelForCTC, AutoProcessor
    except Exception as error:
        raise PipelineError(ExitCode.ALIGNMENT_REVIEW_FAILED, "Could not initialize CTC alignment model", {"type": type(error).__name__}) from error
    processor = AutoProcessor.from_pretrained(settings.model, revision=settings.revision, cache_dir=str(settings.hf_home / "hub"))
    model = AutoModelForCTC.from_pretrained(settings.model, revision=settings.revision, cache_dir=str(settings.hf_home / "hub"))
    model.to(settings.device)
    model.eval()
    return model, processor


def _set_threads(threads: int) -> None:
    import torch
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)


def _review_case(
    case: dict[str, object], segment: dict[str, object], all_segments: list[dict[str, object]], audio_path: Path, work_dir: Path,
    speakers: dict[str, object], speaker_names: dict[str, str], model: Any, processor: Any,
    settings: AlignmentSettings,
) -> dict[str, object]:
    start, end = float(segment["start"]), float(segment["end"])
    context_start, context_end = max(0.0, start - 3.0), end + 3.0
    context_segments = [
        item for item in all_segments
        if float(item["end"]) > context_start and float(item["start"]) < context_end
    ]
    context_text = " ".join(str(item.get("text", "")) for item in context_segments)
    context_word_owners = [
        (str(item["id"]), sentence_end)
        for item in context_segments
        for _, sentence_end in _words_with_sentence_end(str(item.get("text", "")))
    ]
    clip_path = work_dir / "clips" / f"{segment['id']}.wav"
    extract_audio_clip(audio_path, clip_path, context_start, context_end)
    waveform, sample_rate = _read_mono_wav(clip_path)
    if sample_rate != settings.sample_rate:
        raise PipelineError(ExitCode.ALIGNMENT_REVIEW_FAILED, "Unexpected review WAV sample rate", {"actual": sample_rate, "expected": settings.sample_rate})
    words = _align_words(context_text, waveform, sample_rate, model, processor, settings.device)
    if len(words) != len(context_word_owners):
        raise PipelineError(ExitCode.ALIGNMENT_REVIEW_FAILED, "Aligned word count does not match context VTT words")
    for word, (owner, sentence_end) in zip(words, context_word_owners, strict=True):
        word["segment_id"] = owner
        word["sentence_end"] = sentence_end
        word["start"] = round(context_start + float(word["start"]), 3) if word["start"] is not None else None
        word["end"] = round(context_start + float(word["end"]), 3) if word["end"] is not None else None
        speaker_id = _speaker_for_interval(word["start"], word["end"], speakers)
        word["diarization_speaker_id"] = speaker_id
        word["diarization_speaker_name"] = speaker_names.get(speaker_id) if speaker_id else None

    cue_words = [word for word in words if word["segment_id"] == segment["id"]]
    separator_index = _separator_word_index(cue_words, str(case["separator_after_text"]))
    before = cue_words[separator_index] if separator_index is not None else None
    after = cue_words[separator_index + 1] if separator_index is not None and separator_index + 1 < len(cue_words) else None
    observed_before = before.get("diarization_speaker_name") if before else None
    observed_after = after.get("diarization_speaker_name") if after else None
    expected_before, expected_after = str(case["before_separator_speaker"]), str(case["after_separator_speaker"])
    return {
        "segment_id": segment["id"],
        "start": start,
        "end": end,
        "vtt_text": segment.get("text", ""),
        "human_annotation": case,
        "alignment": {
            "context_start": context_start,
            "context_end": context_end,
            "context_segment_ids": [item["id"] for item in context_segments],
            "word_count": len(cue_words),
            "words": cue_words,
            "separator_word_index": separator_index,
            "separator_after_word": before.get("word") if before else None,
            "next_word": after.get("word") if after else None,
            "proposed_boundary_seconds": after.get("start") if after else None,
            "before_separator_speaker": observed_before,
            "after_separator_speaker": observed_after,
            "expected_sequence_matches": observed_before == expected_before and observed_after == expected_after,
            "reason": _alignment_reason(cue_words, separator_index, expected_before, expected_after),
            "punctuation_baseline": _punctuation_baseline(cue_words, expected_before, expected_after),
        },
        "decision": "human_review_required",
    }


def _align_words(text: str, waveform, sample_rate: int, model: Any, processor: Any, device: str) -> list[dict[str, object]]:
    import torch
    lexical_words = _WORD_RE.findall(text)
    if not lexical_words:
        raise PipelineError(ExitCode.ALIGNMENT_REVIEW_FAILED, "VTT cue has no alignable words")
    vocab = processor.tokenizer.get_vocab()
    delimiter = processor.tokenizer.word_delimiter_token or "|"
    blank_id = processor.tokenizer.pad_token_id
    if blank_id is None or delimiter not in vocab:
        raise PipelineError(ExitCode.ALIGNMENT_REVIEW_FAILED, "CTC tokenizer has no usable blank or word delimiter")
    labels, owners = _labels_for_words(lexical_words, vocab, delimiter)
    if not labels:
        raise PipelineError(ExitCode.ALIGNMENT_REVIEW_FAILED, "VTT cue has no tokens in the CTC tokenizer vocabulary")
    inputs = processor(waveform, sampling_rate=sample_rate, return_tensors="pt")
    with torch.inference_mode():
        logits = model(inputs.input_values.to(device)).logits[0].cpu()
    aligned = _ctc_viterbi(logits, labels, int(blank_id))
    if not aligned:
        raise PipelineError(ExitCode.ALIGNMENT_REVIEW_FAILED, "CTC alignment did not produce target-token frames")
    duration = len(waveform) / sample_rate
    by_word: dict[int, list[tuple[int, float]]] = {}
    for label_index, frame, log_probability in aligned:
        owner = owners[label_index]
        if owner is not None:
            by_word.setdefault(owner, []).append((frame, log_probability))
    output = []
    total_frames = int(logits.shape[0])
    for index, word in enumerate(lexical_words):
        frames = by_word.get(index, [])
        if not frames:
            output.append({"word": word, "start": None, "end": None, "confidence": 0.0})
            continue
        first, last = min(item[0] for item in frames), max(item[0] for item in frames)
        # CTC path probabilities are necessarily very small for a large alphabet.
        # Store a local relative score instead: selected-token probability divided
        # by the most likely token probability in that frame.
        confidence = sum(float(torch.exp(torch.tensor(item[1]))) for item in frames) / len(frames)
        output.append({
            "word": word,
            "start": round(duration * first / total_frames, 3),
            "end": round(duration * (last + 1) / total_frames, 3),
            "confidence": round(confidence, 4),
        })
    return output


def _labels_for_words(words: list[str], vocab: dict[str, int], delimiter: str) -> tuple[list[int], list[int | None]]:
    labels: list[int] = []
    owners: list[int | None] = []
    for word_index, word in enumerate(words):
        for character in word.casefold():
            if character in vocab:
                labels.append(vocab[character])
                owners.append(word_index)
        if word_index < len(words) - 1:
            labels.append(vocab[delimiter])
            owners.append(None)
    return labels, owners


def _ctc_viterbi(logits, labels: list[int], blank_id: int) -> list[tuple[int, int, float]]:
    """Return (target-label index, frame, log probability relative to frame best)."""
    import torch
    emission = torch.log_softmax(logits, dim=-1)
    frames = int(emission.shape[0])
    extended: list[int] = [blank_id]
    for label in labels:
        extended.extend([label, blank_id])
    states = len(extended)
    neg_inf = float("-inf")
    previous = [neg_inf] * states
    previous[0] = float(emission[0, blank_id])
    if states > 1:
        previous[1] = float(emission[0, extended[1]])
    parents: list[list[int]] = [[-1] * states for _ in range(frames)]
    for frame in range(1, frames):
        current = [neg_inf] * states
        for state, token in enumerate(extended):
            options = [(previous[state], state)]
            if state >= 1:
                options.append((previous[state - 1], state - 1))
            if state >= 2 and state % 2 == 1 and token != extended[state - 2]:
                options.append((previous[state - 2], state - 2))
            best_score, best_state = max(options, key=lambda item: item[0])
            current[state] = best_score + float(emission[frame, token])
            parents[frame][state] = best_state
        previous = current
    state = states - 1 if previous[states - 1] >= previous[states - 2] else states - 2
    result: list[tuple[int, int, float]] = []
    for frame in range(frames - 1, -1, -1):
        if state % 2 == 1:
            label_index = (state - 1) // 2
            relative_log_probability = float(emission[frame, extended[state]] - torch.max(emission[frame]))
            result.append((label_index, frame, relative_log_probability))
        if frame:
            state = parents[frame][state]
    return list(reversed(result))


def _read_mono_wav(path: Path):
    import numpy as np
    with wave.open(str(path), "rb") as handle:
        if handle.getnchannels() != 1 or handle.getsampwidth() != 2:
            raise PipelineError(ExitCode.ALIGNMENT_REVIEW_FAILED, "Review WAV must be mono PCM16")
        sample_rate = handle.getframerate()
        samples = np.frombuffer(handle.readframes(handle.getnframes()), dtype="<i2").astype("float32") / 32768.0
    return samples, sample_rate


def _separator_word_index(words: list[dict[str, object]], separator: str) -> int | None:
    target = [item.casefold() for item in _WORD_RE.findall(separator)]
    observed = [str(item["word"]).casefold() for item in words]
    if not target:
        return None
    for start in range(len(observed) - len(target), -1, -1):
        if observed[start:start + len(target)] == target:
            return start + len(target) - 1
    return None


def _speaker_for_interval(start: float | None, end: float | None, speakers: dict[str, object]) -> str | None:
    if start is None or end is None:
        return None
    choices: dict[str, float] = {}
    for span in _items(speakers.get("segments")):
        speaker_id = span.get("speaker_id")
        if not speaker_id:
            continue
        overlap = max(0.0, min(end, float(span["end"])) - max(start, float(span["start"])))
        if overlap:
            choices[str(speaker_id)] = choices.get(str(speaker_id), 0.0) + overlap
    if not choices:
        return None
    winner = max(choices, key=choices.get)
    duration = max(0.001, end - start)
    return winner if choices[winner] / duration >= 0.5 else None


def _speaker_names(transcript: dict[str, object]) -> dict[str, str]:
    votes: dict[str, Counter[str]] = {}
    for segment in _items(transcript.get("segments")):
        speaker_id, name = segment.get("speaker_id"), segment.get("speaker_name")
        if speaker_id and isinstance(name, str) and name not in {"", "UNKNOWN"}:
            votes.setdefault(str(speaker_id), Counter())[name] += 1
    return {speaker_id: names.most_common(1)[0][0] for speaker_id, names in votes.items()}


def _alignment_reason(words: list[dict[str, object]], separator_index: int | None, expected_before: str, expected_after: str) -> str:
    if separator_index is None:
        return "separator_text_not_found_in_vtt_words"
    if separator_index + 1 >= len(words):
        return "separator_is_at_end_of_vtt_cue"
    before, after = words[separator_index], words[separator_index + 1]
    if before.get("start") is None or after.get("start") is None:
        return "one_or_more_boundary_words_unaligned"
    if before.get("diarization_speaker_name") == expected_before and after.get("diarization_speaker_name") == expected_after:
        return "expected_speaker_sequence_observed"
    return "pyannote_sequence_differs_from_human_reading_annotation"


def _punctuation_baseline(words: list[dict[str, object]], expected_before: str, expected_after: str) -> dict[str, object]:
    """Compare the word-level Pyannote transition to nearby sentence-ending words."""
    change_index = next(
        (index for index in range(1, len(words))
         if words[index - 1].get("diarization_speaker_name")
         and words[index].get("diarization_speaker_name") != words[index - 1].get("diarization_speaker_name")),
        None,
    )
    if change_index is None or words[change_index].get("start") is None:
        return {"status": "no_matching_pyannote_transition"}
    transition = float(words[change_index]["start"])
    candidates = [
        (index, word) for index, word in enumerate(words[:-1])
        if word.get("sentence_end") and word.get("end") is not None
        and abs(float(word["end"]) - transition) <= 1.5
    ]
    if not candidates:
        return {"status": "no_sentence_end_within_1_5_seconds", "pyannote_transition_seconds": transition}
    index, word = min(candidates, key=lambda item: abs(float(item[1]["end"]) - transition))
    return {
        "status": "candidate",
        "pyannote_transition_seconds": transition,
        "boundary_after_word": word["word"],
        "boundary_seconds": word["end"],
        "word_index": index,
    }


def _render_markdown(result: dict[str, object]) -> str:
    lines = [
        f"# Forced-alignmenti kontroll: {result.get('title') or 'ERR transkriptsioon'}",
        "",
        "> Katse kasutab muutmata ERR-i VTT teksti. Tulemus ei muuda põhi-transkriptsiooni automaatselt.",
        "",
    ]
    for item in _items(result.get("cases")):
        if item.get("verdict") == "clean_transition":
            annotation = item["human_annotation"]
            lines.extend([f"## Puhas kontrollüleminek · {annotation['before_segment_id']} → {annotation['after_segment_id']}", "",
                          f"Lugemiskonteksti märgendus (audiot pole kontrollitud): **{annotation['before_speaker']}** → **{annotation['after_speaker']}**.", "",
                          f"Cue-sisesed Pyannote'i üleminekud: `{len(item['internal_speaker_transitions'][0]) + len(item['internal_speaker_transitions'][1])}`.", ""])
            continue
        annotation = item["human_annotation"]
        alignment = item["alignment"]
        lines.extend([
            f"## {format_time(float(item['start']))}–{format_time(float(item['end']))} · {item['segment_id']}",
            "",
            f"VTT: {item['vtt_text']}",
            "",
            f"Lugemiskonteksti märgendus (audiot pole kontrollitud): **{annotation['before_separator_speaker']}** | **{annotation['after_separator_speaker']}** pärast teksti „{annotation['separator_after_text']}”",
            "",
            f"Joondatud piir: {format_time(float(alignment['proposed_boundary_seconds'])) if alignment['proposed_boundary_seconds'] is not None else 'leidmata'}; Pyannote enne/pärast: **{alignment['before_separator_speaker'] or '—'}** → **{alignment['after_separator_speaker'] or '—'}**.",
            "",
            f"Tulemus: `{alignment['reason']}`; automaatne muudatus: ei.",
            "",
            f"Kirjavahemärgi baseline: `{alignment['punctuation_baseline']['status']}`.",
            "",
            "| Sõna | Aeg | Joonduskindlus | Pyannote |",
            "|---|---:|---:|---|",
        ])
        for word in _items(alignment.get("words")):
            when = "—" if word.get("start") is None else f"{format_time(float(word['start']))}–{format_time(float(word['end']))}"
            lines.append(f"| {word['word']} | {when} | {word['confidence']} | {word.get('diarization_speaker_name') or word.get('diarization_speaker_id') or '—'} |")
        lines.append("")
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise PipelineError(ExitCode.ALIGNMENT_REVIEW_FAILED, "Required completed-run artifact is missing", {"path": str(path)})
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise PipelineError(ExitCode.ALIGNMENT_REVIEW_FAILED, "Could not parse completed-run artifact", {"path": str(path)}) from error
    if not isinstance(value, dict):
        raise PipelineError(ExitCode.ALIGNMENT_REVIEW_FAILED, "Completed-run artifact must be a JSON object", {"path": str(path)})
    return value


def _load_cases(path: Path) -> list[dict[str, object]]:
    data = _load_json(path)
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise PipelineError(ExitCode.INVALID_ARGUMENT, "Alignment case file must contain a non-empty cases array", {"path": str(path)})
    mixed_required = {"segment_id", "before_separator_speaker", "after_separator_speaker", "separator_after_text"}
    control_required = {"before_segment_id", "after_segment_id", "before_speaker", "after_speaker"}
    invalid = [index for index, item in enumerate(cases) if not isinstance(item, dict) or ((control_required if item.get("verdict") == "clean_transition" else mixed_required) - set(item))]
    if invalid:
        raise PipelineError(ExitCode.INVALID_ARGUMENT, "Alignment case is missing required fields", {"indexes": invalid})
    return [dict(item) for item in cases]


def _items(value: object) -> list[dict[str, object]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _words_with_sentence_end(text: str) -> list[tuple[str, bool]]:
    """Keep the punctuation fact while feeding only tokenizer-compatible words to CTC."""
    result: list[tuple[str, bool]] = []
    for raw in re.findall(r"\S+", text):
        words = _WORD_RE.findall(raw)
        for index, word in enumerate(words):
            result.append((word, index == len(words) - 1 and raw.rstrip().endswith((".", "?", "!"))))
    return result


def _work_key(output_dir: Path, transcript: dict[str, object]) -> str:
    return hashlib.sha256(f"{output_dir.resolve()}:{_json_digest(transcript)}".encode()).hexdigest()[:20]


def _json_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
