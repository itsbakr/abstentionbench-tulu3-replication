"""Files of record are never overwritten (CLAUDE.md, "Files per run": "Nothing is overwritten; re-runs skip ids
already present"; design rule 5: "the runner refuses to append to a file built from a different prompt").

17 Oct 2026 (typed design, step 2a fixer). The score and judge-prompt writers (`withholding.score.programmatic`,
`judged`, `abstention_judge`) opened their target with "w" and then validated row by row, so a row the typed layer
refused, or a judge prompt that was not the rule D request, left the stored file truncated. Every writer now goes
through `RecordWriter`: the lines go to a temporary file beside the target, and only a run that finished is reconciled
with the target, which is

- written (through a rename) when it does not exist or is empty;
- left as it is when it already holds exactly these lines ("unchanged");
- appended to when each of its lines is one of these lines (an earlier run of the same writer cut short): its lines
  stay byte for byte, the missing ones follow, through a rename;
- refused otherwise (`RecordFileRefused`), with nothing written: the file was built under another reading, version or
  prompt. A re-score or re-judge writes new file names, and stored score files move only by an incremental rescoring
  with a changelog (`scripts/rescore_rule_d_2a.py`, then one script per rule D step: `scripts/rescore_rule_d_2b.py`,
  `scripts/rescore_rule_d_2c.py`, `scripts/rescore_rule_d_2d.py`).

A run that raises leaves the target untouched and removes its temporary file.
"""
from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Self

RESCORING = ("scripts/rescore_rule_d_2a.py, scripts/rescore_rule_d_2b.py, "   # one per rule D step so far
             "scripts/rescore_rule_d_2c.py, scripts/rescore_rule_d_2d.py")


class RecordFileRefused(FileExistsError):
    """The target holds a line this writer would not write; nothing was written."""


def _digest(line: bytes) -> bytes:
    return hashlib.sha256(line).digest()


def _lines(path: Path) -> Iterator[bytes]:
    """The non-blank lines of `path`, as bytes without their newline."""
    with open(path, "rb") as f:
        for raw in f:
            line = raw.rstrip(b"\n")
            if line.strip():
                yield line


def existing_lines(path: str | Path) -> list[str]:
    """The non-blank lines a target already holds, as written ([] when it does not exist), for a writer that skips
    the ids already present before it spends a call (withholding.score.judged.main) and writes them back unchanged."""
    p = Path(path)
    return [x.decode("utf-8") for x in _lines(p)] if p.exists() else []


def _describe(line: bytes) -> str:
    try:
        r = json.loads(line)
    except ValueError:
        return f"an unreadable line ({line[:60]!r})"
    return ", ".join(f"{k} {r[k]!r}" for k in ("id", "sample", "scorer") if k in r) or "a line without an id"


def refusal(target: Path, line: bytes, n: int, writer: str) -> RecordFileRefused:
    """The refusal of a target holding `n` lines `writer` would not write, the first of them `line`."""
    return RecordFileRefused(
        f"{target}: holds {n} line(s) {writer} would not write (first: {_describe(line)}); nothing was written. A "
        "file of record is never overwritten: a re-score or re-judge writes new file names, and stored score files "
        f"move only by an incremental rescoring with a changelog ({RESCORING}).")


class RecordWriter:
    """Write the lines of one file of record (module docstring): `write(line)` per line (no newline), then, on a
    clean exit, the target is reconciled and `outcome` says how ("written n", "unchanged", "appended n")."""

    def __init__(self, target: str | Path, writer: str):
        self.target = Path(target)
        self.writer = writer
        self.tmp = self.target.with_name(f".{self.target.name}.{os.getpid()}.tmp")
        self.n = 0
        self.outcome: str | None = None
        self._f = None

    def __enter__(self) -> Self:
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self._f = open(self.tmp, "w", encoding="utf-8")
        return self

    def write(self, line: str) -> None:
        if "\n" in line:
            raise ValueError("a record line holds no newline")
        self._f.write(line + "\n")
        self.n += 1

    def __exit__(self, exc_type, exc, tb) -> bool:
        self._f.close()
        try:
            if exc_type is None:
                self.outcome = self._reconcile()
        finally:
            if self.tmp.exists():
                self.tmp.unlink()
        return False

    def _reconcile(self) -> str:
        if not self.target.exists() or not any(True for _ in _lines(self.target)):
            os.replace(self.tmp, self.target)
            return f"written {self.n}"
        old = [_digest(x) for x in _lines(self.target)]
        new = [_digest(x) for x in _lines(self.tmp)]
        if old == new:
            return "unchanged"
        extra = Counter(old) - Counter(new)
        if extra:
            first = next(x for x in _lines(self.target) if _digest(x) in extra)
            raise refusal(self.target, first, sum(extra.values()), self.writer)
        have = Counter(old)
        part = self.target.with_name(f".{self.target.name}.{os.getpid()}.part")
        try:
            with open(part, "wb") as out:
                out.writelines(x + b"\n" for x in _lines(self.target))
                n = 0
                for x in _lines(self.tmp):
                    d = _digest(x)
                    if have[d]:
                        have[d] -= 1
                        continue
                    out.write(x + b"\n")
                    n += 1
            os.replace(part, self.target)
        finally:
            if part.exists():
                part.unlink()
        return f"appended {n}"
