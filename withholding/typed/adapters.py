"""Adapters from every stored row shape to the typed layer (design `notes/typed_ingestion_design_2026-10-15.md`,
section 6 step 0: "Write adapters for every stored row shape the pipeline brief lists").

Each adapter reads one stored shape as it sits on disk, refuses unknown keys (``extra="forbid"``, strict types), and
maps it onto the design's types:

| stored shape | where it is written | typed as |
|---|---|---|
| prompt row (`prompts*.jsonl`) | the prompt builders; also embedded in every output row | `StoredPromptRow` -> `models.PromptRecord` (2.2) |
| output row (`outputs*.jsonl`) | `withholding/run/modal_vllm.py:226-246` | `StoredOutputRow` -> PromptRecord, `models.GenerationConfig` (2.3), and through `ingest.classify_stored_row` the Completion |
| score line, four shapes (`scores*.jsonl`) | programmatic and judged scorers; the abstention judge; recognition v3 and v4 | `score_line`: `models.ProgrammaticLine` / `models.JudgeLine` (LegacyScoreLine, 2.5a), or `LegacyRecognitionLine` (outside step 1's proof) |
| judge prompt row (`judge_prompts*.jsonl`) | `withholding/score/abstention_judge.py:60-96` | `JudgePromptRow` |
| judge output row (`judge_outputs*.jsonl`) | the runner over judge prompts | `StoredOutputRow` + `abstention_verdict` (`models.AbstentionYesNo` / `models.Unparsed`, 2.6) |
| cache record (`results/judge_cache_*.jsonl`) | `withholding/score/gemini_judge.py:124-131`, `claude_judge.py:164-172` | `CacheRecord` (finish reason normalized, 2.6) |
| rollout (`rollouts.jsonl`), pilot reward row (`rewards.jsonl`) | `withholding/train/grpo_modal.py` `write_rollouts`; `withholding/analysis/pilot_p2_report.py:365` | `RolloutRow` (c_reward v1.1), `TypedRolloutRow` (v2, from 25 Oct 2026), `PilotRewardRow` |

Rows lacking a field the runner added later carry it as not recorded, never as a guess: `stop_reason`,
`vllm_version`, `prompt_token_hash`, `think_forced` and `max_model_len` (no stored row records them, or only some do),
`finish_reason` on the 4 local smoke rows. Two runner defaults of the time are cited instead: a row without `sample`
is sample 0 (`withholding/score/programmatic.py:488`, `row_identity`), and a sampling record without `n` or
`stop_token_ids` ran with vLLM's defaults, one sample and no stop ids, because the runner then had no such parameter
(`withholding/run/modal_vllm.py:216-217` passes them since).

When2Call tools (2.2): `meta.tools` is parsed per line into a ToolSet (12,276 stored rows hold newline-joined JSON
objects, 2,455 one object, 905 the empty string, which is `declared_empty`), each tool's key order must be the stored
one, and the legacy serializer must rebuild the stored string byte for byte, or the row is refused. Every stored
prompt carries its declared tools as message text, because the runner never passes `tools=` to the template
(`withholding/run/modal_vllm.py:226-227`), so a stored row with a declared ToolSet is `tool_render =
system_text_legacy` (only adapters admit it, design 2.2); a prompt that declares no tools is `slot`.

Step 0 changes no behaviour: nothing here is read by a scorer, judge, reward or report yet.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from functools import cache
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, JsonValue, model_validator

from withholding.typed import models as _M

ROOT = Path(__file__).resolve().parents[2]
ITEM_STATUS_PATH = ROOT / "results" / "c_data" / "item_status.json"
NOT_RECORDED = "not_recorded"
_CFG = ConfigDict(frozen=True, extra="forbid", strict=True)


class AdapterError(ValueError):
    """A stored row the adapter refuses: an unknown key, a wrong type, a tool string the per-line parse cannot
    rebuild, a judge prompt whose id does not name its subject."""


class _Mirror(BaseModel):
    """Base of the stored-row mirrors: frozen, unknown keys refused, strict (design 2.0)."""

    model_config = _CFG


def _tuples(value: Any) -> Any:
    """JSON arrays as tuples, recursively (strict mode refuses a list for a tuple field)."""
    if isinstance(value, list):
        return tuple(_tuples(v) for v in value)
    return value


# ============================================================================================ prompt and output rows
class StoredMessage(_Mirror):
    """One chat message as stored."""

    role: str
    content: str


class StoredSampling(_Mirror):
    """The runner's `sampling` record (`withholding/run/modal_vllm.py:241-243`); `n` and `stop_token_ids` are absent
    on rows written before the runner had them, `top_k` was never set (audit 26)."""

    max_tokens: int
    temperature: float
    top_p: float
    seed: int
    n: int | None = None
    chat_template_kwargs: dict[str, bool] | None = None
    stop_token_ids: tuple[int, ...] | None = None


class StoredPromptRow(_Mirror):
    """A prompt row as the prompt builders write it."""

    id: str
    behavior: str
    messages: tuple[StoredMessage, ...]
    meta: dict[str, JsonValue]

    @model_validator(mode="before")
    @classmethod
    def _arrays(cls, d: Any) -> Any:
        if isinstance(d, Mapping) and isinstance(d.get("messages"), list):
            d = {**d, "messages": tuple(d["messages"])}
        return d

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> StoredPromptRow:
        """The mirror of a parsed prompt row; AdapterError names the refusal."""
        try:
            return cls.model_validate(dict(row))
        except ValueError as e:
            raise AdapterError(f"prompt row {row.get('id')!r} refused: {e}") from e


class StoredOutputRow(_Mirror):
    """An output row as the runner writes it (`withholding/run/modal_vllm.py:232-246`), every stored variant: the
    current shape, the extended passes' `cap`/`cap_first_pass`, the Tulu rows without the runner's split fields, the
    dose check's `vllm_version`, the two smoke files, the judge outputs' `subject_id`, and from 25 Oct 2026 the runner's
    `stop_reason`, ingestion stamp, completion ids and their hash (design section 6 step 6, section 9 (b)). A key the
    runner never wrote is refused. Which optional keys a row carried is `model_fields_set`."""

    id: str
    behavior: str
    messages: tuple[StoredMessage, ...]
    meta: dict[str, JsonValue]
    output: str
    model: str
    sample: int | None = None
    subfolder: str | None = None
    revision: str | None = None
    thinking: bool | None = None
    dtype: str | None = None
    chat_template_from: str | None = None
    prompt_render_hash: str | None = None
    vllm_version: str | None = None
    finish_reason: Literal["stop", "length"] | None = None
    reasoning: str | None = None
    answer: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    sampling: StoredSampling | None = None
    think_forced: bool | None = None
    prompt_token_hash: str | None = None
    stop_reason: int | str | None = None
    cap: int | None = None
    cap_first_pass: int | None = None
    subject_id: str | None = None
    # the runner's ingestion stamp (design section 6 step 6, plan W7.2; rows written from 25 Oct 2026):
    # ingest.RUNNER_STAMP_FIELDS, checked against the typed reading by ingest.classify_stored_row
    spec_id: str | None = None
    think_opened_by: Literal["template", "model"] | None = None
    think_closed: bool | None = None
    think_close_count: int | None = None
    empty_output: bool | None = None
    invented_turn: bool | None = None
    # the ids vLLM sampled and their hash (step 6 fix round, design 9 (b); rows written from 25 Oct 2026), checked
    # against each other and completion_tokens by ingest.classify_stored_row
    completion_token_ids: tuple[int, ...] | None = None
    completion_token_hash: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _arrays(cls, d: Any) -> Any:
        if not isinstance(d, Mapping):
            return d
        d = dict(d)
        for k in ("messages", "completion_token_ids"):
            if isinstance(d.get(k), list):
                d[k] = tuple(d[k])
        s = d.get("sampling")
        if isinstance(s, Mapping) and isinstance(s.get("stop_token_ids"), list):
            d["sampling"] = {**s, "stop_token_ids": tuple(s["stop_token_ids"])}
        return d

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> StoredOutputRow:
        """The mirror of a parsed output row; AdapterError names the refusal."""
        try:
            return cls.model_validate(row)
        except ValueError as e:
            raise AdapterError(f"output row {row.get('id')!r} refused: {e}") from e

    @property
    def sample_or_default(self) -> int:
        """The sample index; 0 where the row has none, as every scorer reads it (`programmatic.py:488`)."""
        return 0 if self.sample is None else self.sample

    @property
    def chat_kwargs(self) -> dict[str, bool] | None:
        """The chat template kwargs as passed (`sampling.chat_template_kwargs`); None when no sampling was recorded."""
        return None if self.sampling is None else dict(self.sampling.chat_template_kwargs or {})

    @property
    def stop_reason_or_not_recorded(self) -> int | str | None:
        """vLLM's stop_reason as stored, or not_recorded (no stored row carries it; W8.5.6)."""
        return self.stop_reason if "stop_reason" in self.model_fields_set else NOT_RECORDED


