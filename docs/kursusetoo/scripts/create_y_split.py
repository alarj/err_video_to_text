"""Create an independent candidate-level Y 70/30 split from the B/B1/B2 pool."""

import csv
import hashlib
import json
import secrets
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LOG = ROOT / "log"
MANIFEST = ROOT / "docs" / "kursusetoo" / "manifestid" / "y_split_manifest.json"
X_MANIFEST = ROOT / "docs" / "kursusetoo" / "manifestid" / "x_split_manifest.json"
SOURCES = {
    "training_data_b.csv": "4a7e4dbbbf8c760e10ae49f9cc2b0d77de96fa0ee517731053486d64328c9095",
    "test1_data_b.csv": "de55ad11a8236782ef286e2876c0ba32d1cf9a145377ea3afe0c7d1e0ff08c7e",
    "test2_data_b.csv": "f96dd98818797d8523cf87c4c4d658c989b7b0e91287f91fbfa82214a04bc183",
}
CLASSES = ("ACCEPTED", "MODIFIED", "REJECTED")
FIELDS = [
    "process", "candidate", "segment", "no", "duration_s", "words",
    "show_speaker_count", "candidate_type", "internal_speaker_change_count",
    "distinct_speaker_count", "dominant_speaker_coverage",
    "nearest_change_edge_ratio", "decision",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bucket(value):
    return "4+" if int(value) >= 4 else str(int(value))


def summary(rows):
    return {
        "rows": len(rows),
        "labels": dict(Counter(row["decision"] for row in rows)),
        "speaker_buckets": dict(Counter(bucket(row["show_speaker_count"]) for row in rows)),
        "candidate_types": sorted({row["candidate_type"] for row in rows}),
        "processes": sorted({int(row["process"]) for row in rows}),
        "candidates": sorted(int(row["candidate"]) for row in rows),
    }


def write(path, rows):
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main():
    assert not MANIFEST.exists(), "Y manifest already exists; do not silently replace a fixed split."
    assert X_MANIFEST.exists(), "X manifest must exist before making independent Y split."
    rows = []
    for filename, expected in SOURCES.items():
        path = LOG / filename
        assert digest(path) == expected, f"Unexpected source checksum: {filename}"
        with path.open(encoding="utf-8", newline="") as handle:
            source = list(csv.DictReader(handle))
        assert source and set(FIELDS) <= set(source[0]), filename
        rows.extend({field: row[field] for field in FIELDS} for row in source)

    assert len(rows) == 1831
    assert len({row["candidate"] for row in rows}) == len(rows)
    rng = secrets.SystemRandom()
    by_class = {label: [row for row in rows if row["decision"] == label] for label in CLASSES}
    test = []
    for label in CLASSES:
        test.extend(rng.sample(by_class[label], round(0.30 * len(by_class[label]))))
    test_ids = {row["candidate"] for row in test}
    train = [row for row in rows if row["candidate"] not in test_ids]
    rng.shuffle(train)
    rng.shuffle(test)
    train_info, test_info = summary(train), summary(test)
    assert train_info["rows"] + test_info["rows"] == 1831
    assert set(CLASSES) <= set(train_info["labels"]) and set(CLASSES) <= set(test_info["labels"])
    assert {"2", "3", "4+"} <= set(train_info["speaker_buckets"])
    assert {"2", "3", "4+"} <= set(test_info["speaker_buckets"])
    assert set(test_info["candidate_types"]) <= set(train_info["candidate_types"])
    assert set(train_info["processes"]) & set(test_info["processes"])
    x_test = {int(candidate) for candidate in json.loads(X_MANIFEST.read_text(encoding="utf-8"))["test"]["candidates"]}
    assert test_ids != x_test, "Y test split must not equal X test split."

    train_path, test_path = LOG / "training_data_y.csv", LOG / "test_data_y1.csv"
    write(train_path, train)
    write(test_path, test)
    manifest = {
        "created_on": "2026-10-20",
        "split": "Y / Y1",
        "method": "independent candidate-level stratified 70/30 split; Python secrets.SystemRandom backed by the OS CSPRNG; no show-level exclusion",
        "source_files": SOURCES,
        "source_rows": len(rows),
        "features": FIELDS[4:-1],
        "training": {**train_info, "sha256": digest(train_path)},
        "test": {**test_info, "sha256": digest(test_path)},
        "shared_processes": sorted(set(train_info["processes"]) & set(test_info["processes"]),),
        "shared_process_count": len(set(train_info["processes"]) & set(test_info["processes"])),
        "x1_test_overlap_candidates": len(test_ids & x_test),
        "x1_test_jaccard": len(test_ids & x_test) / len(test_ids | x_test),
    }
    with MANIFEST.open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    compact = {**manifest, "training": {key: value for key, value in manifest["training"].items() if key != "candidates"}, "test": {key: value for key, value in manifest["test"].items() if key != "candidates"}}
    print(json.dumps(compact, indent=2))


if __name__ == "__main__":
    main()
