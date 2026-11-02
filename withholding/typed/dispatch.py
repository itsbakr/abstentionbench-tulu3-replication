"""Step 1's dispatcher (design `notes/typed_ingestion_design_2026-10-15.md`, 2.4 and section 6 step 1): a stored
output row in, today's score line out, through a typed entry.

A typed entry takes (text, gold) and nothing else (design 2.0). What a body must not see is handled here:
- `type_stored_row` classifies the stored row (`ingest.classify_stored_row`, kept in the store), registers its frozen
  14 Oct reading (`ingest.register_legacy`), and builds its typed gold (`adapters.prompt_record`) and its row identity
  (`models.LegacyRowIdentity`, design 2.4's table: id, sample with default 0, behavior, model, subfolder, thinking).
- `legacy_line` issues the entry's text (`ingest.read_legacy` under the entry's `legacy_binding`), calls the entry, and
  appends the row identity after the body's keys, as `withholding.score.programmatic.score_row` does with
  `row_identity`; so the line serializes byte-identical to today's (design 2.5a: the identity cannot ride in the body,
  which never sees it).

Step 2a (17 Oct 2026) adds the rule D dispatch: `delivered` gives a typed row's DeliveredText under a rule id, or the
undelivered reason checked against the grants, and `rule_d_line` writes the line of a rule D entry, or the no_answer
body itself when nothing was delivered (design 2.4: a dispatcher, not the scorer, writes no_answer). The legacy
entries above serve step 1's proof only. The caller drops each completion from the store (`ingest.forget`) when its
line is written. Step 5 (25 Oct 2026) adds `reliablemath_record`, the typed ScoreRecord of that line for the
ReliableMath group, which the C reward and the evaluation of a stored row both project (OD-4).

The directory section below serves step 1's writer replay (`withholding/typed/replay.py`,
`scripts/typed_replay_scores.py`): `DirectoryDispatch` types a directory's output files once and checks every row
against its step 0 sidecar line; `score_line` and `serialize_line` write a typed entry's line through the per-family
LegacyScoreLine table (design 2.5a); `empty_output_line` is Batch A's empty-completion no_answer path on typed inputs,
which the replay applies only where a directory's mark_empty_completions changelog says it ran; `cache_only_judge`
answers the Gemini judge from cached replies and raises on any other prompt.

Step 6 (25 Oct 2026; design section 6 step 6, plan W7.2): a row no sidecar line covers is typed through the runner's
ingestion stamp it carries (`ingest.RUNNER_ROW_FIELDS`, checked against the typed reading), and refused
(`IngestionRefused`) when it carries none; `ingestion_basis` says which of the two types a directory, for the report
readers (`withholding.analysis.typed_views.typed_ok`).
"""
from __future__ import annotations

import contextlib
import gzip
import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from withholding.typed import adapters, ingest, models

RESULTS = Path(__file__).resolve().parents[2] / "results"


@dataclass(frozen=True)
class TypedRow:
    """One stored output row as a typed entry's dispatcher holds it: the completion key (in ingest's store, with its
    legacy reading registered), the prompt's typed gold, the row identity written after the body, the Completion's
    finish_reason (the no_answer body of step 2a's dispatcher writes `truncated` from it; no scorer reads it from
    here) and its spec id (read by `reliablemath_record` only)."""

    key: str
    gold: Any
    identity: models.LegacyRowIdentity
    finish_reason: str = "not_recorded"
    spec_id: str | None = None   # the Completion's TemplateSpec id (step 5: a ScoreRecord carries it, design 2.5)


def draw_of(path: str | os.PathLike, results: str | os.PathLike = RESULTS) -> str:
    """The draw of an output file (design 2.3, Revision 4): its real path relative to results/ (or to the `results`
    root a DirectoryDispatch was given), as the backfill keys rows; a file outside it keeps its real path."""
    real = Path(os.path.realpath(path))
    try:
        return real.relative_to(os.path.realpath(results)).as_posix()
    except ValueError:
        return real.as_posix()


