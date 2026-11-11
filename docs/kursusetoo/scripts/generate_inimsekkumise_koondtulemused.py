#!/usr/bin/env python3
"""Koosta binaarse inimsekkumise katse täielik mudelitabel."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "docs/kursusetoo/mudelivariantide_koondtulemused2.md"
COHORTS = ("B1", "B2", "C1", "D1", "X1", "Y1")
METRICS = (
    ("Recall1_TPR", "Recall(1) / TPR(1)"),
    ("FNR1", "FNR(1)"),
    ("NPV0_AutomaticBranchCorrectness", "Automaatharu õigsus / NPV(0)"),
    ("AutomaticBranchShare", "Automaatharu osakaal"),
    ("BalancedAccuracy", "Balanced accuracy"),
    ("F1Class1", "F1(1)"),
    ("MacroF1", "Macro-F1"),
    ("Accuracy", "Accuracy"),
)


def variant_name(value: str) -> str:
    return "kõik 8 atribuuti" if value == "full" else f"`{value}` eemaldatud"


def pct(value: str) -> str:
    if value == "":
        return "—"
    return f"{100 * float(value):.2f}%".replace(".", ",")


def load_cohort(cohort: str) -> dict[tuple[str, str], dict[str, str]]:
    complete = []
    supplements = []
    file_cohort = cohort.lower()
    for path in sorted((ROOT / "log").glob(f"*_{file_cohort}_inimsekkumine_octave/models_{file_cohort}_inimsekkumine_octave.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        perclass_path = path.with_name(path.name.replace("models_", "perclass_", 1))
        with perclass_path.open(newline="", encoding="utf-8") as handle:
            f1_class1 = {
                (row["Model"], row["Variant"]): row["F1"]
                for row in csv.DictReader(handle)
                if row["Class"] == "1"
            }
        for row in rows:
            if row["Status"] == "OK":
                row["F1Class1"] = f1_class1[(row["Model"], row["Variant"])]
        if len(rows) == 498:
            complete.append(rows)
        elif len(rows) == 9 and all(row["Model"] == "Boosted Trees" and row["Status"] == "OK" for row in rows):
            supplements.append(rows)
    if len(complete) != 1 or len(supplements) != 1:
        raise ValueError(f"{cohort}: oodati üht 498-realist põhitulemust ja üht 9-realist Boosted Treesi tulemust")
    data = {(row["Model"], row["Variant"]): row for row in complete[0] if row["Status"] == "OK"}
    data.update({(row["Model"], row["Variant"]): row for row in supplements[0]})
    if len(data) != 498 or any(row["Status"] != "OK" for row in data.values()):
        raise ValueError(f"{cohort}: täielik tulemus ei koosne 498 edukast variandist")
    return data


def main() -> None:
    datasets = {}
    for cohort in COHORTS:
        datasets[cohort] = load_cohort(cohort)
    keys = sorted(datasets["B1"])
    if any(set(datasets[cohort]) != set(keys) for cohort in COHORTS):
        raise ValueError("Mudelite ja variantide kogumid ei ühti")

    headers = ["Mudel", "Atribuutide variant"] + [f"{cohort} {label}" for cohort in COHORTS for _, label in METRICS]
    lines = [
        "# Mudelivariantide binaarsed koondtulemused",
        "",
        "Täielik tabel sisaldab kõiki 498 mudeli-/atribuudivarianti kuuel binaarsel",
        "katsel. Vastus `human_interaction_required` on tuletatud muutmata",
        "otsusest: `ACCEPTED` ja `REJECTED` = 0; `MODIFIED` = 1.",
        "",
        "Mõõdikute ning valikureegli selgitus on failis [tulemused2.md](tulemused2.md).",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---", "---"] + ["---:" for _ in headers[2:]]) + " |",
    ]
    for key in keys:
        values = []
        for cohort in COHORTS:
            row = datasets[cohort][key]
            values.extend(pct(row[name]) for name, _ in METRICS)
        lines.append(f"| {key[0]} | {variant_name(key[1])} | " + " | ".join(values) + " |")
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
