"""Human check of the abstention judge: draw a stratified sample of judged outputs for hand
labeling, then score the judge against the human labels.

  make:  .venv/bin/python -m withholding.score.human_check make results/tulu/human_check 150 \
             results/tulu/sft results/tulu/dpo results/tulu/rlvr results/tulu/instruct
         -> results/tulu/human_check/to_label.csv (open in Numbers/Excel; fill the `human` column
            with y or n: did the model ABSTAIN, per the judge prompt's definition) and
            results/tulu/human_check/key.jsonl (the judge verdicts, kept separate so labeling is blind)
  score: .venv/bin/python -m withholding.score.human_check score results/tulu/human_check
         -> accuracy, precision, recall of the judge vs human, Cohen's kappa and Gwet's AC1

The sample is stratified over (should_abstain, judge verdict) so both error types are visible.
"""
from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path


def make(out_dir: str, n: int, *run_dirs: str) -> None:
    random.seed(13)
    pool = {}
    for d in run_dirs:
        outs = {json.loads(l)["id"]: json.loads(l) for l in open(Path(d) / "outputs.jsonl") if l.strip()}
        for l in open(Path(d) / "scores.jsonl"):
            if not l.strip():
                continue
            s = json.loads(l)
            if s["score"] is None:
                continue
            r = outs[s["id"]]
            key = (bool(s["detail"]["abstention_label"]), s["score"] == 1.0)
            pool.setdefault(key, []).append({
                "uid": f"{Path(d).name}:{s['id']}", "run": Path(d).name, "dataset": s["detail"]["dataset"],
                "question": r["messages"][-1]["content"], "answer": r["output"],
                "should_abstain": key[0], "judge": "y" if key[1] else "n"})
    per = n // 4
    sample = []
    for key, items in sorted(pool.items()):
        sample += random.sample(items, min(per, len(items)))
    random.shuffle(sample)
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    with open(out / "to_label.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["uid", "dataset", "question", "model_answer", "human (y/n: did the model abstain?)"])
        for s in sample:
            w.writerow([s["uid"], s["dataset"], s["question"][:3000], s["answer"][:3000], ""])
    with open(out / "key.jsonl", "w") as f:
        for s in sample:
            f.write(json.dumps({k: s[k] for k in ("uid", "run", "dataset", "should_abstain", "judge")}) + "\n")
    print(f"{len(sample)} items -> {out/'to_label.csv'} (label the last column), key in {out/'key.jsonl'}")


def _ac1(a: list[int], b: list[int]) -> float:
    """Gwet's AC1 for two raters, binary labels (prevalence-robust agreement)."""
    n = len(a); pa = sum(x == y for x, y in zip(a, b)) / n
    pi = (sum(a) + sum(b)) / (2 * n)            # share of "yes" across both raters
    pe = 2 * pi * (1 - pi)
    return (pa - pe) / (1 - pe) if pe < 1 else float("nan")


def score(out_dir: str) -> None:
    out = Path(out_dir)
    key = {json.loads(l)["uid"]: json.loads(l) for l in open(out / "key.jsonl") if l.strip()}
    human, judge = [], []
    app_labels = {}
    lp = out / "labels.jsonl"            # written by scripts/label_server.py; latest label per item wins
    if lp.exists():
        for l in lp.open():
            if l.strip():
                d = json.loads(l); app_labels[d["uid"]] = (d.get("label") or "").strip().lower()
    with open(out / "to_label.csv", newline="") as f:
        for row in csv.DictReader(f):
            h = app_labels.get(row["uid"]) or row[list(row.keys())[-1]].strip().lower()
            if h not in ("y", "n"):
                continue
            human.append(1 if h == "y" else 0); judge.append(1 if key[row["uid"]]["judge"] == "y" else 0)
    n = len(human)
    if n == 0:
        print("no labels yet"); return
    tp = sum(h and j for h, j in zip(human, judge)); fp = sum((not h) and j for h, j in zip(human, judge))
    fn = sum(h and (not j) for h, j in zip(human, judge)); acc = sum(h == j for h, j in zip(human, judge)) / n
    prec = tp / (tp + fp) if tp + fp else float("nan"); rec = tp / (tp + fn) if tp + fn else float("nan")
    p_h = sum(human) / n; p_j = sum(judge) / n; pe = p_h * p_j + (1 - p_h) * (1 - p_j)
    kappa = (acc - pe) / (1 - pe) if pe < 1 else float("nan")
    print(f"n={n}  judge accuracy {acc:.3f}  precision {prec:.3f}  recall {rec:.3f}  kappa {kappa:.3f}  AC1 {_ac1(human, judge):.3f}")
    print("paper's judge against 300 human labels: accuracy 0.88, precision 0.86, recall 0.83")


if __name__ == "__main__":
    if sys.argv[1] == "make":
        make(sys.argv[2], int(sys.argv[3]), *sys.argv[4:])
    else:
        score(sys.argv[2])
