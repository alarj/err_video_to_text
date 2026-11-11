#!/usr/bin/env python3
"""Summarise raw diarization candidate density by show speaker count.

The query is read-only.  It deliberately does not inspect candidate status,
decision, or any later human correction: every active candidate belonging to
the active AUTOMATIC_DRAFT transcript is counted.
"""

from __future__ import annotations

import json
import statistics
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "docs/kursusetoo/diariseerimise_kandidaatide_tihedus.md"

REMOTE = r'''
import hashlib, json
from pathlib import Path
from app.database.oracle import connection

result = {"candidates": [], "artifacts": {}}
with connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SET TRANSACTION READ ONLY")
        cur.execute("""SELECT tv.process_id, rc.id
                       FROM review_candidates rc
                       JOIN transcript_segments s ON s.id = rc.transcript_segment_id
                       JOIN transcript_versions tv ON tv.id = s.transcript_version_id
                       WHERE tv.version_type = 'AUTOMATIC_DRAFT'
                         AND tv.end_date IS NULL
                         AND s.end_date IS NULL
                         AND rc.end_date IS NULL""")
        result["candidates"] = cur.fetchall()
        cur.execute("""SELECT tv.process_id, a.artifact_type, a.path
                       FROM transcript_versions tv
                       JOIN transcript_artifacts ta ON ta.transcript_version_id = tv.id
                       JOIN artifacts a ON a.id = ta.artifact_id
                       WHERE tv.version_type = 'AUTOMATIC_DRAFT'
                         AND tv.end_date IS NULL
                         AND ta.end_date IS NULL
                         AND a.end_date IS NULL
                         AND a.artifact_type IN ('DIARIZATION_JSON', 'AUTOMATIC_TRANSCRIPT_JSON')""")
        for process_id, artifact_type, path in cur.fetchall():
            data = Path(path).read_bytes()
            entry = result["artifacts"].setdefault(str(process_id), {})
            if artifact_type in entry:
                raise RuntimeError((process_id, artifact_type, "duplicate active artifact"))
            entry[artifact_type] = {
                "sha256": hashlib.sha256(data).hexdigest(),
                "data": json.loads(data),
            }
print(json.dumps(result))
'''


def time_bounds(segments: list[dict]) -> tuple[float, float]:
    starts = [float(segment["start"]) for segment in segments]
    ends = [float(segment["end"]) for segment in segments]
    if not starts or min(starts) < 0 or max(ends) <= min(starts):
        raise ValueError("invalid or empty timed segments")
    return min(starts), max(ends)


def speaker_bucket(speaker_count: int) -> str:
    return "2" if speaker_count == 2 else "3" if speaker_count == 3 else "4+"


def rounded(value: float) -> str:
    return f"{value:.3f}".replace(".", ",")


def main() -> None:
    snapshot = json.loads(subprocess.run(
        ["docker", "compose", "exec", "-T", "api", "python", "-c", REMOTE],
        text=True,
        capture_output=True,
        check=True,
        cwd=ROOT,
    ).stdout)

    candidate_counts = Counter(int(process_id) for process_id, _ in snapshot["candidates"])
    rows: list[dict[str, object]] = []
    missing: list[tuple[int, str]] = []
    for process_id, candidate_count in sorted(candidate_counts.items()):
        artifacts = snapshot["artifacts"].get(str(process_id), {})
        required = {"DIARIZATION_JSON", "AUTOMATIC_TRANSCRIPT_JSON"}
        absent = required - set(artifacts)
        if absent:
            missing.append((process_id, ", ".join(sorted(absent))))
            continue

        diarization = artifacts["DIARIZATION_JSON"]["data"]["segments"]
        transcript = artifacts["AUTOMATIC_TRANSCRIPT_JSON"]["data"]["segments"]
        speaker_count = len({segment["speaker_id"] for segment in diarization})
        if speaker_count < 2:
            raise ValueError(f"process {process_id}: oodati vähemalt kahte osalejat, leiti {speaker_count}")
        start, end = time_bounds(transcript)
        duration_seconds = end - start
        rows.append({
            "process": process_id,
            "raw_candidates": candidate_count,
            "speakers": speaker_count,
            "duration_seconds": duration_seconds,
            "candidates_per_5_minutes": candidate_count / duration_seconds * 300,
        })

    if missing:
        detail = "; ".join(f"{process_id} ({why})" for process_id, why in missing)
        raise RuntimeError(f"{len(missing)} kandidaatidega protsessil puudub artefakt: {detail}")

    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[speaker_bucket(int(row["speakers"]))].append(row)

    lines = [
        "# Toorkandidaatide tihedus osalejate arvu järgi",
        "",
        "## Andmed ja arvutus",
        "",
        "Arvutus hõlmab kõiki aktiivseid `AUTOMATIC_DRAFT` versiooni aktiivseid "
        "diariseerimise kandidaate, sõltumata kandidaadi `status`-ist, `decision`-ist "
        "või käsitsi parandamise seisust. Iga saate kandidaatide arv on seega "
        "käsitsi parandamise eelne toorkandidaatide arv.",
        "",
        "Iga saate kohta arvutatakse tihedus `kandidaate / saate kestus sekundites × 300`. "
        "Saate kestus on automaatse transkriptsiooni esimese ja viimase ajamärgi vahe. "
        "Rühma keskmine on nende saatekohaste tiheduste aritmeetiline keskmine: "
        "pikem saade ei saa tulemuses suuremat kaalu ainult oma pikkuse tõttu.",
        "",
        "## Tulemused",
        "",
        "| Osalejate arv | Saateid | Min kandidaate 5 min saate kohta | Maks kandidaate 5 min saate kohta | Keskmine kandidaate 5 min saate kohta | Mediaan kandidaate 5 min saate kohta |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for label in ("2", "3", "4+"):
        densities = [float(row["candidates_per_5_minutes"]) for row in groups[label]]
        lines.append(
            f"| {label} | {len(densities)} | {rounded(min(densities))} | {rounded(max(densities))} | "
            f"{rounded(statistics.mean(densities))} | {rounded(statistics.median(densities))} |"
        )
    all_densities = [float(row["candidates_per_5_minutes"]) for row in rows]
    lines.append(
        f"| **Kõik saated** | **{len(all_densities)}** | {rounded(min(all_densities))} | "
        f"{rounded(max(all_densities))} | {rounded(statistics.mean(all_densities))} | "
        f"{rounded(statistics.median(all_densities))} |"
    )

    lines.extend([
        "",
        "## Kontrollid",
        "",
        f"- Kandidaate sisaldavaid protsesse kokku: **{len(candidate_counts)}**.",
        f"- Arvutusse jõudnud protsesse: **{len(rows)}**.",
        f"- Toorkandidaate kokku: **{sum(candidate_counts.values())}**.",
        "- Kõik tihedused on arvutatud ujukomaarvuna ja esitatud tavapäraselt ümardatuna kolme komakohani.",
    ])
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