def identity_of(row: Mapping[str, Any]) -> models.LegacyRowIdentity:
    """The row identity today's dispatchers write after a body (`withholding/score/programmatic.py` row_identity):
    id, sample (0 where the row has none), behavior, model, subfolder, thinking."""
    return models.LegacyRowIdentity(id=row["id"], sample=row.get("sample", 0), behavior=row.get("behavior"),
                                    model=row.get("model"), subfolder=row.get("subfolder"),
                                    thinking=row.get("thinking"))


def type_stored_row(row: Mapping[str, Any], *, draw: str, registry: Any,
                    ext_cap_first_pass: int | None = None) -> TypedRow:
    """Classify a stored output row read from the output file `draw` and register its frozen reading; IngestError
    (with the row id) for a row the typed layer refuses. A row of an extended pass's own outputs_ext.jsonl takes its
    merged twin's cap_first_pass (`adapters.merged_twin_caps`; D17)."""
    return _type_row(row, draw=draw, registry=registry, ext_cap_first_pass=ext_cap_first_pass)[0]


def _type_row(row: Mapping[str, Any], *, draw: str, registry: Any,
              ext_cap_first_pass: int | None = None) -> tuple[TypedRow, dict]:
    """`type_stored_row`, with the classification's extras (`ingest.classify_stored_row`: the sidecar line the
    backfill would write for the row, without its file, line and prompt token hash)."""
    ext = {} if ext_cap_first_pass is None else {"ext_cap_first_pass": ext_cap_first_pass}
    c, x = ingest.classify_stored_row(row, draw=draw, registry=registry, keep=True, **ext)
    ingest.register_legacy(c.key, row)
    return TypedRow(key=c.key, gold=adapters.prompt_record(row).gold, identity=identity_of(row),
                    finish_reason=c.finish_reason, spec_id=c.spec_id), x


def delivered(t: TypedRow, rule_id: str) -> tuple[Any, str | None]:
    """(DeliveredText, None) or (None, undelivered reason) of a typed row under `rule_id` (ingest.deliver); for an
    undelivered row the reason is checked against the grants (models.NoAnswerRecord: a `reason:` line registers it)."""
    dt, reason = ingest.deliver(t.key, rule_id)
    if dt is None:
        models.NoAnswerRecord(completion_key=t.key, rule_id=rule_id, undelivered_reason=reason)
    return dt, reason


def rule_d_line(t: TypedRow, entry: Callable[..., dict], rule_id: str) -> dict:
    """One programmatic score line under rule D (design 2.4, step 2a): the entry on the row's DeliveredText and its
    gold when the row delivers, else the dispatcher's no_answer body (`programmatic.no_answer_body_rule_d`, with the
    undelivered reason; no scorer is called); then the row identity. An entry that writes its own layout names its
    no_answer body as `entry.no_answer_body` (step 2e: ImpossibleBench v4, `programmatic.no_answer_body_impossible_v4`),
    called the same way without the family."""
    s, _, _ = _rule_d_body(t, entry, rule_id)
    s.update(t.identity.model_dump())
    return s


def _rule_d_body(t: TypedRow, entry: Callable[..., dict], rule_id: str) -> tuple[dict, Any, str | None]:
    """(body, DeliveredText or None, undelivered reason or None) of `rule_d_line`, before the row identity."""
    from withholding.score import programmatic as P

    if getattr(entry, "reads", None) != "DeliveredText":
        raise TypeError(f"{getattr(entry, '__name__', entry)} is not a rule D entry")
    dt, reason = delivered(t, rule_id)
    if dt is None:
        own = getattr(entry, "no_answer_body", None)
        if own is not None:
            s = own(t.gold, finish_reason=t.finish_reason, reason=reason, rule_id=rule_id)
        else:
            family = models.family_of(ingest.split_key(t.key).prompt_id)
            s = P.no_answer_body_rule_d(family, t.gold, finish_reason=t.finish_reason, reason=reason, rule_id=rule_id)
    else:
        s = entry(dt, t.gold)
    return s, dt, reason