# ================================================================================================ tools (2.2)
def parse_when2call_tools(tools: str) -> _M.ToolSet:
    """`meta.tools` parsed per line into a ToolSet (design 2.2). The empty string is `declared_empty`. Every line must
    be one JSON object whose keys are name, description, parameters in that order, and the ToolSet's legacy
    serializer must rebuild `tools` byte for byte; AdapterError otherwise. `json.loads` on the whole string would
    raise on 13,181 stored rows, which is why the parse is per line."""
    if not isinstance(tools, str):
        raise AdapterError(f"meta.tools must be a str, got {type(tools).__name__}")
    if tools == "":
        return _M.ToolSet(state="declared_empty")
    specs = []
    for i, line in enumerate(tools.split("\n")):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            raise AdapterError(f"meta.tools line {i} is not one JSON value: {e}") from e
        if not isinstance(obj, dict) or tuple(obj) != ("name", "description", "parameters"):
            raise AdapterError(f"meta.tools line {i} is not a (name, description, parameters) object")
        specs.append(_M.ToolSpec(name=obj["name"], description=obj["description"], parameters=obj["parameters"]))
    ts = _M.ToolSet(state="declared", tools=tuple(specs))
    if ts.legacy_serialize() != tools:
        raise AdapterError("the per-line tool serializer does not rebuild the stored meta.tools string")
    return ts


