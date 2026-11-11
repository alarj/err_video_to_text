#!/usr/bin/env python3
"""Loo kolme otsuseklassi CSV-dest binaarsed inimsekkumise andmed.

Reegel on teadlikult ainus muutus lähteandmete suhtes:
ACCEPTED ja REJECTED -> 0; MODIFIED -> 1.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LOG = ROOT / "log"
MANIFEST = ROOT / "docs/kursusetoo/manifestid/inimsekkumise_andmed.json"

ATTRIBUTES = [
    "duration_s",
    "words",
    "show_speaker_count",
    "candidate_type",
    "internal_speaker_change_count",
    "distinct_speaker_count",
    "dominant_speaker_coverage",
    "nearest_change_edge_ratio",
]
OUTPUT_COLUMNS = ["process", "candidate", "segment", "no", *ATTRIBUTES, "human_interaction_required"]
SOURCES = {
    "B": ("training_data_b.csv", "training_data_b_inimsekkumine.csv"),
    "B1": ("test1_data_b.csv", "test1_data_b_inimsekkumine.csv"),
    "B2": ("test2_data_b.csv", "test2_data_b_inimsekkumine.csv"),
    "C": ("training_data_c.csv", "training_data_c_inimsekkumine.csv"),
    "C1": ("test_data_c1.csv", "test_data_c1_inimsekkumine.csv"),
    "D": ("training_data_d.csv", "training_data_d_inimsekkumine.csv"),
    "D1": ("test_data_d1.csv", "test_data_d1_inimsekkumine.csv"),
    "X": ("training_data_x.csv", "training_data_x_inimsekkumine.csv"),
    "X1": ("test_data_x1.csv", "test_data_x1_inimsekkumine.csv"),
    "Y": ("training_data_y.csv", "training_data_y_inimsekkumine.csv"),
    "Y1": ("test_data_y1.csv", "test_data_y1_inimsekkumine.csv"),
}
MAPPING = {"ACCEPTED": "0", "REJECTED": "0", "MODIFIED": "1"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    manifest: dict[str, object] = {
        "response": "human_interaction_required",
        "mapping": MAPPING,
        "attributes": ATTRIBUTES,
        "datasets": {},
    }
    for label, (source_name, output_name) in SOURCES.items():
        source = LOG / source_name
        output = LOG / output_name
        with source.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ValueError(f"{source}: päiserida puudub")
            required = {"decision", *OUTPUT_COLUMNS[:-1]}
            missing = required - set(reader.fieldnames)
            if missing:
                raise ValueError(f"{source}: puuduvad veerud {sorted(missing)}")
            rows = list(reader)

        binary = Counter()
        decisions = Counter()
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
            writer.writeheader()
            for row in rows:
                decision = row["decision"]
                if decision not in MAPPING:
                    raise ValueError(f"{source}: tundmatu decision {decision!r}")
                value = MAPPING[decision]
                writer.writerow({column: row[column] for column in OUTPUT_COLUMNS[:-1]} | {
                    "human_interaction_required": value,
                })
                decisions[decision] += 1
                binary[value] += 1

        manifest["datasets"][label] = {
            "source": f"log/{source_name}",
            "output": f"log/{output_name}",
            "rows": len(rows),
            "source_decisions": dict(sorted(decisions.items())),
            "binary_classes": dict(sorted(binary.items())),
            "sha256": sha256(output),
        }
        print(f"{label}: {len(rows)} rida, 0={binary['0']}, 1={binary['1']}: {output}")

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Manifest: {MANIFEST}")


if __name__ == "__main__":
    main()