def reliablemath_record(t: TypedRow, rule_id: str) -> models.ScoreRecord:
    """The typed ScoreRecord (design 2.5) of a ReliableMath-group row under `rule_id` (step 5, 25 Oct 2026; OD-4).

    The line is `rule_d_line`'s through the evaluation scorer of record, `programmatic.score_reliablemath_rule_d`, or
    the dispatcher's no_answer body when nothing was delivered. The record keeps its stamp as a ScorerId, its label,
    its score (None for no_answer, design 2.5), the delivered text's sha, the Completion's finish_reason and spec id,
    and the ReliableMathDetail with `matches_original_key` (`programmatic.matches_original_key`: the comparison the
    correct label uses, against the gold's original key; None when the gold has none). A no_answer record's detail
    holds solvable and the undelivered reason. The C reward (`withholding.typed.reward`) and the evaluation of a
    stored row both read this record, so one scorer serves training and evaluation."""
    from withholding.score import programmatic as P

    k = ingest.split_key(t.key)
    family = models.family_of(k.prompt_id)
    if family not in P.RELIABLEMATH_FAMILIES:
        raise ValueError(f"{t.key}: a ReliableMath record needs a ReliableMath-group prompt, not {family}")
    if t.spec_id is None:
        raise ValueError(f"{t.key}: the typed row carries no spec id")
    s, dt, reason = _rule_d_body(t, P.score_reliablemath_rule_d, rule_id)
    sid = P.rule_d_scorer("reliablemath/boxed", rule_id)
    if s["scorer"] != sid.stamp:
        raise ValueError(f"{t.key}: the line's stamp {s['scorer']} is not {sid.stamp}")
    d = s["detail"]
    if dt is None:
        label, score, sha = "no_answer", None, None
        detail = {"solvable": d["solvable"], "undelivered_reason": reason}
    else:
        label, score, sha = s["label"], float(s["score"]), dt.text_sha
        detail = {"boxed": d["boxed"], "solvable": d["solvable"], "admitted": d["admitted"], "idk": d["idk"],
                  "matches_original_key": P.matches_original_key(d["boxed"], d["admitted"], d["idk"], t.gold)}
    return models.ScoreRecord(completion_key=t.key, prompt_id=k.prompt_id, sample=k.sample, run_id=k.run_id,
                              spec_id=t.spec_id, family=family, scorer=sid, label=label, score=score,
                              delivered_sha=sha, finish_reason=t.finish_reason, verdict_ref=None, detail=detail)


def legacy_text(t: TypedRow, entry: Callable[..., dict]) -> Any:
    """The sealed LegacyReadText `entry` reads on this row: the view its legacy binding picks."""
    return ingest.read_legacy(t.key, entry.legacy_binding)


def legacy_line(t: TypedRow, entry: Callable[..., dict]) -> dict:
    """entry(text, gold) followed by the row identity: one score line as today's writer builds it."""
    s = entry(legacy_text(t, entry), t.gold)
    s.update(t.identity.model_dump())
    return s