# ================================================================================================ golds (2.2)
_ANSWER_FORMAT: dict[str, str] = {**{f: "boxed" for f in _M.RELIABLEMATH_GROUP}, "math500": "boxed",
                                  "rlcr": "tac_tags", "impossible_lcb": "code_block", "xstest": "free_text",
                                  "when2call": "tool_call_or_text", "abstentionbench": "free_text",
                                  "smoke": "free_text"}


def _need_meta(meta: Mapping[str, Any], *keys: str) -> None:
    missing = [k for k in keys if k not in meta]
    if missing:
        raise AdapterError(f"meta lacks {missing}")


def abstention_label(meta: Mapping[str, Any]) -> tuple[bool, str]:
    """(abstention_label, label_source): `meta.abstention_label`, else `str(meta.target) == "True"`, the fallback the
    judge applies (`withholding/score/abstention_judge.py:80-83`), applied once here and recorded (design 2.2)."""
    lab = meta.get("abstention_label")
    if lab is None:
        return str(meta.get("target")) == "True", "target_fallback"
    if not isinstance(lab, bool):
        raise AdapterError(f"abstention_label must be a bool, got {type(lab).__name__}")
    return lab, "abstention_label"


def gold_of(family: str, meta: Mapping[str, Any]) -> Any:
    """The family's typed gold from a row's meta (design 2.2): only the fields a scorer or judge prompt reads; every
    other meta key stays on disk and never reaches a body."""
    if family in _M.RELIABLEMATH_GROUP:
        _need_meta(meta, "solvable", "ground_truth")
        return _M.ReliableMathGold(solvable=meta["solvable"], ground_truth=meta["ground_truth"],
                                   original_ground_truth=meta.get("original_ground_truth"))
    if family == "rlcr":
        _need_meta(meta, "answer", "set")
        return _M.RLCRGold(answer=meta["answer"], set=meta["set"])
    if family == "math500":
        _need_meta(meta, "answer", "level")
        return _M.Math500Gold(answer=meta["answer"], level=meta["level"])
    if family == "impossible_lcb":
        _need_meta(meta, "split", "test", "original_test", "entry_point")
        return _M.ImpossibleGold(split=meta["split"], test=meta["test"], original_test=meta["original_test"],
                                 entry_point=meta["entry_point"])
    if family == "xstest":
        _need_meta(meta, "label", "type")
        return _M.XSTestGold(label=meta["label"], type=meta["type"])
    if family == "when2call":
        _need_meta(meta, "correct_answer")
        return _M.When2CallGold(correct_answer=meta["correct_answer"])
    if family == "abstentionbench":
        _need_meta(meta, "dataset")
        label, source = abstention_label(meta)
        return _M.AbstentionGold(abstention_label=label, label_source=source, dataset=meta["dataset"],
                                 ref_answer=meta.get("ref_answer", "[]"))
    if family == "smoke":
        _need_meta(meta, "gold")
        return _M.SmokeGold(gold=meta["gold"], why=meta.get("why"))
    raise AdapterError(f"no gold adapter for family {family!r}")


@cache
def _item_status_file(path: str) -> dict[str, str]:
    p = Path(path)
    if not p.exists():
        return {}
    return {k: v.get("status") for k, v in json.loads(p.read_text(encoding="utf-8")).items()}


