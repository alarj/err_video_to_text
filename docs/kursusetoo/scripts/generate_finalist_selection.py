#!/usr/bin/env python3
"""Koosta põhidokumenti fikseeritud finalistide valiku tabelid."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "docs/kursusetoo/tulemused.md"
COHORTS = ("B1", "B2", "C1", "D1")
ALL_COHORTS = COHORTS + ("X1", "Y1")
CLASSES = ("ACCEPTED", "MODIFIED", "REJECTED")
MODEL_PATHS = {
    "B1": ROOT / "log/oct-HlIJvh_test1_octave/models_test1_octave.csv",
    "B2": ROOT / "log/oct-rdhW8P_test2_octave/models_test2_octave.csv",
    "C1": ROOT / "log/oct-yxbe3l_c1_octave/models_c1_octave.csv",
    "D1": ROOT / "log/oct-3bqqzd_d1_octave/models_d1_octave.csv",
    "X1": ROOT / "log/oct-bshFjj_x1_octave/models_x1_octave.csv",
    "Y1": ROOT / "log/oct-OKMtsB_y1_octave/models_y1_octave.csv",
}
PERCLASS_PATHS = {name: path.with_name(path.name.replace("models_", "perclass_")) for name, path in MODEL_PATHS.items()}
B1_MODEL_UPDATE = ROOT / "log/oct-TmAUoK_test1_octave/models_test1_octave.csv"
B1_PERCLASS_UPDATE = ROOT / "log/oct-TmAUoK_test1_octave/perclass_test1_octave.csv"
START = "<!-- FINALIST_SELECTION_START -->"
END = "<!-- FINALIST_SELECTION_END -->"


def read(path: Path, key_fields: tuple[str, ...]) -> dict[tuple[str, ...], dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {tuple(row[field] for field in key_fields): row for row in csv.DictReader(handle)}


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def pct(value: float) -> str:
    return f"{value * 100:.2f}%".replace(".", ",")


def display(item_key: tuple[str, str]) -> str:
    model, variant = item_key
    variant_text = "kõik 8 tunnust" if variant == "full" else f"`{variant}` eemaldatud"
    return f"{model}, {variant_text}"


def percentile_ranks(values: dict[tuple[str, str], float]) -> dict[tuple[str, str], float]:
    """Keskmise asetuse protsentiil: sidemed saavad sama väärtuse."""
    count = len(values)
    return {
        key: (sum(other < value for other in values.values()) + (sum(other == value for other in values.values()) - 1) / 2) / (count - 1)
        for key, value in values.items()
    }


def main() -> None:
    model = {name: read(path, ("Model", "Variant")) for name, path in MODEL_PATHS.items()}
    perclass = {name: read(path, ("Model", "Variant", "Class")) for name, path in PERCLASS_PATHS.items()}
    model["B1"].update(read(B1_MODEL_UPDATE, ("Model", "Variant")))
    perclass["B1"].update(read(B1_PERCLASS_UPDATE, ("Model", "Variant", "Class")))
    keys = sorted(model["B1"])

    def overall(item_key: tuple[str, str], metric: str, cohorts: tuple[str, ...] = COHORTS) -> float:
        return mean([float(model[cohort][item_key][metric]) for cohort in cohorts])

    def class_value(item_key: tuple[str, str], class_name: str, metric: str, cohorts: tuple[str, ...] = COHORTS) -> float:
        return mean([float(perclass[cohort][(item_key[0], item_key[1], class_name)][metric] or 0) for cohort in cohorts])

    ranks = {metric: percentile_ranks({key: overall(key, metric) for key in keys}) for metric in ("Accuracy", "MacroF1", "BalancedAccuracy", "WeightedF1")}
    for class_name in CLASSES:
        for metric in ("F1", "Recall_TPR"):
            ranks[f"{class_name}_{metric}"] = percentile_ranks({key: class_value(key, class_name, metric) for key in keys})

    eligible = [
        key for key in keys
        if all(
            min(float(perclass[cohort][(key[0], key[1], class_name)]["F1"] or 0) for cohort in COHORTS) >= 0.50
            and min(float(perclass[cohort][(key[0], key[1], class_name)]["Recall_TPR"] or 0) for cohort in COHORTS) >= 0.55
            for class_name in CLASSES
        )
    ]

    def general_score(item_key: tuple[str, str]) -> float:
        return (
            0.25 * ranks["MacroF1"][item_key]
            + 0.15 * ranks["BalancedAccuracy"][item_key]
            + 0.07 * ranks["WeightedF1"][item_key]
            + 0.03 * ranks["Accuracy"][item_key]
        )

    def overall_score(item_key: tuple[str, str]) -> float:
        return general_score(item_key) + 0.40 * mean([ranks[f"{class_name}_F1"][item_key] for class_name in CLASSES]) + 0.10 * mean([ranks[f"{class_name}_Recall_TPR"][item_key] for class_name in CLASSES])

    def class_score(item_key: tuple[str, str], class_name: str) -> float:
        return general_score(item_key) + 0.40 * ranks[f"{class_name}_F1"][item_key] + 0.10 * ranks[f"{class_name}_Recall_TPR"][item_key]

    overall_top = sorted(eligible, key=overall_score, reverse=True)[:10]
    class_top = {class_name: sorted(eligible, key=lambda key: class_score(key, class_name), reverse=True)[:5] for class_name in CLASSES}
    class_only = sorted(set().union(*class_top.values()) - set(overall_top), key=overall_score, reverse=True)

    lines = [
        START,
        "",
        "### Fikseeritud finalistide valikureegel",
        "",
        "See finalistitabel on B1–D1 saadetepõhiste katsete rakendus sama valikureegliga. X1–Y1 kandidaadipõhise jaotuse rakendus on allpool ning seda käsitletakse samaväärse võrdlusandmena. Kõigepealt rakendatakse kõigile kolmele klassile ja igale B1–D1 katsele kaks kohustuslikku tingimust: `F1 ≥ 50%` ning `recall / TPR ≥ 55%`. Selle filtri läbis **51/498** varianti.",
        "",
        "Allesjäänud variante võrreldakse protsentiilsete asetuste abil kõigi 498 variandi seas. Üldine koondskoor on 50% üldtoimivus (`25%` macro-F1, `15%` balanced accuracy, `7%` weighted F1, `3%` accuracy), 40% kolme klassi F1 võrdne keskmine ja 10% kolme klassi recall'i võrdne keskmine. Klassipõhistes top-5 tabelites kasutatakse sama üldtoimivuse 50% osa, kuid ülejäänud 50% tuleb vastava klassi F1-st (40%) ja recall'ist (10%).",
        "",
        "#### Üldine top-10",
        "",
        "| Koht | Variant | Koondskoor | Macro-F1, B1–D1 | Balanced accuracy, B1–D1 | Weighted F1, B1–D1 | Macro-F1, X1 | Macro-F1, Y1 |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for position, item_key in enumerate(overall_top, 1):
        lines.append(f"| {position} | {display(item_key)} | {overall_score(item_key) * 100:.2f} | {pct(overall(item_key, 'MacroF1'))} | {pct(overall(item_key, 'BalancedAccuracy'))} | {pct(overall(item_key, 'WeightedF1'))} | {pct(overall(item_key, 'MacroF1', ('X1',)))} | {pct(overall(item_key, 'MacroF1', ('Y1',)))} |".replace(".", ","))

    for class_name in CLASSES:
        lines.extend([
            "",
            f"#### Klass `{class_name}` – top-5",
            "",
            "| Koht | Variant | Klassiskoor | F1, B1–D1 | Recall / TPR, B1–D1 | F1, X1 | Recall / TPR, X1 | F1, Y1 | Recall / TPR, Y1 |",
            "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
        ])
        for position, item_key in enumerate(class_top[class_name], 1):
            lines.append(f"| {position} | {display(item_key)} | {class_score(item_key, class_name) * 100:.2f} | {pct(class_value(item_key, class_name, 'F1'))} | {pct(class_value(item_key, class_name, 'Recall_TPR'))} | {pct(class_value(item_key, class_name, 'F1', ('X1',)))} | {pct(class_value(item_key, class_name, 'Recall_TPR', ('X1',)))} | {pct(class_value(item_key, class_name, 'F1', ('Y1',)))} | {pct(class_value(item_key, class_name, 'Recall_TPR', ('Y1',)))} |".replace(".", ","))

    lines.extend([
        "",
        "#### Klassitop-5-st üldisest top-10-st välja jäänud variandid",
        "",
        "| Variant | Jõudis klassi top-5 hulka | Üldine koondskoor |",
        "|---|---|---:|",
    ])
    for item_key in class_only:
        reached = ", ".join(class_name for class_name in CLASSES if item_key in class_top[class_name])
        lines.append(f"| {display(item_key)} | `{reached}` | {overall_score(item_key) * 100:.2f} |".replace(".", ","))

    # X1/Y1 kasutab täpselt sama filtrit ja protsentiilset skoori nagu
    # B1–D1 valik, kuid kahe kandidaadipõhise juhujaotuse keskmistel.
    # See on võrdlusvaade ega asenda saadetepõhist põhi-eelvalikut.
    xy_cohorts = ("X1", "Y1")

    def xy_overall(item_key: tuple[str, str], metric: str) -> float:
        return overall(item_key, metric, xy_cohorts)

    def xy_class_value(item_key: tuple[str, str], class_name: str, metric: str) -> float:
        return class_value(item_key, class_name, metric, xy_cohorts)

    xy_ranks = {
        metric: percentile_ranks({key: xy_overall(key, metric) for key in keys})
        for metric in ("Accuracy", "MacroF1", "BalancedAccuracy", "WeightedF1")
    }
    for class_name in CLASSES:
        for metric in ("F1", "Recall_TPR"):
            xy_ranks[f"{class_name}_{metric}"] = percentile_ranks(
                {key: xy_class_value(key, class_name, metric) for key in keys}
            )

    xy_eligible = [
        key for key in keys
        if all(
            min(float(perclass[cohort][(key[0], key[1], class_name)]["F1"] or 0) for cohort in xy_cohorts) >= 0.50
            and min(float(perclass[cohort][(key[0], key[1], class_name)]["Recall_TPR"] or 0) for cohort in xy_cohorts) >= 0.55
            for class_name in CLASSES
        )
    ]

    def xy_general_score(item_key: tuple[str, str]) -> float:
        return (
            0.25 * xy_ranks["MacroF1"][item_key]
            + 0.15 * xy_ranks["BalancedAccuracy"][item_key]
            + 0.07 * xy_ranks["WeightedF1"][item_key]
            + 0.03 * xy_ranks["Accuracy"][item_key]
        )

    def xy_overall_score(item_key: tuple[str, str]) -> float:
        return xy_general_score(item_key) + 0.40 * mean([xy_ranks[f"{class_name}_F1"][item_key] for class_name in CLASSES]) + 0.10 * mean([xy_ranks[f"{class_name}_Recall_TPR"][item_key] for class_name in CLASSES])

    def xy_class_score(item_key: tuple[str, str], class_name: str) -> float:
        return xy_general_score(item_key) + 0.40 * xy_ranks[f"{class_name}_F1"][item_key] + 0.10 * xy_ranks[f"{class_name}_Recall_TPR"][item_key]

    xy_top = sorted(xy_eligible, key=xy_overall_score, reverse=True)[:10]
    xy_class_top = {class_name: sorted(xy_eligible, key=lambda key: xy_class_score(key, class_name), reverse=True)[:5] for class_name in CLASSES}
    xy_class_only = sorted(set().union(*xy_class_top.values()) - set(xy_top), key=xy_overall_score, reverse=True)

    lines.extend([
        "",
        "### X1–Y1 kandidaadipõhine finalistivalik",
        "",
        f"See on X1–Y1 kandidaadipõhise jaotuse rakendus sama valikureegliga. Kasutatud on sama filtrit (`F1 ≥ 50%` ja `recall / TPR ≥ 55%` igas klassis mõlemas katses) ning sama protsentiilset kaalutud skoori. Filtri läbis **{len(xy_eligible)}/498** varianti.",
        "",
        "#### Üldine top-10",
        "",
        "| Koht | Variant | Koondskoor | Macro-F1, X1 | Macro-F1, Y1 | Macro-F1, X1–Y1 | Balanced accuracy, X1–Y1 | Weighted F1, X1–Y1 |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ])
    for position, item_key in enumerate(xy_top, 1):
        lines.append(f"| {position} | {display(item_key)} | {xy_overall_score(item_key) * 100:.2f} | {pct(overall(item_key, 'MacroF1', ('X1',)))} | {pct(overall(item_key, 'MacroF1', ('Y1',)))} | {pct(xy_overall(item_key, 'MacroF1'))} | {pct(xy_overall(item_key, 'BalancedAccuracy'))} | {pct(xy_overall(item_key, 'WeightedF1'))} |".replace(".", ","))

    for class_name in CLASSES:
        lines.extend([
            "",
            f"#### Klass `{class_name}` – top-5",
            "",
            "| Koht | Variant | Klassiskoor | F1, X1 | Recall / TPR, X1 | F1, Y1 | Recall / TPR, Y1 | F1, X1–Y1 | Recall / TPR, X1–Y1 |",
            "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
        ])
        for position, item_key in enumerate(xy_class_top[class_name], 1):
            lines.append(f"| {position} | {display(item_key)} | {xy_class_score(item_key, class_name) * 100:.2f} | {pct(class_value(item_key, class_name, 'F1', ('X1',)))} | {pct(class_value(item_key, class_name, 'Recall_TPR', ('X1',)))} | {pct(class_value(item_key, class_name, 'F1', ('Y1',)))} | {pct(class_value(item_key, class_name, 'Recall_TPR', ('Y1',)))} | {pct(xy_class_value(item_key, class_name, 'F1'))} | {pct(xy_class_value(item_key, class_name, 'Recall_TPR'))} |".replace(".", ","))

    lines.extend([
        "",
        "#### Klassitop-5-st üldisest top-10-st välja jäänud variandid",
        "",
        "| Variant | Jõudis klassi top-5 hulka | Üldine koondskoor |",
        "|---|---|---:|",
    ])
    for item_key in xy_class_only:
        reached = ", ".join(class_name for class_name in CLASSES if item_key in xy_class_top[class_name])
        lines.append(f"| {display(item_key)} | `{reached}` | {xy_overall_score(item_key) * 100:.2f} |".replace(".", ","))
    lines.extend(["", END])

    text = OUTPUT.read_text(encoding="utf-8")
    before, remainder = text.split(START, 1)
    _, after = remainder.split(END, 1)
    OUTPUT.write_text(before + "\n".join(lines) + after, encoding="utf-8")


if __name__ == "__main__":
    main()
