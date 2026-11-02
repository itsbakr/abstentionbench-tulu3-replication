#!/usr/bin/env python
"""The 21-dataset means behind the report's table and its level sentences (written for the public folder, 2 Nov 2026).

For each stage and each judge column it prints the recall on should-abstain items averaged over the 21 datasets that
have a paper value at all three stages (the per-dataset rows of results/tulu_n4/report.md less self_aware), the paper's
own means over the same datasets, and the two stage-to-stage differences. The per-dataset recall is the mean over items
of the per-item mean verdict, as withholding.analysis.abstention_report prints it.

    .venv/bin/python -B scripts/mean_over_21_datasets.py
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from withholding.analysis.abstention_report import load_scores, paper_recall  # noqa: E402

STAGES = ("SFT", "DPO", "RLVR")
COLUMNS = {"answer key shown": "scores.jsonl", "answer-key line removed": "scores_abstain_label_blind_all_post-2d.jsonl"}


def per_dataset(path: str) -> dict[str, float]:
    scores, info = load_scores(path)
    by = defaultdict(list)
    for item, s in scores.items():
        dataset, should_abstain = info[item]
        if should_abstain:
            by[dataset].append(s)
    return {d: float(np.mean(v)) for d, v in by.items()}


def main() -> None:
    paper = {s: paper_recall(s) for s in STAGES}
    shared = sorted(set.intersection(*(set(paper[s]) for s in STAGES)))
    print(f"datasets with a paper value at all three stages: {len(shared)}")
    rows = {"paper": [float(np.mean([paper[s][d] for d in shared])) for s in STAGES]}
    for name, fname in COLUMNS.items():
        ours = {s: per_dataset(f"results/tulu_n4/{s.lower()}/{fname}") for s in STAGES}
        missing = [d for d in shared if any(d not in ours[s] for s in STAGES)]
        assert not missing, missing
        rows[f"mine, {name}"] = [float(np.mean([ours[s][d] for d in shared])) for s in STAGES]
    print(f"{'':30s} {'SFT':>7s} {'DPO':>7s} {'RLVR':>7s} {'SFT to DPO':>11s} {'DPO to RLVR':>12s}")
    for name, v in rows.items():
        print(f"{name:30s} {v[0]:7.3f} {v[1]:7.3f} {v[2]:7.3f} {v[1]-v[0]:+11.3f} {v[2]-v[1]:+12.3f}")


if __name__ == "__main__":
    main()