# ========================================================================= directory dispatch (step 1's writer replay)
# The writers step 1's proof replays (design section 6 step 1, proof 1, "Writer sequence"; the replay itself is
# withholding/typed/replay.py, driven by scripts/typed_replay_scores.py) read a whole output file at a time. This
# section types one directory's stored rows once for them:
# - `DirectoryDispatch` reads the step 0 sidecar of the directory and its output rows, types every row through
#   `type_stored_row`, and refuses a row whose completion key or raw text sha is not the sidecar's line for the same
#   file and line (the sidecar is the record of what step 0 typed; a row that moved since is not silently re-typed);
# - `score_line` calls a typed entry on a row under the entry's binding (`legacy_line`: the issuer picks
#   delivered_20261014 or whole_output per family as design 2.4's table and the RLCR closure state) and serializes
#   it through the per-family table of design 2.5a (`layout_of`, `serialize_line`);
# - `empty_output_line` is today's empty-completion no_answer path (Batch A, `scripts/mark_empty_completions.py`) on
#   typed inputs: the dispatcher, not a body, writes it, and the replay applies it only where a directory's
#   mark_empty_completions changelog says it ran;
# - `cache_only_judge` answers the Gemini judge from cached replies and refuses everything else, so no replay can
#   make a call.
SIDECAR_ROOT = RESULTS / "_ingest" / "sidecars_2026-10-15"  # where scripts/backfill_completions.py wrote step 0's
SIDECAR_NAME = "typed/completions.v2.jsonl.gz"
JUDGE_LAYOUT_FILES = ("scores_abstain.jsonl", "scores.jsonl")  # design 2.5a: JudgeLine; every other score file is
# ProgrammaticLine (scores_programmatic*, scores_judged*, scores_impossible_v3, the OOD files)


class SidecarMismatch(ingest.IngestError):
    """A stored output row whose typed key or raw sha differs from its step 0 sidecar line, or that has none."""


class IngestionRefused(SidecarMismatch):
    """An output row no reader types (design section 6, step 6; plan W7.2): no step 0 sidecar line covers it and it
    lacks the runner's ingestion fields (`ingest.RUNNER_ROW_FIELDS`). A directory written before 25 Oct 2026 is covered
    by its sidecar (scripts/backfill_completions.py writes one); a row the runner wrote since carries the fields."""


OUTPUT_PREFIX, OUTPUT_SUFFIX = "outputs", ".jsonl"   # the output files the backfill types (its output_dirs)


def output_files(directory: Path) -> list[Path]:
    """A directory's output files, sorted: `outputs*.jsonl`, the files scripts/backfill_completions.py types."""
    return sorted(p for p in Path(directory).iterdir()
                  if p.name.startswith(OUTPUT_PREFIX) and p.name.endswith(OUTPUT_SUFFIX) and p.is_file())


def refused(rel_dir: str, file: str, lineno: int, row: Mapping[str, Any]) -> IngestionRefused:
    """The refusal of one output row that neither a sidecar line nor the runner's fields cover."""
    return IngestionRefused(
        f"no step 0 sidecar line covers this row and it lacks the runner's ingestion fields "
        f"{list(ingest.missing_runner_fields(row))}; type the directory first: python scripts/backfill_completions.py "
        f"--dirs {rel_dir} --sidecar-root {SIDECAR_ROOT.relative_to(RESULTS.parent)} --report-dir <a scratch dir>",
        where=f"{rel_dir}/{file}:{lineno}", row_id=row.get("id"))


def ingestion_basis(rel_dir: str, *, sidecar_root: Path = SIDECAR_ROOT, results: Path = RESULTS) -> str:
    """What types a directory's rows for a report reader: "sidecar" when its step 0 sidecar exists (old directories;
    a row it does not cover is refused when read, `DirectoryDispatch.rows`), else "runner_stamp" when every row of
    every output file carries the runner's ingestion fields (a directory the runner wrote from 25 Oct 2026).
    IngestionRefused for any other directory, one with no output row included: a reader never reads it."""
    if (Path(sidecar_root) / rel_dir / SIDECAR_NAME).exists():
        return "sidecar"
    n = 0
    d = Path(results) / rel_dir
    for path in output_files(d) if d.is_dir() else []:
        with open(path, encoding="utf-8") as fh:
            for lineno, raw in enumerate(fh, 1):
                if raw.strip():
                    n += 1
                    row = json.loads(raw)
                    if ingest.missing_runner_fields(row):
                        raise refused(rel_dir, path.name, lineno, row)
    if not n:
        raise IngestionRefused(f"no step 0 sidecar for {rel_dir} and no output row to type", where=rel_dir)
    return "runner_stamp"


