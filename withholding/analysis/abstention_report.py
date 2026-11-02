"""Per-dataset abstention recall per stage, stage-to-stage deltas with the paired item bootstrap,
and a comparison against the numbers in AbstentionBench's own results file.

    .venv/bin/python -m withholding.analysis.abstention_report \
        --stage SFT=results/tulu/sft/scores.jsonl --stage DPO=results/tulu/dpo/scores.jsonl \
        --stage RLVR=results/tulu/rlvr/scores.jsonl --out results/tulu/report.md

23 Oct 2026 (typed design, section 6 step 4; OD-3, D7, D18): after its tables the report appends the typed cells of the
two AbstentionBench rates per stage in their three views and the consecutive deltas with their bounds and quoted forms
(withholding.analysis.typed_views.tulu_section); --no-typed leaves them out.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from itertools import pairwise
from pathlib import Path

import numpy as np

from withholding.analysis.bootstrap import paired_bootstrap_delta

HERE = Path(__file__).resolve().parents[2]
CSV = HERE / "third_party" / "abstentionbench" / "abstention_performance.csv"
# our export's dataset keys -> the results file's dataset_name_formatted (one row each; datasets
# with several scenarios in the file, like CoCoNot and KUQ, are pooled on our side)
PAPER_NAMES = {"squad2": ["SQuAD 2.0"], "musique": ["Musique"], "mmlu_math": ["MMLU Math"],
               "gsm8k": ["GSM8K"], "umwp": ["UMWP"], "qaqa": ["QAQA"], "falseqa": ["FalseQA"],
               "freshqa": ["FreshQA"], "bbq": ["BBQ"], "alcuna": ["ALCUNA"], "mediq": ["MediQ"],
               "moralchoice": ["MoralChoice"], "qasper": ["QASPER"], "worldsense": ["WorldSense"],
               "gpqa": ["GPQA-Diamond"], "mmlu_history": ["MMLU History"],
               "situated_qa": ["SituatedQA/Geo"], "big_bench_disambiguate": ["BB/Disambiguate"],
               "big_bench_known_unknowns": ["BB/Known unknowns"],
               "coconot": ["CoCoNot/False presumptions", "CoCoNot/Humanizing", "CoCoNot/Incomprehensible",
                           "CoCoNot/Subjective", "CoCoNot/Temporal", "CoCoNot/Unknowns", "CoCoNot/Unsupported"],
               "kuq": ["KUQ/Ambiguous", "KUQ/Controversial", "KUQ/False assumptions", "KUQ/Future unknowns",
                       "KUQ/Unsolved problems"]}
PAPER_STAGE = {"Base": "Llama 3.1 8B Base", "SFT": "Llama 3.1 8B Tulu 3 SFT", "DPO": "Llama 3.1 8B Tulu 3 DPO",
               "RLVR": "Llama 3.1 8B Tulu 3 PPO RLVF", "Instruct": "Llama 3.1 8B Instruct"}


def paper_recall(stage: str) -> dict[str, float]:
    with open(CSV) as fh:
        rows = list(csv.DictReader(fh))
    want = PAPER_STAGE.get(stage)
    out = {}
    for ours, theirs in PAPER_NAMES.items():
        vals = [float(r["recall"]) for r in rows if r["model_name_formatted"] == want and r["dataset_name_formatted"] in theirs]
        if vals:
            out[ours] = float(np.mean(vals))
    return out


def score_lines(path: str, arm: str | None = None) -> list[dict]:
    """The lines of an abstention score file in stored order; with `arm` (25 Oct 2026; D25's label_blind_all) each
    delivered line carries that arm's verdict on the same delivered text instead (its line in the same directory,
    withholding.typed.step3.LLAMA_ARMS, matched by id and subject sample; withholding.analysis.cascade_report.with_arm
    refuses a delivered row without a line and a line for an undelivered row or for no row), and an undelivered line
    (no_answer) is kept as it is: the arm judges delivered rows only."""
    with open(path) as fh:
        rows = [json.loads(x) for x in fh if x.strip()]
    if arm is None:
        return rows
    from withholding.analysis.cascade_report import with_arm
    keyed = with_arm(Path(path).parent, {(r["id"], r["detail"].get("subject_sample", 0)): r for r in rows}, arm)
    return [keyed[(r["id"], r["detail"].get("subject_sample", 0))] for r in rows]


def load_scores(path: str, arm: str | None = None):
    """Returns per-item mean score over samples for should-abstain items, keyed by item id,
    plus per-dataset answered/abstained counts for precision. `arm`: score_lines'."""
    per_item = defaultdict(list)
    info = {}
    for r in score_lines(path, arm):
        if r["score"] is None:
            continue
        per_item[r["id"]].append(r["score"])
        info[r["id"]] = (r["detail"]["dataset"], bool(r["detail"]["abstention_label"]))
    return {k: float(np.mean(v)) for k, v in per_item.items()}, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", action="append", required=True, help="NAME=path/to/scores.jsonl, in lineage order")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-typed", action="store_true", help="leave out step 4's typed cells")
    args = ap.parse_args()
    stages = [s.split("=", 1) for s in args.stage]
    data = {name: load_scores(path) for name, path in stages}
    names = [n for n, _ in stages]
    datasets = sorted({d for _, info in data.values() for d, _ in info.values()})

    lines = [f"# AbstentionBench report ({', '.join(names)})", "",
             "Recall = share of should-abstain items the judge marked as abstention (mean over samples per item).",
             "Paper = the same number from AbstentionBench's results file for the matching Tülu 3 8B stage (scenarios pooled by mean).", ""]
    # recall table
    lines.append("| dataset | n should-abstain | " + " | ".join(f"{n} ours / paper" for n in names) + " |")
    lines.append("|---|---|" + "---|" * len(names))
    paper = {n: paper_recall(n) for n in names}
    pooled = {n: [] for n in names}
    for d in datasets:
        cells = []
        n_items = 0
        for n in names:
            scores, info = data[n]
            ids = [i for i, (dd, lab) in info.items() if dd == d and lab]
            n_items = len(ids)
            vals = [scores[i] for i in ids]
            pooled[n].extend(vals)
            ours = np.mean(vals) if vals else float("nan")
            p = paper[n].get(d)
            cells.append(f"{ours:.3f} / {p:.3f}" if p is not None else f"{ours:.3f} / -")
        lines.append(f"| {d} | {n_items} | " + " | ".join(cells) + " |")
    lines.append("| **pooled (all should-abstain items)** | | " + " | ".join(f"{np.mean(pooled[n]):.3f}" for n in names) + " |")
    lines.append("| **mean over datasets (paper's headline)** | | " + " | ".join(
        f"{np.mean([np.mean([data[n][0][i] for i,(dd,lab) in data[n][1].items() if dd==d and lab]) for d in datasets]):.3f} / {np.mean(list(paper[n].values())):.3f}" if paper[n] else "-" for n in names) + " |")
    # deltas
    lines += ["", "## Stage-to-stage deltas (paired item bootstrap over should-abstain items, 10,000 resamples)", "",
              "| from -> to | n items | delta | 95% interval |", "|---|---|---|---|"]
    for a, b in pairwise(names):
        sa, ia = data[a]; sb, _ib = data[b]
        ids = [i for i in ia if i in sb and ia[i][1]]
        if not ids:
            continue
        d = paired_bootstrap_delta(np.array([sa[i] for i in ids]), np.array([sb[i] for i in ids]))
        lines.append(f"| {a} -> {b} | {d['n_items']} | {d['delta']:+.3f} | [{d['lo']:+.3f}, {d['hi']:+.3f}] |")
    # precision / answer rate
    lines += ["", "## Precision and abstention rate (all items)", "", "| stage | abstention rate on answerable items (false abstentions) | precision |", "|---|---|---|"]
    for n in names:
        scores, info = data[n]
        ans = [scores[i] for i, (_, lab) in info.items() if not lab]
        yes_should = sum(scores[i] for i, (_, lab) in info.items() if lab)
        yes_all = sum(scores.values())
        lines.append(f"| {n} | {np.mean(ans) if ans else float('nan'):.3f} | {yes_should / yes_all if yes_all else float('nan'):.3f} |")
    if not args.no_typed:   # 23 Oct 2026 (step 4): the typed cells, after every table above
        from withholding.analysis import typed_views as TV
        if TV.typed_ok([Path(p).parent for _, p in stages]):
            lines += TV.tulu_section(stages, args.out)
        else:
            lines += TV.NOT_TYPED
    Path(args.out).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
