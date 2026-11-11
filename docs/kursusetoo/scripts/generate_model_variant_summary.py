#!/usr/bin/env python3
"""Koosta B1–D1 mudelivariantide täielik Markdown-koondtabel.

Lähteandmed on GNU Octave'i mudelitulemuste CSV-d. B1 korral asendatakse
algse Test1 käituse 54 standardse SVM-i rida uuema SVM-käituse ridadega.
"""

from __future__ import annotations

import csv
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "docs/kursusetoo/mudelivariantide_koondtulemused.md"
METRICS = [
    ("TrainingAccuracy", "Treeningu accuracy"),
    ("Accuracy", "Accuracy"),
    ("MacroF1", "Macro-F1"),
    ("BalancedAccuracy", "Balanced accuracy"),
    ("WeightedF1", "Weighted F1"),
]
TOP_METRICS = [item for item in METRICS if item[0] != "TrainingAccuracy"]
COHORTS = {
    "B1": ROOT / "log/oct-HlIJvh_test1_octave/models_test1_octave.csv",
    "B2": ROOT / "log/oct-rdhW8P_test2_octave/models_test2_octave.csv",
    "C1": ROOT / "log/oct-yxbe3l_c1_octave/models_c1_octave.csv",
    "D1": ROOT / "log/oct-3bqqzd_d1_octave/models_d1_octave.csv",
    "X1": ROOT / "log/oct-bshFjj_x1_octave/models_x1_octave.csv",
    "Y1": ROOT / "log/oct-OKMtsB_y1_octave/models_y1_octave.csv",
}
B1_SVM_UPDATE = ROOT / "log/oct-TmAUoK_test1_octave/models_test1_octave.csv"
RANKING_COHORTS = ("B1", "B2", "C1", "D1")


def key(row: dict[str, str]) -> tuple[str, str]:
    return row["Model"], row["Variant"]


def read_rows(path: Path, expected_rows: int = 498) -> dict[tuple[str, str], dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = {key(row): row for row in csv.DictReader(handle)}
    if len(rows) != expected_rows:
        raise ValueError(f"{path}: oodati {expected_rows} rida, leiti {len(rows)}")
    return rows


def display_variant(variant: str) -> str:
    return "kõik 8 tunnust" if variant == "full" else f"`{variant}` eemaldatud"


def pct(value: str) -> str:
    return f"{100 * float(value):.2f}%".replace(".", ",")


def load_data() -> tuple[dict[str, dict[tuple[str, str], dict[str, str]]], list[tuple[str, str]]]:
    data = {name: read_rows(path) for name, path in COHORTS.items()}
    b1_update = read_rows(B1_SVM_UPDATE, expected_rows=54)
    for item_key, row in b1_update.items():
        data["B1"][item_key] = row

    all_keys = sorted(data["B1"])
    if any(set(rows) != set(all_keys) for rows in data.values()):
        raise ValueError("Katsete mudelivariantide kogumid ei ühti")
    return data, all_keys


def top_tables(data: dict[str, dict[tuple[str, str], dict[str, str]]], all_keys: list[tuple[str, str]], count: int) -> str:
    lines = []
    for metric, label in TOP_METRICS:
        ordered = sorted(
            all_keys,
            key=lambda item_key: sum(float(data[cohort][item_key][metric]) for cohort in RANKING_COHORTS) / len(RANKING_COHORTS),
            reverse=True,
        )
        ranked = ordered[:count]
        extrema = {
            cohort: (
                max(float(data[cohort][item_key][metric]) for item_key in all_keys),
                min(float(data[cohort][item_key][metric]) for item_key in all_keys),
            )
            for cohort in COHORTS
        }
        extras = [
            item_key for item_key in ordered[count:]
            if any(float(data[cohort][item_key][metric]) in extrema[cohort] for cohort in COHORTS)
        ]
        lines.extend([
            f"### Parimad mudelid {label} järgi",
            "",
            "| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ])
        for index, (model, variant) in enumerate(ranked + extras):
            values = [float(data[cohort][(model, variant)][metric]) for cohort in COHORTS]
            formatted = []
            for cohort, value in zip(COHORTS, values):
                rendered = pct(str(value))
                highest, lowest = extrema[cohort]
                if value == highest:
                    rendered = f"**{rendered}**"
                elif value == lowest:
                    rendered = f"***{rendered}***"
                formatted.append(rendered)
            lines.append(
                f"| {model}, {display_variant(variant)} | "
                + " | ".join(formatted[:4])
                + f" | {pct(str(sum(values[:4]) / len(values[:4])))} | {formatted[4]} | {formatted[5]} |"
            )
            if index == len(ranked) - 1 and extras:
                lines.append("| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, help="prindi iga mõõdiku parimad variandid Markdownina")
    parser.add_argument("--update-main", action="store_true", help="asenda põhidokumendi üldiste mudelitabelite plokk")
    args = parser.parse_args()
    data, all_keys = load_data()

    if args.top:
        print(top_tables(data, all_keys, args.top))
        return

    if args.update_main:
        main_doc = ROOT / "docs/kursusetoo/tulemused.md"
        start = "<!-- OVERALL_MODEL_TABLES_START -->"
        end = "<!-- OVERALL_MODEL_TABLES_END -->"
        text = main_doc.read_text(encoding="utf-8")
        before, remainder = text.split(start, 1)
        _, after = remainder.split(end, 1)
        main_doc.write_text(before + start + "\n\n" + top_tables(data, all_keys, 10) + end + after, encoding="utf-8")
        return

    headers = ["Mudel", "Tunnusevariant"]
    alignments = ["---", "---"]
    for cohort in COHORTS:
        headers.extend(f"{cohort} {label.lower()}" for _, label in METRICS)
        alignments.extend("---:" for _ in METRICS)

    lines = [
        "# Mudelivariantide koondtulemused",
        "",
        "See dokument sisaldab kõikide 498 kaheksa atribuudiga mudelivariandi",
        "B1, B2, C1, D1, X1 ja Y1 tulemusi. Põhidokumendis on nende tulemuste",
        "lühendatud top-tabelid ja tõlgendus: [tulemused.md](tulemused.md).",
        "",
        "B1 tabelis on 54 standardse SVM-i tulemused uuemast käitusest",
        "`log/oct-TmAUoK_test1_octave`; ülejäänud 444 tulemust pärinevad",
        "`log/oct-HlIJvh_test1_octave`. B2, C1 ja D1 on vastavalt",
        "`log/oct-rdhW8P_test2_octave`, `log/oct-yxbe3l_c1_octave`,",
        "`log/oct-3bqqzd_d1_octave`; X1 on `log/oct-bshFjj_x1_octave` ja",
        "Y1 on `log/oct-OKMtsB_y1_octave`.",
        "Kõik 498 varianti lõpetasid igas katses",
        "staatusega `OK`.",
        "",
        "Mõõdikute tähendused on põhidokumendi jaotises „Mõõdikute tähendus“.",
        "Tabeli veergudes on protsendid; treeningu accuracy on võrdluseks,",
        "mitte mudelite valimise iseseisev alus.",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(alignments) + " |",
    ]
    for item_key in all_keys:
        model, variant = item_key
        values = []
        for cohort in COHORTS:
            row = data[cohort][item_key]
            values.extend(pct(row[metric]) for metric, _ in METRICS)
        lines.append(f"| {model} | {display_variant(variant)} | " + " | ".join(values) + " |")

    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
