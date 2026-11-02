"""The 14 Oct 2026 think registry and its delivered-answer reading, frozen for the legacy views (design 2.4; review item 16).

`withholding/score/think_registry.py` keeps serving its legacy callers unchanged, and the typed layer never reads it.
This module holds a read-only copy of that registry as it stood on 14 Oct 2026, so the legacy views of step 1 (design
2.4: answer_or_output, whole_output, delivered_20261014) stay on the 14 Oct reading whatever later happens to the live
registry. The reason for the freeze: `thinking_rule` returns None for an entry with no answer channel
(`withholding/score/programmatic.py:277`), so adding, say, an RL-Zero channel to the live registry would make the live
`delivered_answer` (`programmatic.py:290`) move rows of its legacy callers (`scripts/rescore_forced_think.py`,
`scripts/mark_empty_completions.py`, `scripts/make_impossible_human_check_v3.py`). The frozen copy cannot move.

What is copied, and how:
- The span between the BEGIN and END markers below is `withholding/score/think_registry.py:38-155` (TEMPLATES,
  THINK_TEMPLATE_FORMAT, NOT_ON_RECORD, CONTENT_RULE, Entry, _kw, the pattern constants, ENTRIES, row_key, _match,
  _lookup, lookup), byte for byte, from the file as committed in faa3238 (the only commit that touched it; unchanged
  at HEAD cbb04ac and in the working tree on 15 Oct 2026). `FROZEN_SPAN_SHA256` is its sha256, equal to the sha256
  of `git show faa3238:withholding/score/think_registry.py | sed -n 38,155p`; `frozen_span()` re-reads it from this
  file, and `tests/typed/test_registry.py` checks the hash.
- `_delivered_answer_legacy`, `_log_once`, `thinking_rule` and `delivered_answer` are
  `withholding/score/programmatic.py:240-311` as committed in e7d3d1d (the last commit that touched that file;
  unchanged at HEAD). The only edits, verified by diff on 15 Oct: `think_registry.lookup` and `think_registry.row_key`
  read the frozen `lookup` and `row_key`, the logger is this module's, and one log message and one docstring name
  the frozen registry.
- `runner_split` is the runner's legacy split (`withholding/run/modal_vllm.py:230` and `:238`), which fills the stored
  `answer` and `reasoning` fields.

Nothing here is a reading rule of the typed layer (rule D lives in `withholding.typed.ingest`). These functions exist
so that step 1 can prove byte identity with today's code, and so that D16's guard can compare the frozen 14 Oct
reading with rule D on every ImpossibleBench row.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import logging
from dataclasses import dataclass
from functools import cache
from pathlib import Path

FROZEN_FROM = "withholding/score/think_registry.py:38-155 at commit faa3238840dd9619b788d6e5e5d7c4acaee7ba2c"
FROZEN_SPAN_SHA256 = "10094b359b2fc947feee9505c2dfe3ab2d763a053a0b8810d41f95bf3aa2e061"
_BEGIN = "# ---- BEGIN FROZEN SPAN (withholding/score/think_registry.py:38-155, byte for byte) ----\n"
_END = "# ---- END FROZEN SPAN ----\n"


def frozen_span() -> bytes:
    """The bytes between the BEGIN and END markers of this file: the frozen copy of think_registry.py:38-155."""
    raw = Path(__file__).read_bytes()
    b, e = raw.index(_BEGIN.encode()) + len(_BEGIN), raw.index(_END.encode())
    return raw[b:e]


def frozen_span_ok() -> bool:
    """True when the frozen span still hashes to FROZEN_SPAN_SHA256 (nobody edited the copy)."""
    return hashlib.sha256(frozen_span()).hexdigest() == FROZEN_SPAN_SHA256


# ---- BEGIN FROZEN SPAN (withholding/score/think_registry.py:38-155, byte for byte) ----
# Template facts, keyed by sha256(template text)[:12]. tail = the end of the prompt with add_generation_prompt=True.
TEMPLATES = {
    "6d549883b5ed": {"source": "allenai/Olmo-3-7B-Think chat_template.jinja (also shipped by RL-Zero Code/IF/General/Mix)",
                     "think_forced": True, "tail": "<|im_start|>assistant\n<think>"},
    "bbff3bab94f2": {"source": "allenai/Olmo-3-7B-RL-Zero-Math chat_template.jinja (bare completion, no chat tokens)",
                     "think_forced": False, "tail": 'Remember to put your answer on its own line after "Answer:"'},
    "1d357aa3a95c": {"source": "nvidia/Nemotron-Cascade-8B tokenizer_config.json",
                     "think_forced": False, "tail": " /think<|im_end|>\n<|im_start|>assistant\n (/no_think when off)"},
    "a55ee1b16601": {"source": "Qwen/Qwen3-1.7B and Qwen/Qwen3-4B tokenizer_config.json",
                     "think_forced": False, "tail": "<|im_start|>assistant\n (thinking on)"},
}

THINK_TEMPLATE_FORMAT = ("the released Olmo 3 Think reasoning models (Think-SFT, Think-DPO, Think): notes/olmo3_design.md:10 "
                         "(the generation prompt ends in <|im_start|>assistant\\n<think>, thinking is forced) and "
                         "notes/prereg_olmo3.md:3-4 (the smoke run checked the think split before Phase 1); the reasoning "
                         "goes in the block and the answer after </think>, which the runner splits on")
NOT_ON_RECORD = ("not on record: the template forces the block open, but the RL-Zero training format (and a base "
                 "model's) was not read; today's rule is kept until the owner records it with a citation")
CONTENT_RULE = "template does not open the block: a row is a thinking row when its output opens one"


@dataclass(frozen=True)
class Entry:
    """One verified (model, revision or subfolder, template source, kwargs) family. Patterns use fnmatch; revision "*"
    only where the template comes from template_from, so the checkpoint revision cannot change the render."""
    model: str
    revision: str
    subfolder: str | None
    template_from: str
    kwargs: str
    template: str
    answer_channel: str | None
    basis: str
    verified_on: tuple

    @property
    def think_forced(self) -> bool:
        return TEMPLATES[self.template]["think_forced"]


def _kw(**k) -> str:
    """chat_template_kwargs as the registry key holds them (JSON, sorted keys)."""
    return json.dumps(k, sort_keys=True)


_ON = _kw(enable_thinking=True)
_OFF = _kw(enable_thinking=False)
_CASCADE_STAGES = "Nemotron-Cascade-8B-*"
_GRPO = "/root/.cache/huggingface/grpo/*"
_RAFT = "/root/.cache/huggingface/raft/*"

ENTRIES = (
    # Olmo 3 Think lineage under the Think template: forced open, answer after </think>
    *(Entry(m, "*", None, "allenai/Olmo-3-7B-Think", _ON, "6d549883b5ed", "after_think", THINK_TEMPLATE_FORMAT, v)
      for m, v in (("allenai/Olmo-3-7B-Think", ("olmo3/think/rlvr", "olmo3/think_ext/rlvr", "olmo3/traj/step_0050",
                                                "olmo3/traj/step_1375", "olmo3/smoke")),
                   ("allenai/Olmo-3-7B-Think-SFT", ("olmo3/think/sft", "olmo3/think_ext/sft")),
                   ("allenai/Olmo-3-7B-Think-DPO", ("olmo3/think/dpo", "olmo3/think_ext/dpo")))),
    # RL-Zero runs and the base model under the Think template: forced open, answer channel not on record
    *(Entry(m, "main", None, "allenai/Olmo-3-7B-Think", _ON, "6d549883b5ed", None, NOT_ON_RECORD, (v,))
      for m, v in (("allenai/Olmo-3-7B-RL-Zero-Code", "olmo3/rlzero/code"),
                   ("allenai/Olmo-3-7B-RL-Zero-IF", "olmo3/rlzero/if"),
                   ("allenai/Olmo-3-7B-RL-Zero-General", "olmo3/rlzero/general"),
                   ("allenai/Olmo-3-1025-7B", "olmo3/rlzero/base_think"))),
    # RL-Zero-Math's bare completion template: no think tag
    *(Entry(m, "main", None, "allenai/Olmo-3-7B-RL-Zero-Math", _ON, "bbff3bab94f2", "after_think", CONTENT_RULE, (v,))
      for m, v in (("allenai/Olmo-3-7B-RL-Zero-Math", "olmo3/rlzero/math"),
                   ("allenai/Olmo-3-1025-7B", "olmo3/rlzero/base_math"))),
    # Nemotron-Cascade: every stage (and Qwen3-8B-Base) under the final model's template, thinking on or off
    *(Entry(m, "main", sub, "nvidia/Nemotron-Cascade-8B", kw, "1d357aa3a95c", "after_think", CONTENT_RULE, v)
      for m, sub, kw, v in (
          ("nvidia/Nemotron-Cascade-8B", None, _ON, ("cascade/think_ext/final", "cascade/think_extra/final")),
          ("nvidia/Nemotron-Cascade-8B-Intermediate-ckpts", _CASCADE_STAGES, _ON,
           ("cascade/think/sft", "cascade/drift/ifrl", "cascade/intervention/ifrl")),
          ("nvidia/Nemotron-Cascade-8B", None, _OFF, ("cascade/no_think/final",)),
          ("nvidia/Nemotron-Cascade-8B-Intermediate-ckpts", _CASCADE_STAGES, _OFF, ("cascade/no_think/sft",)),
          ("Qwen/Qwen3-8B-Base", None, _OFF, ("cascade/no_think/base",)))),
    # Qwen3 (C pilots, OOD, dose check, P2/P3, C smoke): thinking on, the model opens the block itself
    *(Entry(m, "main", None, src, _ON, "a55ee1b16601", "after_think", CONTENT_RULE, v)
      for m, src, v in (
          ("Qwen/Qwen3-1.7B", "Qwen/Qwen3-1.7B", ("pilots/p2/qwen3_1p7b",)),
          (_GRPO, "Qwen/Qwen3-1.7B", ("c_pilot/a/step_40", "c_pilot_ap/ap/step_40", "ood/eval/c_pilot_a")),
          (_RAFT, "Qwen/Qwen3-1.7B", ("pilots/p3/eval_pi_a",)),
          ("Qwen/Qwen3-4B", "Qwen/Qwen3-4B", ("pilots/c_smoke/qwen3_4b",)))),
    Entry("Qwen/Qwen3-1.7B", "main", None, "<own>", _ON, "a55ee1b16601", "after_think", CONTENT_RULE,
          ("c_data/dose_check", "ood/eval/step0")),
    # Not listed: Tülu 3 / 3.1 and Llama-3.1-8B-Instruct (no think tag in the Tülu template; none of their 274,784
    # rows opens or closes a think block on 14 Oct 2026, so both rules agree; several runs have no prompt_render_hash
    # and the gated Llama template was not rendered), results/smoke (Qwen3-0.6B, thinking off). They keep today's rule.
)


def row_key(r: dict) -> tuple:
    """The registry key of an output row; "<own>" = the run passed no chat_template_from (the model's own template)."""
    kw = (r.get("sampling") or {}).get("chat_template_kwargs") or {}
    return (r.get("model"), r.get("revision"), r.get("subfolder"), r.get("chat_template_from") or "<own>",
            json.dumps(kw, sort_keys=True))


def _match(pattern: str | None, value) -> bool:
    if pattern is None:
        return value in (None, "")
    return value is not None and fnmatch.fnmatchcase(str(value), pattern)


@cache
def _lookup(key: tuple) -> Entry | None:
    model, revision, subfolder, template_from, kwargs = key
    for e in ENTRIES:
        if (e.template_from == template_from and e.kwargs == kwargs and _match(e.model, model)
                and _match(e.revision, revision) and _match(e.subfolder, subfolder)):
            return e
    return None


def lookup(r: dict) -> Entry | None:
    """The registry entry of an output row, or None for a family not in the registry."""
    return _lookup(row_key(r))
# ---- END FROZEN SPAN ----

THINK_OPEN = "<think>"
THINK_CLOSE = "</think>"
log = logging.getLogger(__name__)


def runner_split(output: str) -> tuple[str | None, str]:
    """(reasoning, answer) as the runner stores them: `withholding/run/modal_vllm.py:230` splits on the last close, and
    `:238` stores reasoning (None when there is no close) and answer (the text after the close, else the output)."""
    reasoning, sep, answer = output.rpartition(THINK_CLOSE)
    return (reasoning if sep else None), (answer if sep else output)


# `withholding/score/programmatic.py:240-311` at commit e7d3d1de, reading the frozen registry above.
def _delivered_answer_legacy(r: dict) -> tuple[str, bool]:
    """delivered_answer as it was until 14 Oct 2026: a row counted as thinking only when '<think>' occurred in the first
    200 characters of its text, and a row the runner had split fell back to the whole output when its answer was empty.
    Kept for the families that keep today's rule (see thinking_rule) and for scripts/rescore_forced_think.py, which
    compares it with the new rule to find the rows that change."""
    text = r.get("answer") or r.get("output") or ""
    if r.get("reasoning") is not None:
        return text, True
    if "<think>" in text[:200]:
        i = text.rfind(THINK_CLOSE)
        if i < 0:
            return "", False
        return text[i + len(THINK_CLOSE):], True
    return text, True


_logged: set = set()


def _log_once(key: tuple, msg: str) -> None:
    """One warning per (family key, message) per process."""
    if (key, msg) not in _logged:
        _logged.add((key, msg))
        log.warning("%s: %s", msg, key)


def thinking_rule(r: dict) -> dict | None:
    """14 Oct 2026: forced-think templates. {"think_forced": bool} when the think-block rule applies to the row's
    family, None when the family keeps the rule used before 14 Oct 2026 (logged once per family).

    think_forced = the template opened the think block in the prompt. It comes from the row's own stamp
    (withholding/run/modal_vllm.py writes it since 14 Oct 2026) or, for rows written before, from the frozen 14 Oct
    registry above. None for a family in neither (unknown), and for a registry family whose answer channel is not on
    record (RL-Zero Code / IF / General, the base model under the Think template): their template forces the block
    open but they almost never close it, and how they were trained to answer is not on record."""
    e = lookup(r)
    stamp = r.get("think_forced")
    if e is not None and e.answer_channel is None:
        _log_once(row_key(r), "answer channel not on record, today's delivered-answer rule kept")
        return None
    if isinstance(stamp, bool):
        if e is not None and stamp != e.think_forced:
            _log_once(row_key(r), "think_forced stamp disagrees with the registry, the stamp is used")
        return {"think_forced": stamp}
    if e is not None:
        return {"think_forced": e.think_forced}
    _log_once(row_key(r), "family not in the frozen 14 Oct registry, today's delivered-answer rule kept")
    return None


def delivered_answer(r: dict) -> tuple[str, bool]:
    """(answer text, delivered): the text a reader of the answer gets, and whether the row delivered one.

    14 Oct 2026: forced-think templates. A thinking row is one whose output opens a think block (its first
    non-whitespace text is <think>) or whose template opened the block in the prompt (thinking_rule: the row's stamp,
    or the registry for older rows; the Olmo 3 Think template ends the prompt with <think>, so Olmo traces never begin
    with it and were read as delivered answers before this date). A row that closes a think block delivers the text
    after its last </think>, and delivered nothing when that text is empty or whitespace (the old fallback to the whole
    output scored those rows on their reasoning). A thinking row that never closes the block delivered nothing. Any
    other row delivers its whole output. The rule uses no count, position cut-off or share; it replaces the test
    '<think>' in the first 200 characters. Families thinking_rule does not cover keep _delivered_answer_legacy."""
    rule = thinking_rule(r)
    if rule is None:
        return _delivered_answer_legacy(r)
    text = r.get("output") or ""
    i = text.rfind(THINK_CLOSE)
    if i >= 0:
        answer = text[i + len(THINK_CLOSE):]
        return (answer, True) if answer.strip() else ("", False)
    if rule["think_forced"] or text.lstrip().startswith(THINK_OPEN):
        return "", False
    return text, True