class JudgeCacheMiss(LookupError):
    """A Gemini judge prompt whose reply is not among the cached replies the replay was given (no call is made)."""

    def __init__(self, key: str):
        super().__init__(f"judge reply not cached: {key}")
        self.key = key


def layout_of(score_file: str) -> type:
    """The LegacyScoreLine layout of a score file (design 2.5a's per-family serializer table): JudgeLine for
    scores_abstain.jsonl and scores.jsonl, ProgrammaticLine for every other score file."""
    return models.JudgeLine if Path(score_file).name in JUDGE_LAYOUT_FILES else models.ProgrammaticLine


def serialize_line(d: Mapping[str, Any], layout: type) -> str:
    """One score line through the typed mirror (design 2.5a): the dict's top-level key order must be the layout's
    (the mirror never reorders, so a body that wrote another order is refused, not repaired), the line validates in
    strict mode, and `models.serialize_score_line` writes it; the newline is the writers'."""
    if tuple(d) != tuple(layout.model_fields):
        raise models.LegacyLineError(f"key order {tuple(d)} is not the {layout.__name__} layout")
    return models.serialize_score_line(layout.model_validate(dict(d))) + "\n"


def read_sidecar(rel_dir: str, sidecar_root: Path = SIDECAR_ROOT) -> dict[tuple[str, int], dict]:
    """{(output file name, line number): sidecar record} of one directory (its real path relative to results/)."""
    path = Path(sidecar_root) / rel_dir / SIDECAR_NAME
    if not path.exists():
        raise SidecarMismatch(f"no step 0 sidecar for {rel_dir} ({path})")
    out: dict[tuple[str, int], dict] = {}
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            out[(rec["file"], rec["line"])] = {k: rec[k] for k in ("key", "raw_sha", "spec_id", "finish_reason",
                                                                   "prompt_id", "sample")}
    return out


@dataclass(frozen=True)
class DirectoryRow:
    """One stored output row of a directory, typed: where it sits (file, 1-based line with blank lines counted, as the
    backfill counts them), the parsed row (the writers' own bookkeeping pairs score rows with it; no body reads it),
    its id family, its TypedRow and its PromptRecord (the judged entries take the prompt: question, gold, ToolSet)."""

    file: str
    line: int
    row: dict
    family: str
    typed: TypedRow
    prompt: Any


