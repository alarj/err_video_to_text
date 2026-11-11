#!/usr/bin/env python3
"""Lisa tulemuste põhidokumenti klassipõhised parimate mudelite tabelid."""

from __future__ import annotations

import csv
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "docs/kursusetoo/tulemused.md"
COHORTS = ("B1", "B2", "C1", "D1", "X1", "Y1")
RANKING_COHORTS = COHORTS[:4]
PATHS = {
    "B1": ROOT / "log/oct-HlIJvh_test1_octave/perclass_test1_octave.csv",
    "B2": ROOT / "log/oct-rdhW8P_test2_octave/perclass_test2_octave.csv",
    "C1": ROOT / "log/oct-yxbe3l_c1_octave/perclass_c1_octave.csv",
    "D1": ROOT / "log/oct-3bqqzd_d1_octave/perclass_d1_octave.csv",
    "X1": ROOT / "log/oct-bshFjj_x1_octave/perclass_x1_octave.csv",
    "Y1": ROOT / "log/oct-OKMtsB_y1_octave/perclass_y1_octave.csv",
}
B1_SVM_UPDATE = ROOT / "log/oct-TmAUoK_test1_octave/perclass_test1_octave.csv"
METRICS = (
    ("Precision", "precision", True),
    ("Recall_TPR", "recall / TPR", True),
    ("F1", "F1", True),
    ("FPR", "FPR", False),
    ("FNR", "FNR", False),
    ("Specificity_TNR", "specificity / TNR", True),
)
CLASSES = ("ACCEPTED", "MODIFIED", "REJECTED")
START = "<!-- CLASS_MODEL_TABLES_START -->"
END = "<!-- CLASS_MODEL_TABLES_END -->"


def read(path: Path) -> dict[tuple[str, str, str], dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {(r["Model"], r["Variant"], r["Class"]): r for r in csv.DictReader(handle)}


def number(value: str) -> float:
    return float(value) if value else math.nan


def mean(values: list[float]) -> float:
    values = [value for value in values if not math.isnan(value)]
    return sum(values) / len(values) if values else math.nan


def pct(value: float) -> str:
    return "—" if math.isnan(value) else f"{value * 100:.2f}%".replace(".", ",")


def display_variant(variant: str) -> str:
    return "kõik 8 tunnust" if variant == "full" else f"`{variant}` eemaldatud"


def equal(left: float, right: float) -> bool:
    return not math.isnan(left) and not math.isnan(right) and abs(left - right) < 1e-12


def table(data: dict[str, dict[tuple[str, str, str], dict[str, str]]], class_name: str, metric: str, label: str, higher_is_better: bool) -> list[str]:
    keys = sorted((model, variant) for model, variant, item_class in data["B1"] if item_class == class_name)

    def value(cohort: str, item_key: tuple[str, str]) -> float:
        return number(data[cohort][(item_key[0], item_key[1], class_name)][metric])

    def score(item_key: tuple[str, str]) -> float:
        return mean([value(cohort, item_key) for cohort in RANKING_COHORTS])

    ordered = sorted(keys, key=score, reverse=higher_is_better)
    # Top-5 piir on nähtavas protsendivormingus: sama koht tähendab sama
    # B1–D1 keskmist pärast ümardamist kahe komakohani.
    fifth_score = round(score(ordered[4]) * 100, 2)
    ranked = [item_key for item_key in ordered if round(score(item_key) * 100, 2) == fifth_score or item_key in ordered[:5]]
    extrema: dict[str, tuple[float, float]] = {}
    for cohort in COHORTS:
        values = [value(cohort, item_key) for item_key in keys]
        values = [item for item in values if not math.isnan(item)]
        extrema[cohort] = ((max(values), min(values)) if higher_is_better else (min(values), max(values)))

    extras = [
        item_key for item_key in keys if item_key not in ranked
        and any(equal(value(cohort, item_key), extreme) for cohort, extremes in extrema.items() for extreme in extremes)
    ]
    lines = [f"##### {label}", "", "| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for index, item_key in enumerate(ranked + extras):
        rendered = []
        for cohort in COHORTS:
            item = value(cohort, item_key)
            best, worst = extrema[cohort]
            text = pct(item)
            if equal(item, best):
                text = f"**{text}**"
            elif equal(item, worst):
                text = f"***{text}***"
            rendered.append(text)
        lines.append(
            f"| {item_key[0]}, {display_variant(item_key[1])} | "
            + " | ".join(rendered[:4])
            + f" | {pct(score(item_key))} | {rendered[4]} | {rendered[5]} |"
        )
        if index == len(ranked) - 1 and extras:
            lines.append("| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |")
    return lines + [""]


def main() -> None:
    data = {cohort: read(path) for cohort, path in PATHS.items()}
    for row in csv.DictReader(B1_SVM_UPDATE.open(encoding="utf-8", newline="")):
        data["B1"][(row["Model"], row["Variant"], row["Class"])] = row

    lines = [START, "", "Iga järgmine tabel sisaldab vähemalt viis B1–D1 keskmise järgi parimat mudelivarianti. Kui järgmise variandi keskmine on viiendal kohal olevaga sama pärast ümardamist kahe komakohani, kuulub ka see põhiossa. Punktiirjoone all on kõik tabeli põhiosast puudunud variandid, mis olid vähemalt ühes B1, B2, C1, D1, X1 või Y1 katses vastava mõõdiku sisuliselt parimad või halvimad. Precisioni, recalli, F1 ja specificity puhul on suurem parem; FPR-i ja FNR-i puhul väiksem parem. **Paks** tähistab parimat ning ***paks kursiiv*** halvimat tulemust.", ""]
    for class_name in CLASSES:
        lines.extend([f"#### Parimad mudelid klassis `{class_name}`", ""])
        for metric, label, higher_is_better in METRICS:
            lines.extend(table(data, class_name, metric, label, higher_is_better))
    lines.append(END)
    text = OUTPUT.read_text(encoding="utf-8")
    before, remainder = text.split(START, 1)
    _, after = remainder.split(END, 1)
    OUTPUT.write_text(before + "\n".join(lines) + after, encoding="utf-8")


if __name__ == "__main__":
    main()