def item_status_of(prompt_id: str, statuses: Mapping[str, str] | None = None) -> str:
    """clean or not_clean from `results/c_data/item_status.json` (design 2.2: "from results/c_data/item_status.json,
    not a side file"); unscreened for an item the file does not list."""
    st = _item_status_file(str(ITEM_STATUS_PATH)) if statuses is None else statuses
    v = st.get(prompt_id)
    if v is None:
        return "unscreened"
    if v not in ("clean", "not_clean"):
        raise AdapterError(f"item status {v!r} for {prompt_id!r} is neither clean nor not_clean")
    return v


def prompt_record(src: Any, *, item_status: Mapping[str, str] | None = None) -> _M.PromptRecord:
    """The PromptRecord of a stored prompt or output row (or its mirror). Tools: parsed from `meta.tools` for
    When2Call, absent for every other family; a stored row's declared tools are system text (module docstring), which
    `models.PromptRecord` admits only under the backfill context this adapter passes."""
    if isinstance(src, Mapping):
        src = StoredPromptRow.from_row({k: src[k] for k in ("id", "behavior", "messages", "meta") if k in src})
    try:
        family = _M.family_of(src.id)
    except ValueError as e:
        raise AdapterError(str(e)) from e
    meta = src.meta
    tools = parse_when2call_tools(meta.get("tools")) if family == "when2call" else _M.ToolSet(state="absent")
    messages = tuple(_M.Message(role=m.role, content=m.content) for m in src.messages)
    fields = {"id": src.id, "family": family, "behavior": src.behavior, "messages": messages,
              "system_source": "benchmark" if messages and messages[0].role == "system" else "none", "tools": tools,
              "tool_render": "slot" if tools.state == "absent" else "system_text_legacy",
              "answer_format": _ANSWER_FORMAT[family], "gold": gold_of(family, meta),
              "item_status": item_status_of(src.id, item_status), "prompt_sha": _M.prompt_sha_of(messages, tools)}
    try:  # this is the backfill adapter, the only one models.PromptRecord admits system_text_legacy from (2.2)
        return _M.PromptRecord.model_validate(fields, context={"backfill": True})
    except ValueError as e:
        raise AdapterError(f"prompt {src.id!r} refused: {e}") from e


# ============================================================================================ generation (2.3, 9 (c))
EXT_FILE = "outputs_ext.jsonl"   # the extended pass's own file (scripts/merge_ext.py:22; D17)


def first_pass_draw(draw: str) -> str:
    """The output file an extended pass's first pass was read from (design 2.3, Revision 4). `scripts/merge_ext.py`
    (:21-24, :29-33) reads `<lineage>/<mode>/<stage>/outputs.jsonl`, takes each row that hit the first cap from
    `<lineage>/<mode>_ext/<stage>/outputs_ext.jsonl`, and writes the merge to `<lineage>/<mode>_ext/<stage>/
    outputs.jsonl`; so a re-drawn row of that merged file, and every row of `outputs_ext.jsonl` itself (D17), replaces
    the row of its (prompt, sample) in the first file. AdapterError for any other draw: no other code writes a re-drawn
    row."""
    parts = PurePosixPath(draw).parts
    if (len(parts) >= 3 and parts[-1] in ("outputs.jsonl", EXT_FILE) and parts[-3].endswith("_ext")
            and parts[-3] != "_ext"):
        return str(PurePosixPath(*parts[:-3], parts[-3][:-len("_ext")], parts[-2], "outputs.jsonl"))
    raise AdapterError(f"a re-drawn row outside an extension file (<mode>_ext/<stage>/outputs.jsonl or "
                       f"{EXT_FILE}): {draw!r}")


def is_ext_draw(draw: str) -> bool:
    """True for the extended pass itself, `<lineage>/<mode>_ext/<stage>/outputs_ext.jsonl` (D17, 17 Oct 2026): the
    file `scripts/merge_ext.py` (:19-35) reads the re-drawn rows from. Its rows carry neither `cap` nor
    `cap_first_pass`; the file name is the record that each of them is a re-draw."""
    parts = PurePosixPath(draw).parts
    return len(parts) >= 3 and parts[-1] == EXT_FILE and parts[-3].endswith("_ext") and parts[-3] != "_ext"


def merged_twin_caps(merged_outputs: str | Path) -> dict[tuple[str, int], int]:
    """D17 (17 Oct 2026): {(id, sample): cap_first_pass} of the re-drawn rows of a merged extension file
    (`<lineage>/<mode>_ext/<stage>/outputs.jsonl`, written by `scripts/merge_ext.py`, which copies each row of the
    extended pass's own `outputs_ext.jsonl` into it with `cap` and `cap_first_pass` added). The typed layer reads an
    `outputs_ext.jsonl` row's first cap from its twin here; {} when the file does not exist."""
    out: dict[tuple[str, int], int] = {}
    p = Path(merged_outputs)
    if not p.exists():
        return out
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                if r.get("cap") is not None and r.get("cap") != r.get("cap_first_pass"):
                    out[(r["id"], r.get("sample", 0))] = r["cap_first_pass"]
    return out