class DirectoryDispatch:
    """One directory's output files, typed once against the step 0 sidecar, or, for a row no sidecar line covers,
    against the runner's ingestion stamp the row carries (design section 6 step 6, from 25 Oct 2026). `rel_dir` is the
    directory's real path relative to results/ (a symlinked alias is typed under its target, as the backfill keyed it).
    Rows of a file are typed on first use and stay in ingest's store until `close()`. `stamped_lines` holds, for each
    row typed through its stamp, the sidecar line the backfill would write for it (the classification's own, with the
    Completion's completion token hash and the runner's prompt token hash), keyed (file, line) like the sidecar; a
    report reads it in the sidecar's place."""

    def __init__(self, rel_dir: str, *, registry: Any, sidecar_root: Path = SIDECAR_ROOT,
                 results: Path = RESULTS):
        self.rel_dir = rel_dir
        self.dir = Path(results) / rel_dir
        self._results = Path(results)
        self.registry = registry
        self._sidecar_root = Path(sidecar_root)
        self._sidecar: dict[tuple[str, int], dict] | None = None
        self._files: dict[str, list[DirectoryRow]] = {}
        self._by_id: dict[tuple[str, int], list[DirectoryRow]] = {}
        self.stamped_lines: dict[tuple[str, int], dict] = {}

    def rows(self, file: str) -> list[DirectoryRow]:
        """Every non-blank row of output file `file`, in file order, typed and checked against its sidecar line, or
        typed through the runner's ingestion stamp (checked by `ingest.classify_stored_row`) where no line covers it;
        IngestionRefused for a row with neither."""
        if file not in self._files:
            if self._sidecar is None:
                has = (self._sidecar_root / self.rel_dir / SIDECAR_NAME).exists()
                self._sidecar = read_sidecar(self.rel_dir, self._sidecar_root) if has else {}
            path = self.dir / file
            draw = draw_of(path, self._results)
            out: list[DirectoryRow] = []
            with open(path, encoding="utf-8") as fh:
                for lineno, raw in enumerate(fh, 1):
                    if not raw.strip():
                        continue
                    row = json.loads(raw)
                    where = f"{self.rel_dir}/{file}:{lineno}"
                    rec = self._sidecar.get((file, lineno))
                    if rec is None:
                        if ingest.missing_runner_fields(row):
                            raise refused(self.rel_dir, file, lineno, row)
                        t, x = _type_row(row, draw=draw, registry=self.registry)
                        self.stamped_lines[(file, lineno)] = {
                            "file": file, "line": lineno, **x["sidecar"], "prompt_token_hash": row["prompt_token_hash"],
                            "prompt_token_hash_source": "runner"}
                    else:
                        t = type_stored_row(row, draw=draw, registry=self.registry)
                        raw_sha = ingest.sha256_hex(row["output"])
                        if t.key != rec["key"] or raw_sha != rec["raw_sha"]:
                            raise SidecarMismatch(f"typed key {t.key} / raw sha {raw_sha[:12]} differ from the "
                                                  f"sidecar's {rec['key']} / {rec['raw_sha'][:12]}", where=where,
                                                  row_id=row.get("id"))
                    d = DirectoryRow(file=file, line=lineno, row=row, family=models.family_of(row["id"]), typed=t,
                                     prompt=adapters.prompt_record(row))
                    out.append(d)
                    self._by_id.setdefault((row["id"], row.get("sample", 0)), []).append(d)
            self._files[file] = out
        return self._files[file]

    def find(self, row: Mapping[str, Any]) -> DirectoryRow:
        """The typed row of an output row a writer holds (its own parse of a loaded file): same id and sample, and the
        same parsed content, among the rows already typed."""
        for d in self._by_id.get((row["id"], row.get("sample", 0)), ()):
            if d.row == row:
                return d
        raise ingest.IngestError("a writer handed over a row no loaded output file holds", row_id=row.get("id"))

    def close(self) -> None:
        """Drop every completion this directory registered from ingest's store."""
        ingest.forget([d.typed.key for rows in self._files.values() for d in rows])
        self._files.clear()
        self._by_id.clear()
        self.stamped_lines.clear()


def score_line(d: DirectoryRow, entry: Callable[..., dict], layout: type = models.ProgrammaticLine) -> str:
    """The serialized score line of a typed entry on a typed row: the entry reads the sealed text its binding names
    (`legacy_line`), the dispatcher appends the row identity, and the line goes through the per-family table."""
    return serialize_line(legacy_line(d.typed, entry), layout)


def is_empty_completion(d: DirectoryRow) -> bool:
    """Today's empty-completion rule (`withholding.score.abstention_judge.is_empty_completion`: no non-whitespace
    character) on the sealed whole_output view, content only."""
    return not ingest.read_legacy(d.typed.key, "whole_output").text.strip()


