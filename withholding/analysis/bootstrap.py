"""Paired item bootstrap for the difference between two checkpoints on the same items.

Why paired: both checkpoints answer the SAME items, so item difficulty is shared. Resampling
items (not the two score vectors independently) keeps that pairing and gives a tighter, honest
interval for the delta. This is the only statistic the capstone's headline claims rest on.
"""
from __future__ import annotations

import numpy as np


def paired_bootstrap_delta(a: np.ndarray, b: np.ndarray, n_boot: int = 10_000,
                           seed: int = 13, alpha: float = 0.05) -> dict:
    """Delta = mean(b) - mean(a) with a percentile interval from paired item resampling.

    a, b: per-item scores (0/1 or floats) for checkpoint A and checkpoint B, same length,
          same item order.
    Returns dict(delta, lo, hi, n_items, p_two_sided) where p is the bootstrap share of
    resampled deltas on the other side of zero, doubled (a rough two-sided value, reported
    next to the interval, never alone).
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.shape != b.shape or a.ndim != 1:
        raise ValueError("a and b must be 1-D arrays of the same length (same items, same order)")
    n = a.size
    if n == 0:
        raise ValueError("no items")
    rng = np.random.default_rng(seed)
    diff = b - a
    idx = rng.integers(0, n, size=(n_boot, n))
    boots = diff[idx].mean(axis=1)
    delta = float(diff.mean())
    lo, hi = np.percentile(boots, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    share_other_side = float(np.mean(boots <= 0) if delta > 0 else np.mean(boots >= 0))
    return {
        "delta": delta,
        "lo": float(lo),
        "hi": float(hi),
        "n_items": int(n),
        "p_two_sided": min(1.0, 2 * share_other_side),
    }


def stage_deltas(scores_by_stage: dict[str, np.ndarray], order: list[str], **kw) -> list[dict]:
    """Consecutive deltas along a lineage. scores_by_stage maps stage name to per-item scores
    aligned on the same items. Returns one dict per consecutive pair, in order."""
    out = []
    for prev, nxt in zip(order[:-1], order[1:]):
        d = paired_bootstrap_delta(scores_by_stage[prev], scores_by_stage[nxt], **kw)
        d.update({"from": prev, "to": nxt})
        out.append(d)
    return out