def generation_config(row: StoredOutputRow, spec: Any, *, draw: str, prompt_sha: str,
                      ext_cap_first_pass: int | None = None) -> _M.GenerationConfig | None:
    """The GenerationConfig a stored row ran with (design 2.3 and 9 (c)); None when the row recorded no sampling at
    all (the 4 local MLX smoke rows), whose Completion then carries generation_config_id not_recorded.

    Stored rows: `max_model_len` not recorded (no row records it), `rope_scaling` model_default (the runner passes no
    override, `modal_vllm.py:210-212`), `top_k` vllm_default_unrecorded (`:213`), `tokenizer_revision` not recorded
    (the spec id asserts the registry's pin), `tokenizer_from` and `tokenizer_subfolder` the spec's (the runner loads
    the model's own tokenizer and stores neither), `dtype` and `vllm_version` as stored or not recorded. An extended
    pass's re-drawn row (`cap` above `cap_first_pass`, its max_tokens the larger cap) is provenance redraw and
    `replaces` the completion key of its first pass: the same prompt (`prompt_sha`) and sample, drawn at
    `cap_first_pass` in the file `first_pass_draw(draw)` names; a carried first-pass row (`cap == cap_first_pass`) is
    first_pass (audit 9; design 9 (c)). The backfill checks that every such key names a stored row cut at the cap.

    D17 (17 Oct 2026): a row of the extended pass's own file (`is_ext_draw`) is a re-draw too, typed by the file
    name. Its `cap_first_pass` is not on the row; the caller passes `ext_cap_first_pass`, its merged twin's stored
    `cap_first_pass`, and the row `replaces` the first pass of its prompt and sample drawn at that cap in the file
    `first_pass_draw(draw)` names, the key its twin's `replaces` names. A row of that file without it is refused."""
    s = row.sampling
    if s is None:
        return None
    base = {"max_tokens": s.max_tokens, "temperature": s.temperature, "top_p": s.top_p,
            "top_k": "vllm_default_unrecorded", "seed": s.seed, "n": 1 if s.n is None else s.n,
            "stop_token_ids": tuple(s.stop_token_ids or ()), "max_model_len": NOT_RECORDED,
            "chat_template_kwargs": dict(s.chat_template_kwargs or {}), "tokenizer_from": spec.tokenizer_from,
            "tokenizer_subfolder": spec.tokenizer_subfolder, "tokenizer_revision": NOT_RECORDED,
            "rope_scaling": "model_default", "dtype": row.dtype if row.dtype is not None else NOT_RECORDED,
            "vllm_version": row.vllm_version if row.vllm_version is not None else NOT_RECORDED}
    if is_ext_draw(draw):   # D17: the extended pass's own rows are re-draws, by the file name
        if row.cap is not None or row.cap_first_pass is not None:
            raise AdapterError(f"a row of {EXT_FILE} carries cap or cap_first_pass (only merged rows do)")
        if not isinstance(ext_cap_first_pass, int) or isinstance(ext_cap_first_pass, bool):
            raise AdapterError(f"D17: a row of {EXT_FILE} is a re-draw; its merged twin's cap_first_pass is required")
        if s.max_tokens <= ext_cap_first_pass:
            raise AdapterError(f"D17: the extended pass's max_tokens {s.max_tokens} is not above its first pass's "
                               f"{ext_cap_first_pass}")
        return _redraw(row, spec, base, draw=draw, prompt_sha=prompt_sha, cap_first_pass=ext_cap_first_pass)
    if ext_cap_first_pass is not None:
        raise AdapterError(f"ext_cap_first_pass is given for a row of {EXT_FILE} only")
    if row.cap is None and row.cap_first_pass is None:
        return _M.GenerationConfig(**base, provenance="first_pass")
    if row.cap is None or row.cap_first_pass is None:
        raise AdapterError("cap and cap_first_pass come together")
    if row.cap != s.max_tokens:
        raise AdapterError(f"cap {row.cap} is not the row's max_tokens {s.max_tokens}")
    if row.cap == row.cap_first_pass:
        return _M.GenerationConfig(**base, provenance="first_pass")
    if row.cap < row.cap_first_pass:
        raise AdapterError("an extension's cap is below its first pass's")
    return _redraw(row, spec, base, draw=draw, prompt_sha=prompt_sha, cap_first_pass=row.cap_first_pass)


