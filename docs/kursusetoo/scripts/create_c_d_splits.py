"""Create fixed C and D show-level 70/30 resplits from the frozen B1/B2 pool.

This script never queries or writes the database.  Its only sources are the
already fixed B training, Test1 and Test2 CSV files.
"""
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LOG = ROOT / "log"
MANIFESTS = ROOT / "docs" / "kursusetoo" / "manifestid"
SOURCES = {
    "training_data_b.csv": "4a7e4dbbbf8c760e10ae49f9cc2b0d77de96fa0ee517731053486d64328c9095",
    "test1_data_b.csv": "de55ad11a8236782ef286e2876c0ba32d1cf9a145377ea3afe0c7d1e0ff08c7e",
    "test2_data_b.csv": "f96dd98818797d8523cf87c4c4d658c989b7b0e91287f91fbfa82214a04bc183",
}
SPECS = {"c": 485716290318, "d": 739184620557}
CLASSES = ("ACCEPTED", "MODIFIED", "REJECTED")
FIELDS = [
    "process", "candidate", "segment", "no", "duration_s", "words",
    "show_speaker_count", "candidate_type", "internal_speaker_change_count",
    "distinct_speaker_count", "dominant_speaker_coverage",
    "nearest_change_edge_ratio", "decision",
]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def speaker_bucket(value):
    value = int(value)
    return "4+" if value >= 4 else str(value)


def counts(rows):
    return {
        "rows": len(rows),
        "labels": dict(Counter(row["decision"] for row in rows)),
        "speaker_buckets": dict(Counter(speaker_bucket(row["show_speaker_count"])
                                          for row in rows)),
        "candidate_types": sorted({row["candidate_type"] for row in rows}),
    }


def score(test_processes, process_stats, total_rows, total_labels, total_buckets, all_types):
    test_rows = sum(process_stats[process]["rows"] for process in test_processes)
    test_labels = Counter()
    test_buckets = Counter()
    test_types = set()
    train_types = set()
    for process, stats in process_stats.items():
        if process in test_processes:
            test_labels.update(stats["labels"])
            test_buckets.update(stats["buckets"])
            test_types.update(stats["types"])
        else:
            train_types.update(stats["types"])
    # Required design constraints.  A rejected candidate score is not eligible.
    required_buckets = {"2", "3", "4+"}
    train_labels = total_labels - test_labels
    train_buckets = total_buckets - test_buckets
    if (not set(CLASSES) <= set(test_labels) or
            not set(CLASSES) <= set(train_labels) or
            not required_buckets <= set(test_buckets) or
            not required_buckets <= set(train_buckets) or
            not test_types <= train_types):
        return None
    target = 0.30 * total_rows
    # Prefer the requested test size and preserve the total class distribution.
    size_error = abs(test_rows - target) / total_rows
    class_error = sum(abs(test_labels.get(label, 0) / test_rows -
                          total_labels[label] / total_rows) for label in CLASSES)
    bucket_error = sum(abs(test_buckets.get(bucket, 0) / test_rows -
                           total_buckets[bucket] / total_rows)
                       for bucket in required_buckets)
    return 10 * size_error + 4 * class_error + bucket_error


def choose_split(name, seed, process_rows, process_stats, total_rows, total_labels,
                 total_buckets, all_types):
    rng = random.Random(seed)
    processes = sorted(process_rows)
    best = None
    # Independent Bernoulli draws retain genuine random variation.  Selecting
    # the best eligible draw turns the stated 70/30 and balance requirements
    # into explicit, reproducible constraints rather than a lucky first draw.
    for _ in range(50000):
        selected = {process for process in processes if rng.random() < 0.30}
        if not selected or len(selected) == len(processes):
            continue
        result = score(selected, process_stats, total_rows, total_labels,
                       total_buckets, all_types)
        if result is None:
            continue
        candidate = (result, tuple(sorted(selected)))
        if best is None or candidate[0] < best[0]:
            best = candidate
    assert best is not None, f"No eligible {name.upper()} split found"
    return best


def write_csv(path, rows):
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main():
    source_rows = []
    for filename, expected_hash in SOURCES.items():
        path = LOG / filename
        assert sha256(path) == expected_hash, f"Unexpected source checksum: {filename}"
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert rows and set(FIELDS) <= set(rows[0]), f"Unexpected CSV fields: {filename}"
        source_rows.extend({field: row[field] for field in FIELDS} for row in rows)

    assert len(source_rows) == 1831
    assert len({int(row["candidate"]) for row in source_rows}) == 1831
    process_rows = defaultdict(list)
    for row in source_rows:
        process_rows[int(row["process"])].append(row)
    assert len(process_rows) == 80
    assert all(len({row["show_speaker_count"] for row in rows}) == 1
               for rows in process_rows.values())
    all_buckets = Counter(speaker_bucket(row["show_speaker_count"]) for row in source_rows)
    total_labels = Counter(row["decision"] for row in source_rows)
    all_types = {row["candidate_type"] for row in source_rows}
    process_stats = {
        process: {
            "rows": len(rows),
            "labels": Counter(row["decision"] for row in rows),
            "buckets": Counter(speaker_bucket(row["show_speaker_count"]) for row in rows),
            "types": {row["candidate_type"] for row in rows},
        }
        for process, rows in process_rows.items()
    }
    assert set(total_labels) == set(CLASSES)

    selected_processes = {}
    for name, seed in SPECS.items():
        score_value, selected = choose_split(
            name, seed, process_rows, process_stats, len(source_rows), total_labels,
            all_buckets, all_types)
        test_rows = [row for process in selected for row in process_rows[process]]
        train_rows = [row for process in sorted(set(process_rows) - set(selected))
                      for row in process_rows[process]]
        selected_processes[name] = set(selected)
        train_path = LOG / f"training_data_{name}.csv"
        test_path = LOG / f"test_data_{name}1.csv"
        write_csv(train_path, train_rows)
        write_csv(test_path, test_rows)
        assert not {row["process"] for row in train_rows} & {row["process"] for row in test_rows}
        assert len(train_rows) + len(test_rows) == len(source_rows)
        assert {row["candidate"] for row in train_rows} | {row["candidate"] for row in test_rows} == {
            row["candidate"] for row in source_rows}
        manifest = {
            "created_on": "2026-10-20",
            "split": name.upper(),
            "method": "50000 independent seeded show-level Bernoulli 70/30 draws; lowest eligible balance score selected",
            "seed": seed,
            "objective_score": score_value,
            "source_files": {filename: checksum for filename, checksum in SOURCES.items()},
            "source_rows": len(source_rows),
            "source_processes": sorted(process_rows),
            "features": FIELDS[4:-1],
            "training": {**counts(train_rows), "processes": sorted(set(int(row["process"]) for row in train_rows)),
                         "sha256": sha256(train_path)},
            "test": {**counts(test_rows), "processes": sorted(set(int(row["process"]) for row in test_rows)),
                     "sha256": sha256(test_path)},
        }
        manifest_path = MANIFESTS / f"{name}_split_manifest.json"
        with manifest_path.open("x", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2)
            handle.write("\n")
        print(json.dumps({"split": name.upper(), "score": score_value,
                          "training": manifest["training"], "test": manifest["test"]}, indent=2))
    assert selected_processes["c"] != selected_processes["d"]


if __name__ == "__main__":
    main()
