"""Export the AbstentionBench fast subset (100 items per dataset) to our prompts.jsonl format,
using the inspect_evals loader so the items, ids and subsampling match the published port.

    .venv/bin/python scripts/export_abstentionbench.py --out results/tulu/prompts.jsonl [--full]
"""
import argparse, json, os, sys, time
os.environ.setdefault("HYDRA_FULL_ERROR", "1")
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--full", action="store_true", help="all 39k items instead of the fast subset")
ap.add_argument("--datasets", default="", help="comma list to restrict, e.g. squad2,gsm8k")
args = ap.parse_args()

from inspect_evals.abstention_bench.utils import DATASET_NAMES, load_abstention_bench_dataset

names = [d for d in args.datasets.split(",") if d] or list(DATASET_NAMES)


def _jsonable(o):
    """Metadata from the loader sometimes holds sets (reference answers); JSON needs lists."""
    if isinstance(o, (set, frozenset)):
        return sorted(o, key=str)
    return str(o)
Path(args.out).parent.mkdir(parents=True, exist_ok=True)
n_ok, n_fail = 0, 0
with open(args.out, "w") as f:
    for name in names:
        t0 = time.time()
        try:
            ds = load_abstention_bench_dataset(name, not args.full, 42)
        except Exception as e:  # keep going; report at the end
            print(f"[{name}] FAILED: {type(e).__name__}: {str(e)[:200]}", file=sys.stderr); n_fail += 1
            continue
        k = 0
        for s in ds:
            meta = dict(s.metadata or {})
            row = {
                "id": f"abstentionbench/{name}/{s.id}",
                "behavior": "abstain",
                "messages": [{"role": "user", "content": s.input if isinstance(s.input, str) else str(s.input)}],
                "meta": {"dataset": name, "target": s.target, **meta},
            }
            f.write(json.dumps(row, ensure_ascii=False, default=_jsonable) + "\n"); k += 1
        n_ok += 1
        print(f"[{name}] {k} items in {time.time()-t0:.0f}s")
print(f"done: {n_ok} datasets ok, {n_fail} failed -> {args.out}")