def empty_output_line(kind: str, d: DirectoryRow, current: Mapping[str, Any]) -> str | None:
    """The line an empty completion's score row becomes under Batch A's rule (`scripts/mark_empty_completions.py`
    `no_answer_line`), from typed inputs: the empty output row `d`, evidenced by its blank whole_output text. `kind`
    is the writer's (programmatic, judged, abstain); `current` is the score line being replaced (the judged no_answer
    keeps its judge's stamp, as the writer does). The judge families go through their modules' typed no_answer
    entries (`judged.no_answer_line_typed`, `abstention_judge.abstain_no_answer_line_typed`); a programmatic row is
    written here from the family's gold, the sealed text's finish_reason and the row identity. None where today's
    rule writes none (ImpossibleBench v2 rows)."""
    text = ingest.read_legacy(d.typed.key, "whole_output")
    if kind == "abstain":
        from withholding.score import abstention_judge as AJ

        return models.serialize_score_line(AJ.abstain_no_answer_line_typed(text, d.prompt, d.typed.identity)) + "\n"
    if kind == "judged":
        from withholding.score import judged as J

        line = J.no_answer_line_typed(text, d.prompt, d.typed.identity, replaces=str(current["scorer"]))
        return models.serialize_score_line(line) + "\n"
    from withholding.score import programmatic as P

    g, trunc = d.typed.gold, text.finish_reason == "length"
    if d.family in {f for f, fn in P.SCORERS.items() if fn is P.score_reliablemath}:  # the writer's family set
        s = {"score": 0.0, "label": "no_answer", "scorer": "reliablemath/boxed/v1.2",
             "detail": {"boxed": "", "solvable": bool(g.solvable), "admitted": False, "idk": False, "truncated": trunc,
                        "delivered": False, "empty_output": True}}
    elif d.family == "math500":
        s = {"score": 0.0, "label": "no_answer", "scorer": "math500/math-verify/v1.1",
             "detail": {"boxed": None, "gold": g.answer, "level": g.level, "truncated": trunc, "delivered": False,
                        "empty_output": True}}
    elif d.family == "rlcr":
        s = {"score": None, "label": "no_answer", "scorer": "rlcr/tac/v2.1",
             "detail": {"correct": False, "confidence": None, "answer": "", "gold": str(g.answer), "set": g.set,
                        "strict_format": False, "truncated": trunc, "delivered": False, "empty_output": True}}
    else:
        return None
    s.update(d.typed.identity.model_dump())
    return serialize_line(s, models.ProgrammaticLine)


@contextlib.contextmanager
def cache_only_judge(texts: Mapping[str, str]):
    """Inside the block the Gemini judge (`withholding.score.gemini_judge.judge` and `judge_meta`, and the name
    `withholding.score.judged` imported) answers from `texts` ({cache key: reply}) under the cache's own key function,
    and raises JudgeCacheMiss for any other prompt: no call can reach the API. `texts` holds a reply text, or a
    (text, meta) pair where meta is what `gemini_judge._load` keeps for the line (usage and finish_reason, both None
    on a line written before 10 Oct 2026); `judge_meta` returns the same (text, meta) as the cache path of
    `gemini_judge.judge_meta`. The names `judge` and `judge_meta` that `withholding.score.judged` imported are
    replaced too."""
    from withholding.score import gemini_judge as G
    from withholding.score import judged as J

    def judge_meta(prompt: str, model: str = G.MODEL, max_tokens: int = 1024, temperature: float = 0.0,
                   tag: str | None = None, thinking_budget: int = G.THINKING_BUDGET) -> tuple[str, dict]:
        key = G.cache_key(prompt, model, temperature, tag, thinking_budget, max_tokens)
        if key not in texts:
            raise JudgeCacheMiss(key)
        hit = texts[key]
        text, m = (hit, {}) if isinstance(hit, str) else hit
        return text, {"cached": True, "key": key, "model": model, "usage": m.get("usage"),
                      "finish_reason": m.get("finish_reason")}

    def judge(prompt: str, *a: Any, **k: Any) -> str:
        return judge_meta(prompt, *a, **k)[0]

    names = [(G, "judge", judge), (G, "judge_meta", judge_meta), (J, "judge", judge)]
    if hasattr(J, "judge_meta"):
        names.append((J, "judge_meta", judge_meta))
    saved = [(mod, n, getattr(mod, n)) for mod, n, _ in names]
    for mod, n, fn in names:
        setattr(mod, n, fn)
    try:
        yield
    finally:
        for mod, n, fn in saved:
            setattr(mod, n, fn)
