"""Import a preserved Jutusta.ee transcript as an optional research draft.

The command is dry-run by default.  It never changes process state, review
candidates, the reviewed draft, or the finalization workflow.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import shutil
from typing import Any
import unicodedata


VERSION_TYPE = "JUTUSTA_EE_DRAFT"
COMPARISON_VERSION = "2.0"
BOUNDARY_TOLERANCE_SECONDS = 0.25

_FILLER_WORDS = {"ah", "jaa", "jah", "ka", "no", "noh", "siis"}
_NUMBER_UNITS = {
    "null": 0,
    "üks": 1, "ühe": 1, "üht": 1, "esimene": 1, "esimese": 1, "esimesel": 1,
    "kaks": 2, "kahe": 2, "kaht": 2, "teine": 2, "teise": 2, "teisel": 2,
    "kolm": 3, "kolme": 3, "kolmas": 3, "kolmanda": 3, "kolmandal": 3, "kolmandaks": 3,
    "neli": 4, "nelja": 4, "neljas": 4, "neljanda": 4, "neljandaks": 4,
    "viis": 5, "viie": 5, "viies": 5, "viienda": 5, "viiendaks": 5,
    "kuus": 6, "kuue": 6, "kuues": 6, "kuuenda": 6, "kuuendaks": 6,
    "seitse": 7, "seitsme": 7, "seitsmes": 7, "seitsmenda": 7, "seitsmendaks": 7,
    "kaheksa": 8, "kaheksas": 8, "kaheksanda": 8, "kaheksandaks": 8,
    "üheksa": 9, "üheksas": 9, "üheksanda": 9, "üheksandaks": 9,
}
_NUMBER_TENS_PREFIXES = {
    "küm": 10, "üheteist": 11, "kaheteist": 12, "kolmeteist": 13, "neliteist": 14,
    "viisteist": 15, "kuusteist": 16, "seitseteist": 17, "kaheksateist": 18, "üheksateist": 19,
    "kaheküm": 20, "kaksküm": 20, "kolmeküm": 30, "kolmküm": 30, "neliküm": 40, "viisküm": 50,
    "kuusküm": 60, "seitseküm": 70, "kaheksaküm": 80, "üheksaküm": 90,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a Jutusta.ee transcript without changing the main workflow")
    parser.add_argument("--process-id", type=int, required=True)
    parser.add_argument("--json", type=Path, required=True, dest="json_path")
    parser.add_argument("--text", type=Path, required=True, dest="text_path")
    parser.add_argument("--time-offset-seconds", type=float, default=0.0)
    parser.add_argument("--apply", action="store_true", help="write files and Oracle rows")
    args = parser.parse_args()

    from dotenv import load_dotenv
    from app.database.oracle import connection

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    payload = load_jutusta(args.json_path)
    with connection() as conn:
        context = load_process_context(conn, args.process_id)
        comparison = compare_transcripts(
            context["reference_segments"],
            payload,
            args.time_offset_seconds,
            context["candidate_segment_ids"],
            context["modified_source_segment_ids"],
            context["modified_reviewed_segment_ids"],
        )
        report = {
            "process_id": args.process_id,
            "version_type": VERSION_TYPE,
            "external_job_id": payload.get("job_id"),
            "duration_seconds": payload.get("duration_seconds"),
            "segment_count": len(payload["segments"]),
            "speaker_count": len({segment["speaker"] for segment in payload["segments"]}),
            "time_offset_seconds": args.time_offset_seconds,
            "comparison_summary": comparison["summary"],
            "applied": False,
        }
        if not args.apply:
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return
        created_paths: list[Path] = []
        try:
            version_id, reused, artifact_paths = apply_import(
                conn,
                args.process_id,
                args.json_path,
                args.text_path,
                payload,
                comparison,
                context,
                args.time_offset_seconds,
            )
            created_paths.extend(artifact_paths)
            conn.commit()
        except Exception:
            conn.rollback()
            for path in created_paths:
                path.unlink(missing_ok=True)
            raise
    report.update({"applied": True, "version_id": version_id, "reused": reused})
    print(json.dumps(report, ensure_ascii=False, indent=2))


def load_jutusta(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("segments"), list):
        raise ValueError("Jutusta JSON must contain a segments array")
    normalized = []
    for index, raw in enumerate(value["segments"], start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"Jutusta segment {index} is not an object")
        text = " ".join(str(raw.get("text") or "").split())
        speaker = " ".join(str(raw.get("speaker") or "UNKNOWN").split())
        start = float(raw["start"])
        end = float(raw["end"])
        if not text or end < start:
            raise ValueError(f"Invalid Jutusta segment {index}")
        if len(text.encode("utf-8")) > 4000:
            raise ValueError(f"Jutusta segment {index} exceeds Oracle VARCHAR2(4000)")
        words = []
        for word in raw.get("words") or []:
            words.append({
                "text": str(word.get("text") or "").strip(),
                "start": float(word["start"]),
                "end": float(word["end"]),
                "speaker": speaker,
            })
        normalized.append({"number": index, "start": start, "end": end, "speaker": speaker, "text": text, "words": words})
    return {**value, "segments": normalized}


def load_process_context(conn: Any, process_id: int) -> dict[str, Any]:
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM processes WHERE id = :id AND end_date IS NULL", {"id": process_id})
    process = cursor.fetchone()
    if process is None:
        raise ValueError(f"Process {process_id} does not exist")
    cursor.execute(
        """SELECT tp.speaker_label, p.name
             FROM transcript_versions tv
             JOIN transcript_participants tp
               ON tp.transcript_version_id = tv.id AND tp.end_date IS NULL
             JOIN participants_v p ON p.id = tp.participant_id
            WHERE tv.process_id = :process_id AND tv.version_type = 'REVIEWED_DRAFT'
              AND tv.end_date IS NULL AND tp.mapping_status = 'CONFIRMED'""",
        {"process_id": process_id},
    )
    reviewed_speaker_names = {str(label): str(name) for label, name in cursor.fetchall()}
    cursor.execute(
        """SELECT tv.id, tv.version_type, s.id, s.segment_number, s.start_second, s.end_second,
                  s.text, s.segment_type, s.source_segment_id,
                  tp.speaker_label, p.name, ss.start_second, ss.end_second
             FROM transcript_versions tv
             JOIN transcript_segments s ON s.transcript_version_id = tv.id AND s.end_date IS NULL
             LEFT JOIN transcript_segment_speakers ss ON ss.transcript_segment_id = s.id AND ss.end_date IS NULL
             LEFT JOIN transcript_participants tp ON tp.id = ss.transcript_participant_id AND tp.end_date IS NULL
             LEFT JOIN participants_v p ON p.id = tp.participant_id
            WHERE tv.process_id = :process_id
              AND tv.version_type IN ('AUTOMATIC_DRAFT', 'REVIEWED_DRAFT')
              AND tv.end_date IS NULL
            ORDER BY tv.version_type, s.segment_number, s.id, ss.id""",
        {"process_id": process_id},
    )
    grouped: dict[int, dict[str, Any]] = {}
    for row in cursor.fetchall():
        version_id, version_type, segment_id, number, start, end, text, segment_type, source_id, label, name, speaker_start, speaker_end = row
        item = grouped.setdefault(int(segment_id), {
            "version_id": int(version_id), "version_type": str(version_type), "segment_id": int(segment_id),
            "segment_number": int(number), "start": float(start), "end": float(end), "text": str(text),
            "segment_type": str(segment_type), "source_segment_id": int(source_id) if source_id is not None else None,
            "speaker_durations": defaultdict(float),
        })
        if label is not None:
            display = str(name or reviewed_speaker_names.get(str(label)) or label)
            item["speaker_durations"][display] += max(0.0, float(speaker_end) - float(speaker_start))
    reference_segments = []
    for item in grouped.values():
        durations = item.pop("speaker_durations")
        item["speaker"] = max(durations.items(), key=lambda pair: pair[1])[0] if durations else None
        reference_segments.append(item)
    reference_segments.sort(key=lambda item: (item["version_type"], item["segment_number"], item["segment_id"]))

    cursor.execute(
        """SELECT rc.transcript_segment_id
             FROM review_candidates rc
             JOIN transcript_segments s ON s.id = rc.transcript_segment_id
             JOIN transcript_versions tv ON tv.id = s.transcript_version_id
            WHERE tv.process_id = :process_id AND tv.version_type = 'AUTOMATIC_DRAFT'
              AND rc.end_date IS NULL AND s.end_date IS NULL AND tv.end_date IS NULL""",
        {"process_id": process_id},
    )
    candidate_ids = {int(row[0]) for row in cursor.fetchall()}
    cursor.execute(
        """SELECT s.id, s.source_segment_id
             FROM transcript_segment_modifications m
             JOIN transcript_segments s ON s.id = m.transcript_segment_id
             JOIN transcript_versions tv ON tv.id = s.transcript_version_id
            WHERE tv.process_id = :process_id AND tv.version_type = 'REVIEWED_DRAFT'
              AND m.end_date IS NULL AND s.end_date IS NULL AND tv.end_date IS NULL""",
        {"process_id": process_id},
    )
    modification_rows = cursor.fetchall()
    modified_reviewed_ids = {int(row[0]) for row in modification_rows}
    modified_source_ids = {int(row[1]) for row in modification_rows if row[1] is not None}

    cursor.execute(
        """SELECT a.path
             FROM transcript_versions tv
             JOIN transcript_artifacts ta ON ta.transcript_version_id = tv.id AND ta.end_date IS NULL
             JOIN artifacts a ON a.id = ta.artifact_id AND a.end_date IS NULL
            WHERE tv.process_id = :process_id AND tv.version_type = 'AUTOMATIC_DRAFT'
            ORDER BY CASE a.artifact_type WHEN 'AUTOMATIC_TRANSCRIPT_JSON' THEN 0 ELSE 1 END, a.id
            FETCH FIRST 1 ROW ONLY""",
        {"process_id": process_id},
    )
    artifact = cursor.fetchone()
    if artifact is None:
        raise ValueError("Automatic transcript artifact is missing")
    return {
        "process_status": str(process[0]),
        "reference_segments": reference_segments,
        "candidate_segment_ids": candidate_ids,
        "modified_source_segment_ids": modified_source_ids,
        "modified_reviewed_segment_ids": modified_reviewed_ids,
        "output_dir": Path(str(artifact[0])).resolve().parent,
    }


def compare_transcripts(
    reference_segments: list[dict[str, Any]],
    jutusta: dict[str, Any],
    offset: float,
    candidate_ids: set[int],
    modified_source_ids: set[int],
    modified_reviewed_ids: set[int],
) -> dict[str, Any]:
    words = [
        {**word, "start": word["start"] + offset, "end": word["end"] + offset}
        for segment in jutusta["segments"] for word in segment["words"] if word["text"]
    ]
    turns = [
        {"start": segment["start"] + offset, "end": segment["end"] + offset, "speaker": segment["speaker"]}
        for segment in jutusta["segments"]
    ]
    items = []
    for segment in reference_segments:
        # ERR inserts on-screen subtitle notices into the VTT. They are not
        # spoken audio and therefore have no valid counterpart in an ASR
        # transcript such as Jutusta.ee.
        if segment["segment_type"] == "SYSTEM_NOTICE":
            continue
        overlapping = [word for word in words if word["end"] > segment["start"] and word["start"] < segment["end"]]
        if not overlapping:
            nearby = [
                word for word in words
                if word["end"] > segment["start"] - BOUNDARY_TOLERANCE_SECONDS
                and word["start"] < segment["end"] + BOUNDARY_TOLERANCE_SECONDS
            ]
            reference = normalize_comparison_text(segment["text"])
            nearby_text = normalize_comparison_text(" ".join(word["text"] for word in nearby))
            if semantic_equivalent(reference, nearby_text):
                overlapping = nearby
        jutusta_text = " ".join(word["text"] for word in overlapping)
        left = normalize_comparison_text(segment["text"])
        right = normalize_comparison_text(jutusta_text)
        similarity = SequenceMatcher(None, left, right).ratio() if left and right else 0.0
        if not right:
            verdict = "UNALIGNED"
        elif semantic_equivalent(left, right, similarity):
            verdict = "SEMANTIC_MATCH"
        elif similarity >= 0.75 or left in right or right in left:
            verdict = "CLOSE"
        else:
            verdict = "DIFFERENT"
        speaker_durations: dict[str, float] = defaultdict(float)
        for turn in turns:
            overlap = max(0.0, min(segment["end"], turn["end"]) - max(segment["start"], turn["start"]))
            speaker_durations[turn["speaker"]] += overlap
        jutusta_speaker = max(speaker_durations.items(), key=lambda pair: pair[1])[0] if speaker_durations else None
        if not segment["speaker"] or not jutusta_speaker:
            speaker_verdict = "UNALIGNED"
        elif normalize_text(segment["speaker"]) == normalize_text(jutusta_speaker):
            speaker_verdict = "MATCH"
        else:
            speaker_verdict = "DIFFERENT"
        source_id = segment["source_segment_id"] or segment["segment_id"]
        if source_id in candidate_ids:
            scope = "CANDIDATE"
        elif source_id in modified_source_ids or segment["segment_id"] in modified_reviewed_ids:
            scope = "REVIEW_REACHABLE_NEIGHBOR"
        else:
            scope = "OUTSIDE_REVIEW_WORKBENCH"
        items.append({
            "version_type": segment["version_type"], "version_id": segment["version_id"],
            "segment_id": segment["segment_id"], "segment_number": segment["segment_number"],
            "source_segment_id": segment["source_segment_id"], "start_second": segment["start"],
            "end_second": segment["end"], "review_scope": scope,
            "reference_text": segment["text"], "jutusta_text": jutusta_text,
            "text_verdict": verdict, "text_similarity": round(similarity, 6),
            "reference_speaker": segment["speaker"], "jutusta_speaker": jutusta_speaker,
            "speaker_verdict": speaker_verdict,
        })
    summary: dict[str, Any] = {}
    for version_type in ("AUTOMATIC_DRAFT", "REVIEWED_DRAFT"):
        rows = [item for item in items if item["version_type"] == version_type]
        summary[version_type] = {
            "segments": len(rows),
            "text_verdicts": dict(Counter(item["text_verdict"] for item in rows)),
            "speaker_verdicts": dict(Counter(item["speaker_verdict"] for item in rows)),
            "differences_by_scope": dict(Counter(
                item["review_scope"] for item in rows if item["text_verdict"] == "DIFFERENT" or item["speaker_verdict"] == "DIFFERENT"
            )),
        }
    return {
        "schema_version": "1.0", "comparison_version": COMPARISON_VERSION,
        "time_offset_seconds": offset, "summary": summary, "items": items,
        "interpretation": "Technical alignment result; Jutusta.ee is not treated as ground truth.",
    }


def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return " ".join(re.sub(r"[^\wõäöüšž]+", " ", text, flags=re.UNICODE).split())


def normalize_comparison_text(value: object) -> str:
    """Normalize punctuation and equivalent numeric surface forms."""
    raw = unicodedata.normalize("NFKC", str(value or "")).lower()
    raw = re.sub(r"(\d+)\s*\.?\s*-\s*[a-zõäöüšž]+", r"\1", raw, flags=re.UNICODE)
    tokens = normalize_text(raw).split()
    result: list[str] = []
    index = 0
    while index < len(tokens):
        parsed = _parse_number(tokens, index)
        if parsed is None:
            result.append(tokens[index])
            index += 1
            continue
        number, consumed = parsed
        result.append(f"<num:{number}>")
        index += consumed
    return " ".join(result)


def semantic_equivalent(left: str, right: str, similarity: float | None = None) -> bool:
    if left == right:
        return True
    if similarity is None:
        similarity = SequenceMatcher(None, left, right).ratio() if left and right else 0.0
    if similarity >= 0.94:
        return True
    left_core = [token for token in left.split() if token not in _FILLER_WORDS]
    right_core = [token for token in right.split() if token not in _FILLER_WORDS]
    return bool(left_core) and left_core == right_core


def _parse_number(tokens: list[str], start: int) -> tuple[int, int] | None:
    token = tokens[start]
    digit = re.fullmatch(r"(\d+)(?:\w+)?", token)
    if digit:
        return int(digit.group(1)), 1

    if (_number_word_value(token) is None
            and not token.startswith(("sada", "saja", "tuhat", "tuhande"))):
        return None
    index = start
    total = 0
    current = 0
    consumed_component = False
    while index < len(tokens):
        word = tokens[index]
        value = _number_word_value(word)
        if value is not None:
            if value >= 10:
                if current == 0:
                    current = value
                elif current >= 100 and current % 100 == 0:
                    current += value
                else:
                    break
            else:
                if current == 0:
                    current = value
                elif current >= 10 and current % 10 == 0:
                    current += value
                else:
                    break
            consumed_component = True
            index += 1
            continue
        if word.startswith("sada") or word.startswith("saja"):
            current = (current or 1) * 100
            consumed_component = True
            index += 1
            continue
        if word.startswith("tuhat") or word.startswith("tuhande"):
            total += (current or 1) * 1000
            current = 0
            consumed_component = True
            index += 1
            continue
        break
    if not consumed_component:
        return None
    return total + current, index - start


def _number_word_value(word: str) -> int | None:
    if word in _NUMBER_UNITS:
        return _NUMBER_UNITS[word]
    for prefix, value in sorted(_NUMBER_TENS_PREFIXES.items(), key=lambda item: len(item[0]), reverse=True):
        if word.startswith(prefix):
            return value
    return None


def render_transcript_markdown(jutusta: dict[str, Any], offset: float) -> bytes:
    lines = ["# Transkriptsioon (Jutusta.ee)", ""]
    for segment in jutusta["segments"]:
        lines.append(f"*{format_time(segment['start'] + offset)}* **{segment['speaker']}** {segment['text']}")
        lines.append("")
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def render_comparison_markdown(comparison: dict[str, Any]) -> bytes:
    lines = ["# Jutusta.ee transkriptsiooni võrdlus", "", "See on automaatne tehniline võrdlus, mitte uus inimese referentsotsus.", ""]
    labels = {"AUTOMATIC_DRAFT": "Automaatne transkriptsioon", "REVIEWED_DRAFT": "Inimese ülevaadatud transkriptsioon"}
    for version_type, label in labels.items():
        summary = comparison["summary"].get(version_type, {})
        lines.extend([
            f"## {label}", "",
            f"Segmente: {summary.get('segments', 0)}", "",
            f"Tekstivõrdlus: `{json.dumps(summary.get('text_verdicts', {}), ensure_ascii=False)}`", "",
            f"Kõnelejate võrdlus: `{json.dumps(summary.get('speaker_verdicts', {}), ensure_ascii=False)}`", "",
            f"Erinevused ülevaatuse ulatuse järgi: `{json.dumps(summary.get('differences_by_scope', {}), ensure_ascii=False)}`", "",
            "### Erinevad või joondamata segmendid", "",
        ])
        rows = [item for item in comparison["items"] if item["version_type"] == version_type and (item["text_verdict"] in {"DIFFERENT", "UNALIGNED"} or item["speaker_verdict"] == "DIFFERENT")]
        for item in rows:
            lines.extend([
                f"#### Segment {item['segment_number']} · {format_time(item['start_second'])} · {item['review_scope']}", "",
                f"- Tekst: `{item['text_verdict']}`, sarnasus {item['text_similarity']:.3f}",
                f"- Kõneleja: `{item['speaker_verdict']}` · `{item['reference_speaker'] or '—'}` / `{item['jutusta_speaker'] or '—'}`",
                f"- Võrdlustekst: {item['reference_text'].replace(chr(10), ' ')}",
                f"- Jutusta.ee: {item['jutusta_text'] or '—'}", "",
            ])
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def apply_import(
    conn: Any,
    process_id: int,
    json_source: Path,
    text_source: Path,
    payload: dict[str, Any],
    comparison: dict[str, Any],
    context: dict[str, Any],
    offset: float,
) -> tuple[int, bool, list[Path]]:
    cursor = conn.cursor()
    cursor.execute(
        """SELECT id FROM transcript_versions
            WHERE process_id = :process_id AND version_type = :version_type AND end_date IS NULL
            ORDER BY version_number DESC FETCH FIRST 1 ROW ONLY""",
        {"process_id": process_id, "version_type": VERSION_TYPE},
    )
    existing = cursor.fetchone()
    if existing is not None:
        version_id = int(existing[0])
        refresh_comparison_artifacts(cursor, version_id, comparison)
        return version_id, True, []

    target_dir = context["output_dir"] / "review" / "jutusta-ee"
    target_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "source_json": target_dir / "jutusta-ee-source.json",
        "source_text": target_dir / "jutusta-ee-source.txt",
        "transcript_md": target_dir / "jutusta-ee-transcript.md",
        "comparison_json": target_dir / "jutusta-ee-comparison.json",
        "comparison_md": target_dir / "jutusta-ee-comparison.md",
        "metadata_json": target_dir / "jutusta-ee-run-metadata.json",
    }
    created_paths: list[Path] = []
    copy_file(json_source, paths["source_json"]); created_paths.append(paths["source_json"])
    copy_file(text_source, paths["source_text"]); created_paths.append(paths["source_text"])
    paths["transcript_md"].write_bytes(render_transcript_markdown(payload, offset)); created_paths.append(paths["transcript_md"])
    paths["comparison_json"].write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); created_paths.append(paths["comparison_json"])
    paths["comparison_md"].write_bytes(render_comparison_markdown(comparison)); created_paths.append(paths["comparison_md"])
    metadata = {
        "schema_version": "1.0", "provider": "Jutusta.ee", "external_job_id": payload.get("job_id"),
        "process_id": process_id, "version_type": VERSION_TYPE, "time_offset_seconds": offset,
        "comparison_version": COMPARISON_VERSION, "source_json_sha256": file_sha256(paths["source_json"]),
        "source_text_sha256": file_sha256(paths["source_text"]),
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    paths["metadata_json"].write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); created_paths.append(paths["metadata_json"])

    cursor.execute("SELECT NVL(MAX(version_number), 0) + 1 FROM transcript_versions WHERE process_id = :id", {"id": process_id})
    version_number = int(cursor.fetchone()[0])
    version_var = cursor.var(int)
    cursor.execute(
        """INSERT INTO transcript_versions
               (process_id, activity_id, version_number, version_type, status)
           VALUES (:process_id, NULL, :version_number, :version_type, 'DRAFT')
           RETURNING id INTO :version_id""",
        {"process_id": process_id, "version_number": version_number, "version_type": VERSION_TYPE, "version_id": version_var},
    )
    version_id = int(version_var.getvalue()[0])
    participant_ids: dict[str, int] = {}
    for speaker in sorted({segment["speaker"] for segment in payload["segments"]}):
        participant_var = cursor.var(int)
        cursor.execute(
            """INSERT INTO transcript_participants
                   (transcript_version_id, speaker_label, participant_id, role, mapping_status)
               VALUES (:version_id, :speaker, NULL, NULL, 'UNCONFIRMED')
               RETURNING id INTO :participant_id""",
            {"version_id": version_id, "speaker": speaker, "participant_id": participant_var},
        )
        participant_ids[speaker] = int(participant_var.getvalue()[0])
    for segment in payload["segments"]:
        segment_var = cursor.var(int)
        start = segment["start"] + offset
        end = segment["end"] + offset
        cursor.execute(
            """INSERT INTO transcript_segments
                   (transcript_version_id, segment_number, start_second, end_second, text, segment_type, source_segment_id)
               VALUES (:version_id, :segment_number, :start_second, :end_second, :text, 'SPEECH', NULL)
               RETURNING id INTO :segment_id""",
            {"version_id": version_id, "segment_number": segment["number"], "start_second": start,
             "end_second": end, "text": segment["text"], "segment_id": segment_var},
        )
        cursor.execute(
            """INSERT INTO transcript_segment_speakers
                   (transcript_segment_id, transcript_participant_id, start_second, end_second, confidence)
               VALUES (:segment_id, :participant_id, :start_second, :end_second, 1)""",
            {"segment_id": int(segment_var.getvalue()[0]), "participant_id": participant_ids[segment["speaker"]],
             "start_second": start, "end_second": end},
        )
    artifact_types = {
        "source_json": ("JUTUSTA_EE_SOURCE_JSON", "application/json"),
        "source_text": ("JUTUSTA_EE_SOURCE_TEXT", "text/plain"),
        "transcript_md": ("JUTUSTA_EE_TRANSCRIPT_MARKDOWN", "text/markdown"),
        "comparison_json": ("JUTUSTA_EE_COMPARISON_JSON", "application/json"),
        "comparison_md": ("JUTUSTA_EE_COMPARISON_MARKDOWN", "text/markdown"),
        "metadata_json": ("JUTUSTA_EE_RUN_METADATA_JSON", "application/json"),
    }
    for key, path in paths.items():
        artifact_type, content_type = artifact_types[key]
        artifact_var = cursor.var(int)
        cursor.execute(
            """INSERT INTO artifacts (artifact_type, path, content_type, size_byte, sha256)
               VALUES (:artifact_type, :path, :content_type, :size_byte, :sha256)
               RETURNING id INTO :artifact_id""",
            {"artifact_type": artifact_type, "path": str(path), "content_type": content_type,
             "size_byte": path.stat().st_size, "sha256": file_sha256(path), "artifact_id": artifact_var},
        )
        cursor.execute(
            "INSERT INTO transcript_artifacts (transcript_version_id, artifact_id) VALUES (:version_id, :artifact_id)",
            {"version_id": version_id, "artifact_id": int(artifact_var.getvalue()[0])},
        )
    return version_id, False, created_paths


def refresh_comparison_artifacts(cursor: Any, version_id: int, comparison: dict[str, Any]) -> None:
    cursor.execute(
        """SELECT a.id, a.artifact_type, a.path
             FROM transcript_artifacts ta
             JOIN artifacts a ON a.id = ta.artifact_id
            WHERE ta.transcript_version_id = :version_id
              AND ta.end_date IS NULL AND a.end_date IS NULL
              AND a.artifact_type IN (
                  'JUTUSTA_EE_COMPARISON_JSON',
                  'JUTUSTA_EE_COMPARISON_MARKDOWN',
                  'JUTUSTA_EE_RUN_METADATA_JSON'
              )""",
        {"version_id": version_id},
    )
    artifacts = {
        str(artifact_type): (int(artifact_id), Path(str(path)))
        for artifact_id, artifact_type, path in cursor.fetchall()
    }
    required = {
        "JUTUSTA_EE_COMPARISON_JSON",
        "JUTUSTA_EE_COMPARISON_MARKDOWN",
        "JUTUSTA_EE_RUN_METADATA_JSON",
    }
    if set(artifacts) != required:
        raise ValueError("Existing Jutusta.ee draft does not have all refreshable artifacts")

    json_id, json_path = artifacts["JUTUSTA_EE_COMPARISON_JSON"]
    markdown_id, markdown_path = artifacts["JUTUSTA_EE_COMPARISON_MARKDOWN"]
    metadata_id, metadata_path = artifacts["JUTUSTA_EE_RUN_METADATA_JSON"]
    json_path.write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_bytes(render_comparison_markdown(comparison))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["comparison_version"] = COMPARISON_VERSION
    metadata["comparison_updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for artifact_id, path in ((json_id, json_path), (markdown_id, markdown_path), (metadata_id, metadata_path)):
        cursor.execute(
            """UPDATE artifacts
                  SET size_byte = :size_byte, sha256 = :sha256, last_updated = SYSTIMESTAMP
                WHERE id = :artifact_id AND end_date IS NULL""",
            {"size_byte": path.stat().st_size, "sha256": file_sha256(path), "artifact_id": artifact_id},
        )


def copy_file(source: Path, target: Path) -> None:
    if source.resolve() == target.resolve():
        return
    shutil.copyfile(source, target)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def format_time(value: float) -> str:
    seconds = max(0, int(value))
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"


if __name__ == "__main__":
    main()