def _redraw(row: StoredOutputRow, spec: Any, base: dict, *, draw: str, prompt_sha: str,
            cap_first_pass: int) -> _M.GenerationConfig:
    """A re-drawn row's GenerationConfig: provenance redraw, `replaces` the key of its first pass (the same prompt and
    sample, drawn at `cap_first_pass` in the file `first_pass_draw(draw)` names)."""
    first = _M.GenerationConfig(**{**base, "max_tokens": cap_first_pass}, provenance="first_pass")
    from withholding.typed import ingest as _I  # the run identity lives with the store
    first_run = _I.run_id_of(model=row.model, subfolder=row.subfolder, revision=row.revision, spec_id=spec.spec_id,
                             generation_config_id=first.generation_config_id, draw=first_pass_draw(draw))
    replaces = _M.completion_key(first_run, row.id, row.sample_or_default, prompt_sha=prompt_sha)
    return _M.GenerationConfig(**base, provenance="redraw", replaces=replaces)


def prompt_token_hash(template_text: str | None, chat_kwargs: Mapping[str, Any], token_ids: Any) -> str:
    """The runner's prompt token hash, recomputed offline (`withholding/run/modal_vllm.py:125-130`, copied because
    that module imports modal at load): sha256, 16 hex, of the template text, the chat kwargs and the prompt ids."""
    payload = json.dumps({"chat_template": template_text, "chat_template_kwargs": dict(chat_kwargs),
                          "prompt_token_ids": [int(t) for t in token_ids]}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def completion_token_hash(token_ids: Any) -> str:
    """The Completion's completion_token_hash (design 2.3): sha256, 16 hex, of the completion ids' canonical JSON. The
    runner writes it with its own copy (`withholding/run/modal_vllm.py` completion_token_hash, because that module
    imports modal at load), and the C reward computes it from TRL's ids (`withholding.typed.reward.ids_hash`)."""
    return _M.sha256_hex(_M.canonical_json([int(t) for t in token_ids]))[:16]


# ================================================================================================ score lines (2.5a)
class LegacyRecognitionLine(_Mirror):
    """A stored recognition score line (`scores_recognition.jsonl` v3, `scores_recognition_v4.jsonl`) as an ordered
    mapping: lossless, no semantic invariant. Outside step 1's proof (design 2.5a); step 2r types them."""

    layout: Literal["recognition_v3", "recognition_v4"]
    items: tuple[tuple[str, JsonValue], ...]

    def serialize(self) -> str:
        """The stored line, byte for byte (`json.dumps(..., ensure_ascii=False)`, default separators)."""
        return json.dumps(dict(self.items), ensure_ascii=False)


SCORE_LINE_KINDS = ("programmatic", "judge", "recognition_v3", "recognition_v4")


def score_line(line: str, *, recognition: bool | None = None) -> Any:
    """One stored score line typed as one of its four shapes: `models.ProgrammaticLine` (scores_programmatic*,
    scores_judged*, scores_impossible_v3 and the OOD files) or `models.JudgeLine` (scores_abstain.jsonl and
    scores.jsonl), chosen by the stored key order through `models.parse_score_line` (design 2.5a: "any other order is
    refused"), or a LegacyRecognitionLine. `recognition` says whether the file is a recognition file (None: read from
    the keys)."""
    d = json.loads(line)
    if not isinstance(d, dict):
        raise AdapterError("a score line is a JSON object")
    is_rec = ("run" in d or "planted" in d) if recognition is None else recognition
    if is_rec:
        return LegacyRecognitionLine(layout="recognition_v4" if "run" in d else "recognition_v3",
                                     items=tuple(d.items()))
    try:
        return _M.parse_score_line(line)
    except ValueError as e:
        raise AdapterError(f"score line {d.get('id')!r} refused: {e}") from e


def serialize_score_line(typed: Any) -> str:
    """The stored line of a typed score line, byte for byte (design 2.5a's serializer, or the recognition mirror's)."""
    if isinstance(typed, LegacyRecognitionLine):
        return typed.serialize()
    return _M.serialize_score_line(typed)


def score_line_kind(typed: Any) -> str:
    """Which of the four stored shapes a typed score line is (SCORE_LINE_KINDS)."""
    if isinstance(typed, LegacyRecognitionLine):
        return typed.layout
    return {"ProgrammaticLine": "programmatic", "JudgeLine": "judge"}[type(typed).__name__]


# ================================================================================================ judge rows (2.6)
class AbstentionJudgeMeta(_Mirror):
    """The meta of a stored AbstentionBench judge prompt (`abstention_judge.py:90-93`); `ref_style` is absent on the
    files built before the paper rendering existed (audit 27)."""

    dataset: str | None
    abstention_label: bool
    subject_model: str | None
    subject_sample: int
    ref_style: Literal["paper", "list"] | None = None


class JudgePromptRow(_Mirror):
    """A stored judge prompt (`withholding/score/abstention_judge.py:86-94`): one user message holding the filled
    template, the subject's id and sample. The id is `<subject id>#judge<subject sample>` by construction (`:87`);
    a row whose id says otherwise is refused (audit 23: the id names the subject, not the prompt)."""

    id: str
    subject_id: str
    behavior: str
    messages: tuple[StoredMessage, ...]
    meta: AbstentionJudgeMeta

    @model_validator(mode="before")
    @classmethod
    def _arrays(cls, d: Any) -> Any:
        if isinstance(d, Mapping) and isinstance(d.get("messages"), list):
            d = {**d, "messages": tuple(d["messages"])}
        return d

    @model_validator(mode="after")
    def _shape(self) -> JudgePromptRow:
        if self.id != f"{self.subject_id}#judge{self.meta.subject_sample}":
            raise ValueError(f"judge prompt id {self.id!r} does not name subject {self.subject_id!r} sample "
                             f"{self.meta.subject_sample}")
        if len(self.messages) != 1 or self.messages[0].role != "user":
            raise ValueError("a judge prompt is one user message")
        return self

    @property
    def prompt_text(self) -> str:
        """The judge prompt text, the part of JudgeRequest.identity a resume compares (design 2.6)."""
        return self.messages[0].content


ReplyFinish = Literal["stop", "length", "refusal", "unknown_pre_2026_10_10", "not_recorded"]


def abstention_verdict(text: str, finish_reason: str | None) -> _M.AbstentionYesNo | _M.Unparsed:
    """The typed verdict (design 2.6) of a stored Llama abstention reply. The parse is the paper's
    (`withholding/score/abstention_judge.py:99-107`: lowercase, strip " .,\\n", exactly yes or no). A reply cut at its
    token limit is Unparsed(cut_at_max_tokens) whatever it says; a blank reply is Unparsed(empty_reply); anything else
    that is not yes or no is Unparsed(no_verdict)."""
    if finish_reason == "length":
        return _M.Unparsed(reason="cut_at_max_tokens")
    if not text.strip():
        return _M.Unparsed(reason="empty_reply")
    t = text.lower().strip(" .,\n")
    if t in ("yes", "no"):
        return _M.AbstentionYesNo(abstained=t == "yes")
    return _M.Unparsed(reason="no_verdict")


# ================================================================================================ cache records (2.6)
_FINISH_REFUSAL = {"SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII", "IMAGE_SAFETY", "IMAGE_PROHIBITED_CONTENT",
                   "refusal"}


class CacheRecord(_Mirror):
    """One judge cache record (`results/judge_cache_gemini.jsonl`, `results/judge_cache_claude.jsonl`), every stored
    variant: the pre-10-Oct line (key, model, prompt, text), and the later lines with usage, finish reason, and the
    temperature, tag, max_tokens, thinking settings and transport that are part of the call."""

    key: str
    model: str
    prompt: str
    text: str
    usage: dict[str, JsonValue] | None = None
    finish_reason: str | None = None
    temperature: float | None = None
    tag: str | None = None
    max_tokens: int | None = None
    thinking_budget: int | None = None
    thinking: str | None = None
    transport: str | None = None

    @property
    def normalized_finish_reason(self) -> ReplyFinish:
        """Design 2.6's normalization: STOP and end_turn are stop, MAX_TOKENS is length, a provider safety stop is
        refusal. A record with no finish_reason key was written before the 10 Oct rule (`gemini_judge.py:124-131`
        writes it since): unknown_pre_2026_10_10. A record whose finish_reason is null was written after it by the
        file transport (`claude_judge.py:348-351`), which has none: not_recorded, never passed off as pre-rule."""
        if "finish_reason" not in self.model_fields_set:
            return "unknown_pre_2026_10_10"
        fr = self.finish_reason
        if fr is None:
            return NOT_RECORDED
        if fr in _FINISH_REFUSAL or fr.startswith("BLOCKED_"):  # never cached today (judge_cache.py:50-52)
            return "refusal"
        try:
            return _M.normalize_finish_reason(fr)  # type: ignore[return-value]
        except ValueError as e:
            raise AdapterError(str(e)) from e

    @classmethod
    def from_line(cls, line: str) -> CacheRecord:
        """The typed record of one cache line; AdapterError names the refusal."""
        try:
            return cls.model_validate_json(line)
        except ValueError as e:
            raise AdapterError(f"cache record refused: {e}") from e


# ================================================================================================ rollouts (step 5)
class RolloutRow(_Mirror):
    """One `rollouts.jsonl` line of a run trained under c_reward v1.1 (`withholding/train/grpo_modal.py:261-273` as of
    13 Oct; the A' pilot's). `text` is present on unsolvable prompts only, and it is `completion_text(c)`, which
    rebuilds a closed block from TRL's parsed reasoning content (`withholding/train/c_rewards.py:65-80`): not the
    model's raw text, so it is never classified as a Completion. Lines written under c_reward v2 are TypedRolloutRow."""

    step: int
    id: str | None
    solvable: bool
    reward: float
    boxed: str | None
    admitted: bool
    idk: bool
    finished: bool
    tokens: int
    text: str | None = None

    @model_validator(mode="after")
    def _text_on_unsolvable(self) -> RolloutRow:
        if ("text" in self.model_fields_set) == self.solvable:
            raise ValueError("a rollout carries its text exactly when its prompt is unsolvable")
        return self


class TypedRolloutRow(_Mirror):
    """One `rollouts.jsonl` line written under c_reward v2 (design step 5, 25 Oct 2026; `withholding.typed.reward.
    rollout_row`, written by `grpo_modal.write_rollouts`). Every field is read from the evaluation ScoreRecord the
    rollout's reward was paid on and from its Completion: label, think_state and undelivered reason; boxed, admitted and
    idk (None when nothing was delivered: no_answer is a state, not a zero); the spec id, the completion token hash and
    the delivered text's sha; the scorer stamp with its rule date and read rule. `text` is the decode of the ids, the
    raw text the Completion was classified from, on unsolvable prompts only. "step" stays the first key
    (`grpo_modal._line_step`)."""

    step: int
    id: str
    solvable: bool
    reward: float
    label: str
    think_state: str
    undelivered_reason: str | None
    boxed: str | None
    admitted: bool | None
    idk: bool | None
    finished: bool
    tokens: int
    spec_id: str
    completion_token_hash: str
    delivered_sha: str | None
    scorer: str
    rule_date: str
    read_rule: str
    text: str | None = None

    @model_validator(mode="after")
    def _one_read(self) -> TypedRolloutRow:
        if self.label not in _M.FAMILY_LABELS["reliablemath"] or self.think_state not in _M.THINK_STATES:
            raise ValueError(f"label {self.label!r} or think_state {self.think_state!r} is not a typed value")
        none = self.label == "no_answer"
        if {none} != {self.delivered_sha is None, self.undelivered_reason is not None, self.admitted is None,
                      self.idk is None}:
            raise ValueError("no_answer exactly when nothing was delivered: no delivered sha, an undelivered reason, "
                             "and no admitted or idk read")
        if none and (self.boxed is not None or self.reward != 0.0):
            raise ValueError("an undelivered rollout has no box and earns 0 in every arm")
        if self.undelivered_reason is not None and self.undelivered_reason not in _M.UNDELIVERED_REASONS:
            raise ValueError(f"undelivered reason {self.undelivered_reason!r} is not one of rule D's")
        if not (_M.HEX16.fullmatch(self.spec_id) and _M.HEX16.fullmatch(self.completion_token_hash)
                and (self.delivered_sha is None or _M.HEX64.fullmatch(self.delivered_sha))):
            raise ValueError("spec_id and completion_token_hash are 16 hex, delivered_sha 64 hex")
        if ("text" in self.model_fields_set) == self.solvable:
            raise ValueError("a rollout carries its text exactly when its prompt is unsolvable")
        return self


class PilotRewardRow(_Mirror):
    """One `rewards.jsonl` line of the pilots (`withholding/analysis/pilot_p2_report.py:21-22`, written at `:365`):
    per-sample rewards of arms a and b, their advantages, and the label the scorer gave."""

    policy: str
    id: str
    sample: int
    reward_a: float
    reward_b: float
    adv_a: float
    adv_b: float
    admitted: bool
    label: str
    truncated: bool
    solvable: bool


def read_jsonl(path: str | Path, adapter: Any) -> list[Any]:
    """Every non-blank line of a JSONL file through `adapter` (a mirror class or a function of the parsed row);
    AdapterError names file:line on the first refusal."""
    out = []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                if isinstance(adapter, type) and issubclass(adapter, BaseModel):
                    row = json.loads(line)
                    out.append(adapter.from_row(row) if hasattr(adapter, "from_row") else adapter.model_validate(row))
                else:
                    out.append(adapter(json.loads(line)))
            except ValueError as e:
                raise AdapterError(f"{path}:{i}: {e}") from e
    return out
