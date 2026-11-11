#!/usr/bin/env python3
"""Koosta MODIFIED- ja REJECTED-klassi top-5 F1/recall SVG-joonised."""

from __future__ import annotations

import csv
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
COHORTS = ("B1", "B2", "C1", "D1", "X1", "Y1")
PATHS = {
    "B1": ROOT / "log/oct-HlIJvh_test1_octave/perclass_test1_octave.csv",
    "B2": ROOT / "log/oct-rdhW8P_test2_octave/perclass_test2_octave.csv",
    "C1": ROOT / "log/oct-yxbe3l_c1_octave/perclass_c1_octave.csv",
    "D1": ROOT / "log/oct-3bqqzd_d1_octave/perclass_d1_octave.csv",
    "X1": ROOT / "log/oct-bshFjj_x1_octave/perclass_x1_octave.csv",
    "Y1": ROOT / "log/oct-OKMtsB_y1_octave/perclass_y1_octave.csv",
}
B1_UPDATE = ROOT / "log/oct-TmAUoK_test1_octave/perclass_test1_octave.csv"
TOP = {
    "MODIFIED": [
        ("SVM Kernel", "duration_s"),
        ("KNN k=7 equal", "duration_s"),
        ("KNN k=21 inverse", "duration_s"),
        ("KNN k=7 inverse", "show_speaker_count"),
        ("KNN k=7 equal", "show_speaker_count"),
    ],
    "REJECTED": [
        ("KNN k=10 inverse", "show_speaker_count"),
        ("SVM Kernel", "duration_s"),
        ("KNN k=5 equal", "show_speaker_count"),
        ("KNN k=10 inverse", "duration_s"),
        ("KNN k=7 inverse", "show_speaker_count"),
    ],
}
COLORS = ("#1769aa", "#e07026", "#8f2d8b", "#1b8d63", "#b74444")
PLOT_LEFT, PLOT_RIGHT, PLOT_TOP, PLOT_BOTTOM = 300, 1240, 140, 650
X = dict(zip(COHORTS, (370, 520, 670, 820, 970, 1120)))


def read(path: Path) -> dict[tuple[str, str, str], dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {(row["Model"], row["Variant"], row["Class"]): row for row in csv.DictReader(handle)}


def y(value: float) -> float:
    return PLOT_BOTTOM - value / 100 * (PLOT_BOTTOM - PLOT_TOP)


def path(values: list[float]) -> str:
    return " ".join(("M" if i == 0 else "L") + f"{X[cohort]} {y(value):.1f}" for i, (cohort, value) in enumerate(zip(COHORTS, values)))


def label(model: str, variant: str) -> str:
    suffix = "kõik 8 atribuuti" if variant == "full" else f"{variant} eemaldatud"
    return f"{model}, {suffix}"


def chart(class_name: str, rows: dict[str, dict[tuple[str, str, str], dict[str, str]]]) -> str:
    top = TOP[class_name]
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="780" viewBox="0 0 1400 780">',
        '<style>text{font-family:Arial,sans-serif;fill:#172033}.title{font-size:28px;font-weight:700}.axis{font-size:16px;fill:#516176}.legend{font-size:14px;font-weight:600}.grid{stroke:#d9e1ea;stroke-width:1}.line{fill:none;stroke-width:3.5;stroke-linecap:round;stroke-linejoin:round}.recall{fill:none;stroke-width:2.5;stroke-dasharray:8 6;opacity:.88}</style>',
        '<rect width="1400" height="780" fill="#fff"/>',
        f'<text x="55" y="45" class="title">{class_name}: F1 ja Recall / TPR viie parima mudeli puhul</text>',
    ]
    for tick in range(100, 49, -10):
        yy = y(tick)
        lines.append(f'<line x1="{PLOT_LEFT}" y1="{yy:.1f}" x2="{PLOT_RIGHT}" y2="{yy:.1f}" class="grid"/><text x="246" y="{yy + 6:.1f}" class="axis">{tick}%</text><text x="1252" y="{yy + 6:.1f}" class="axis">{tick}%</text>')
    lines.extend([
        '<line x1="175" y1="425" x2="175" y2="475" stroke="#8a96a6" stroke-width="3"/><text x="175" y="360" class="axis" transform="rotate(-90 175 360)">F1 (%)</text>',
        '<line x1="1340" y1="245" x2="1340" y2="295" stroke="#8a96a6" stroke-width="3" stroke-dasharray="8 6"/><text x="1340" y="360" class="axis" transform="rotate(90 1340 360)">Recall / TPR (%)</text>',
    ])
    for cohort in COHORTS:
        lines.append(f'<text x="{X[cohort] - 10}" y="687" class="axis">{cohort}</text>')
    for (model, variant), color in zip(top, COLORS):
        f1 = [float(rows[cohort][(model, variant, class_name)]["F1"]) * 100 for cohort in COHORTS]
        recall = [float(rows[cohort][(model, variant, class_name)]["Recall_TPR"]) * 100 for cohort in COHORTS]
        lines.append(f'<path d="{path(f1)}" class="line" stroke="{color}"/><path d="{path(recall)}" class="recall" stroke="{color}"/>')
        for cohort, value in zip(COHORTS, f1):
            lines.append(f'<circle cx="{X[cohort]}" cy="{y(value):.1f}" r="6" fill="{color}" stroke="#fff" stroke-width="2"/>')
        for cohort, value in zip(COHORTS, recall):
            lines.append(f'<rect x="{X[cohort] - 5}" y="{y(value) - 5:.1f}" width="10" height="10" fill="{color}" stroke="#fff" stroke-width="2"/>')
    top_set = set(top)
    for cohort in COHORTS:
        class_rows = [row for key, row in rows[cohort].items() if key[2] == class_name]
        for metric, tag in (("F1", "circle"), ("Recall_TPR", "rect")):
            best = max(float(row[metric]) for row in class_rows)
            winners = [key for key, row in rows[cohort].items() if key[2] == class_name and float(row[metric]) == best]
            if not any((model, variant) in top_set for model, variant, _ in winners):
                yy = y(best * 100)
                if tag == "circle":
                    lines.append(f'<circle cx="{X[cohort]}" cy="{yy:.1f}" r="8" fill="#d92525" stroke="#fff" stroke-width="2"/>')
                else:
                    lines.append(f'<rect x="{X[cohort] - 7}" y="{yy - 7:.1f}" width="14" height="14" fill="#d92525" stroke="#fff" stroke-width="2"/>')
    for i, ((model, variant), color) in enumerate(zip(top, COLORS)):
        x = 55 if i in (0, 3) else 430 if i in (1, 4) else 790
        yy = 720 if i < 3 else 748
        lines.append(f'<line x1="{x}" y1="{yy}" x2="{x + 27}" y2="{yy}" class="line" stroke="{color}"/><text x="{x + 37}" y="{yy + 6}" class="legend">{i + 1}. {escape(label(model, variant))}</text>')
    lines.append('<circle cx="1040" cy="741" r="7" fill="#d92525"/><rect x="1053" y="734" width="14" height="14" fill="#d92525"/><text x="1078" y="746" class="legend">Parim muu mudel</text></svg>')
    return "\n".join(lines)


def main() -> None:
    rows = {cohort: read(path) for cohort, path in PATHS.items()}
    rows["B1"].update(read(B1_UPDATE))
    output_dir = ROOT / "docs/kursusetoo"
    for class_name in TOP:
        (output_dir / f"{class_name.lower()}_top5_f1_recall_kuus_katset.svg").write_text(chart(class_name, rows), encoding="utf-8")


if __name__ == "__main__":
    main()
