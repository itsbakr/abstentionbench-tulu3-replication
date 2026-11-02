"""The typed layer's registry: TemplateSpec entries, the render and delivery probes, and the OwnerDecision registry.

Design: `notes/typed_ingestion_design_2026-10-15.md` (cited "design N"), sections 2.1 (TemplateSpec, invariants 1 to 8),
2.3 (rule D and its outcome table), 2.8 (OwnerDecision), 3 (registry load) and 4 (the template layer); decisions:
`notes/typed_layer_decisions_2026-10-15.md` (OD-1 to OD-5, D1 to D21). Step 0 changes no behaviour: nothing that scores
reads this module yet, and `withholding/score/think_registry.py` keeps serving its legacy callers unchanged (the 14 Oct
registry is frozen, byte for byte, in `withholding/typed/legacy.py`).

What is declared and what is derived
------------------------------------
Each family on disk has one `Source` below: the facts a person writes, each with a citation (design 2.1 invariant 5:
the template, the trained answer channel, the BOS policy, the trained stop strings and the tool slot), plus the pinned
40-hex revisions (invariant 4) and the template's full sha256. Everything else is DERIVED by the render probe from the
tokenizer files at the pinned revisions in the local Hugging Face cache (offline; no weights): the generation prefix
text and ids, `think_open_in_prompt` and the template_* channels, the marker ids, the special ids, the role names and
turn-start ids from a two-turn render, the no-tools marker from renders with and without a probe tool, the default
system line, and `accepted_kwargs` (jinja2.meta names, kept only when flipping the kwarg changes the render).

The derived values are pinned in `registry_pins.v1.json` beside this file (written by `python -m
withholding.typed.registry pin`). `load_registry()` derives them again and refuses any value that does not reproduce
(invariant 6), recomputes every spec_id against its pin (invariant 5), and runs the delivery probe: rule D through
`withholding.typed.ingest`'s content core on synthetic completions built from each entry's own markers and role names,
checked against the outcome table of design 2.3 written below from the owner's decisions (invariant 7). Any failure is
a `RegistryError` (invariant 8). Every rule is content-defined: a marker, a role line, a sentinel string's position in
a render; no count, window or share enters a derivation.

Tokenization uses the `tokenizers` library on the cached tokenizer.json (the recipe synthesis found transformers 5.18's
AutoTokenizer mis-tokenizes the Olmo files: notes/reviews/2026-10-14_fidelity_synthesis_model_recipes.md:9-11), and
encodes rendered text with add_special_tokens=False, as vLLM 0.10+ llm.chat does
(notes/reviews/2026-10-14_tulu_fidelity.md:26). Templates render through transformers' own `render_jinja_template`
with the named special tokens it passes (transformers tokenization_utils_base.py:3108), so a render equals the runner's.

The OwnerDecision registry reads the decisions note through `models.load_decisions` (every record by heading and
content sha, `models.section_sha`, its grants line by line), checks the note's Index against its headings and owns
the pin file `owner_decisions.pins.json`. The note carries the owner's line of 17 Oct and loads "confirmed" against
that pin. Only `check` writes the pin (on the first load after a new dated line); every other load, the import-time
one included, reads it, and raises RegistryError when a pinned owner's line was edited or removed, or when a record
changed, was added or was removed, or the Confirmation section changed, with no new dated line (design 2.8, Revision
6). Without any owner's line the note loads its records and scopes "unsigned" and `pin()` refuses (D11). Nothing in
the template layer depends on it.

Invariant 8: importing this module loads the registry (`REGISTRY`), so a probe that does not reproduce raises
RegistryError before anything that imports it can run or score. Running the file as a script (`python -m
withholding.typed.registry ...`) skips that load, so `pin` can rewrite stale pins.

    .venv/bin/python -m withholding.typed.registry derive [NAME ...]   # print derived values (no write)
    .venv/bin/python -m withholding.typed.registry pin                 # write registry_pins.v1.json
    .venv/bin/python -m withholding.typed.registry check               # load, probes, owner status; writes its pin
    .venv/bin/python -m withholding.typed.registry fetch               # download tokenizer files only (no weights)
    .venv/bin/python -m withholding.typed.registry report              # results/_ingest/registry_<date>.{json,md}

The renderers oracle (D6) that cross-checks the delivery probe lives in `withholding/typed/oracle.py`.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from functools import cache
from pathlib import Path
from typing import Any, Literal

from withholding.typed import ingest, models
from withholding.typed.models import (
    BosPolicy,
    Citation,
    RegistryError,
    TemplateSpec,
    canonical_json,
    sha256_hex,
)

ROOT = Path(__file__).resolve().parents[2]
PINS_PATH = Path(__file__).with_name("registry_pins.v1.json")
DECISIONS_NOTE = ROOT / "notes" / "typed_layer_decisions_2026-10-15.md"
OWNER_PINS_PATH = Path(__file__).with_name("owner_decisions.pins.json")
RETRIEVED = date(2026, 10, 15)   # every citation below was re-read on this date
OPEN, CLOSE = "<think>", "</think>"
HEX40 = re.compile(r"[0-9a-f]{40}")

# Names transformers supplies to every chat-template render, so a template naming them reads no run kwarg:
# messages, tools, documents and add_generation_prompt (chat_template_utils.render_jinja_template), the env globals
# raise_exception and strftime_now, and the named special tokens (tokenization_utils_base.py:3108, special_tokens_map).
SPECIAL_TOKEN_ATTRS = ("bos_token", "eos_token", "unk_token", "sep_token", "pad_token", "cls_token", "mask_token")
STANDARD_RENDER_NAMES = frozenset({"messages", "tools", "documents", "add_generation_prompt", "raise_exception",
                                   "strftime_now", *SPECIAL_TOKEN_ATTRS})
# Probe sentinels: plain ASCII words that no template emits, so their positions in a render are content facts.
S_SYS, S_USER1, S_ASST, S_USER2, S_TOOLDESC = "QQSYSPROBEQQ", "QQUSERONEQQ", "QQASSTPROBEQQ", "QQUSERTWOQQ", "QQTOOLQQ"
PROBE_TOOL_NAME = "probe_tool"


# ====================================================================================================== sources
@dataclass(frozen=True)
class Source:
    """One registry entry's declared facts (design 2.1). `name` labels the family; the row-key fields (model,
    revision, subfolder, template source) select which stored rows it covers. `template_from` is the repo whose
    template text renders the prompt: a row with no chat_template_from renders with its own model repo's template
    (withholding/run/modal_vllm.py:209, `_load_chat_template(None)` is None, so llm.chat uses the tokenizer's own)."""

    name: str
    model_pattern: str
    revision_patterns: tuple[str | None, ...]   # fnmatch over the row's `revision`; None: the row records none
    subfolder_pattern: str | None
    template_from: str
    template_file: Literal["chat_template.jinja", "tokenizer_config.json"]
    template_subfolder: str | None
    template_revision: str
    template_sha: str
    tokenizer_from: str
    tokenizer_subfolder: str | None
    tokenizer_revision: str
    kwargs: Mapping[str, bool]
    model_opens_block: bool          # declared: trained to open a block itself (model_opens), else none (design 2.1)
    trained_answer_channel: str
    trained_stop_strings: tuple[str, ...]
    tool_slot: Literal["tools_kwarg", "system_functions_field", "none"]
    bos_expected_at_start: int
    stop_ids: tuple[int, ...] | None  # None: the runner passed none, so vLLM stops on the tokenizer's eos
    trained_decoding: Mapping[str, float] | None
    cites: Mapping[str, str]
    legacy_template_key: str | None = None   # the 14 Oct TEMPLATES key (legacy.py), where that registry lists it
    kwargs_from_thinking: bool = False       # rows carry no chat kwargs; the runner passed enable_thinking=thinking
    oracle_renderer: Literal["qwen3", "default"] = "default"   # design 4's table: which renderers class parses it


def _src(**kw) -> Source:
    return Source(**kw)


# --- shared citations (file:line as of 15 Oct 2026; HEAD cbb04ac) --------------------------------------------------
_CASCADE = "notes/reviews/2026-10-14_cascade_fidelity.md"
_OLMO = "notes/reviews/2026-10-14_olmo3_fidelity.md"
_TULU = "notes/reviews/2026-10-14_tulu_fidelity.md"
_SYNTH = "notes/reviews/2026-10-14_fidelity_synthesis_model_recipes.md"
_DESIGN = "notes/typed_ingestion_design_2026-10-15.md"
_RUNNER_TPL = ("withholding/run/modal_vllm.py:178-189,209,217 (the template text is fetched at main and passed to "
               "llm.chat; no chat_template_from renders with the tokenizer's own)")
_VLLM_EOS = ("withholding/run/modal_vllm.py:210-214 (no stop ids passed: vLLM stops on the tokenizer's eos; "
             "generation_config='vllm' keeps generation_config.json out); " + _TULU + ":50")

CASCADE_FINAL, CASCADE_FINAL_REV = "nvidia/Nemotron-Cascade-8B", "276a779fe0c1fe2d63a68fd573fec7b4b0a1907e"
CASCADE_STAGES, CASCADE_STAGES_REV = ("nvidia/Nemotron-Cascade-8B-Intermediate-ckpts",
                                      "9b379bd8f8ecb1feb19825efefe319bd30d8a223")
CASCADE_TPL = "1d357aa3a95cc57d98140d0ecbff42761eb749ef73eb9766535878259887b4d8"
_CASCADE_CITES = {
    "template": (f"{_CASCADE}:52-57 (final template; the intermediate card: every stage uses the final model's "
                 f"template); withholding/score/think_registry.py:106-114 (every stage and Qwen3-8B-Base under it, its "
                 f"render hashes reproduced 14 Oct); {_RUNNER_TPL}"),
    "bos": f"{_CASCADE}:68 (bos_token null, add_bos_token false) and :119 (stored token counts match a no-BOS render)",
    "trained_stop_strings": f"{_CASCADE}:70-71 (official inference passes no stop ids and cuts at <|im_end|>)",
    "tool_slot": f"{_CASCADE}:47-48 (tools in the system prompt inside <tools></tools>; the template's tools branch)",
    "stop_ids": f"scripts/run_cascade.sh:24 (--stop-token-ids 151645,151643); {_CASCADE}:120",
}
_CASCADE_THINK = {
    "trained_answer_channel": (f"{_CASCADE}:61-63 (NVIDIA's evaluation splits at the FIRST </think> in either mode) "
                               f"and :45-46 (report 3.1.2 SFT format: reasoning in the block, the answer after it)"),
    "reasoning_channel": f"{_CASCADE}:54-55 (' /think' on the last user turn; no think prefill: the model opens it)",
    "kwargs": "withholding/score/think_registry.py:107-111 (enable_thinking true); scripts/run_cascade.sh:24",
}
_CASCADE_NO_THINK = {
    "trained_answer_channel": (f"{_CASCADE}:45-47 (report 3.1.2: the empty <think></think> block is omitted in the "
                               f"non-thinking mode, so the turn is the answer)"),
    "reasoning_channel": f"{_CASCADE}:45-47 (non-thinking mode: no block is trained in the turn)",
    "kwargs": "withholding/score/think_registry.py:112-114 (enable_thinking false); scripts/run_cascade.sh:24",
}
CASCADE_STAGE_FOLDERS = ("Nemotron-Cascade-8B-SFT", "Nemotron-Cascade-8B-RLHF", "Nemotron-Cascade-8B-IFRL",
                         "Nemotron-Cascade-8B-MathRL", "Nemotron-Cascade-8B-CodeRL")


def _cascade(name: str, model: str, model_rev: str, sub: str | None, think: bool) -> Source:
    return _src(
        name=name, model_pattern=model, revision_patterns=("main",), subfolder_pattern=sub,
        template_from=CASCADE_FINAL, template_file="tokenizer_config.json", template_subfolder=None,
        template_revision=CASCADE_FINAL_REV, template_sha=CASCADE_TPL,
        tokenizer_from=model, tokenizer_subfolder=sub, tokenizer_revision=model_rev,
        kwargs={"enable_thinking": think}, model_opens_block=think,
        trained_answer_channel="after_close" if think else "whole", trained_stop_strings=(),
        tool_slot="tools_kwarg", bos_expected_at_start=0, stop_ids=(151645, 151643), trained_decoding=None,
        cites={**_CASCADE_CITES, **(_CASCADE_THINK if think else _CASCADE_NO_THINK)},
        legacy_template_key="1d357aa3a95c")


_CASCADE_SOURCES = (
    _cascade("cascade/final/think", CASCADE_FINAL, CASCADE_FINAL_REV, None, True),
    _cascade("cascade/final/no_think", CASCADE_FINAL, CASCADE_FINAL_REV, None, False),
    *(_cascade(f"cascade/{f.rsplit('-', 1)[1].lower()}/{m}", CASCADE_STAGES, CASCADE_STAGES_REV, f, t)
      for f in CASCADE_STAGE_FOLDERS for m, t in (("think", True), ("no_think", False))),
    _src(name="cascade/qwen3_8b_base/no_think", model_pattern="Qwen/Qwen3-8B-Base", revision_patterns=("main",),
         subfolder_pattern=None, template_from=CASCADE_FINAL, template_file="tokenizer_config.json",
         template_subfolder=None, template_revision=CASCADE_FINAL_REV, template_sha=CASCADE_TPL,
         tokenizer_from="Qwen/Qwen3-8B-Base", tokenizer_subfolder=None,
         tokenizer_revision="49e3418fbbbca6ecbdf9608b4d22e5a407081db4",
         kwargs={"enable_thinking": False}, model_opens_block=False, trained_answer_channel="untrained",
         trained_stop_strings=(), tool_slot="tools_kwarg", bos_expected_at_start=0, stop_ids=(151645, 151643),
         trained_decoding=None, legacy_template_key="1d357aa3a95c",
         cites={**_CASCADE_CITES,
                "trained_answer_channel": ("a pretrained base checkpoint, run as Cascade's stage 0 "
                                           "(withholding/score/think_registry.py:114; " + _DESIGN + ":837)"),
                "reasoning_channel": "a base model: no block is trained (" + _DESIGN + ":837)",
                "trained_stop_strings": "a base model has no trained stop string; the runner's stops: "
                                        "scripts/run_cascade.sh:24",
                "kwargs": "withholding/score/think_registry.py:114 (enable_thinking false)"}),
)

# --- Olmo 3 -------------------------------------------------------------------------------------------------------
OLMO_THINK, OLMO_THINK_REV = "allenai/Olmo-3-7B-Think", "d97e442d7cc678210054dbcc9b440894d62c89a4"
OLMO_MATH, OLMO_MATH_REV = "allenai/Olmo-3-7B-RL-Zero-Math", "dee26a4074b88215cd1326472e1ab14d0259d892"
OLMO_BASE, OLMO_BASE_REV = "allenai/Olmo-3-1025-7B", "a81bae42db3975be1671e27b9c9a56da1a9f980f"
OLMO_THINK_TPL = "6d549883b5ed12879e191845c256a30c7dfd4eced0a4f160060a3ea0199d9e3a"
OLMO_MATH_TPL = "bbff3bab94f2df1534d5971cb5ef47bfa3b06f1fb56965cc70dbcf261e72d3fa"
_OLMO_STOPS = "scripts/run_olmo_stages.sh:14, scripts/_rlzero_one.sh:24 (--stop-token-ids 100265,100257)"
_OLMO_THINK_TEMPLATE = (f"{_OLMO}:43-46 (T1: Think, DPO and RLVR were trained with the Hub chat_template.jinja, "
                        f"open-instruct olmo_thinker; generation prompt <|im_start|>assistant\\n<think>); {_RUNNER_TPL}")
_OLMO_TOOLS = (f"the template reads message.functions on a system or user message; {_SYNTH}:57 (V6: When2Call tools "
               f"sit in the system text, so the template adds the no-functions line)")
_OLMO_THINK_BOS = (f"{_OLMO}:53-56 (T2: training prompt ids start at 100264, no BOS) and :63-64 (T3: tokenizer.json "
                   f"post_processor null, no BOS is ever added); W&B add_bos false ({_OLMO}:45-46)")


def _olmo(name: str, model: str, rev: str, revs: tuple, channel: str, channel_cite: str, *, template_from=OLMO_THINK,
          template_rev=OLMO_THINK_REV, template_sha=OLMO_THINK_TPL, template_file="chat_template.jinja",
          tool_slot="system_functions_field", stop_strings=(), stop_cite=None, decoding=None, decoding_cite=None,
          bos_cite=_OLMO_THINK_BOS, template_cite=_OLMO_THINK_TEMPLATE, model_opens=False, extra=None,
          legacy="6d549883b5ed") -> Source:
    cites = {"template": template_cite, "trained_answer_channel": channel_cite, "bos": bos_cite,
             "trained_stop_strings": stop_cite or (f"{_OLMO}:114-115 (T8: stop on eos [100265, 100257], no stop "
                                                   f"string)"),
             "tool_slot": _OLMO_TOOLS if tool_slot != "none" else
             f"{_OLMO}:83-86 (T5: the bare olmo_thinker_dapo template reads no tools)",
             "stop_ids": _OLMO_STOPS,
             "kwargs": ("the stored rows carry enable_thinking true (withholding/score/think_registry.py:91,97,103), "
                        "which this template does not read (audit 28): it is an ignored kwarg")}
    if decoding is not None:
        cites["trained_decoding"] = decoding_cite
    cites.update(extra or {})
    return _src(name=name, model_pattern=model, revision_patterns=revs, subfolder_pattern=None,
                template_from=template_from, template_file=template_file, template_subfolder=None,
                template_revision=template_rev, template_sha=template_sha, tokenizer_from=model,
                tokenizer_subfolder=None, tokenizer_revision=rev, kwargs={}, model_opens_block=model_opens,
                trained_answer_channel=channel, trained_stop_strings=stop_strings, tool_slot=tool_slot,
                bos_expected_at_start=0, stop_ids=(100265, 100257), trained_decoding=decoding, cites=cites,
                legacy_template_key=legacy)


_THINK_CHANNEL = (f"{_OLMO}:43-46 (T1) and :118 (T8: report p.40, thinking traces are stripped before scoring); "
                  f"notes/olmo3_design.md:10; notes/prereg_olmo3.md:3-4")
_RLZERO_CHANNEL = (f"{_OLMO}:99-105 (T6: open-instruct d928a7c remove_thinking_section keeps the text after the last "
                   f"</think>, the whole text when there is none) and :325-337 (F6); {_SYNTH}:75 (N10); W&B runs "
                   f"xleoveqq (Code), wn9zgjj3 (IF), 0egjzr3s (General), {_OLMO}:33-36 and :75-82 (T5)")
_RLZERO_STOP = f"{_OLMO}:76 (T5: W&B stop_strings ['</answer>'] for Code, IF and General 3.0); {_SYNTH}:55 (V4)"
_RLZERO_DECODING = f"{_OLMO}:77 (T5: W&B temperature 1, vllm_top_p 1)"
_RLZERO_BOS = f"{_OLMO}:78 (T5: W&B add_bos false); the template emits no bos_token"
_BASE_UNTRAINED = (f"{_DESIGN}:842 (`untrained` for the base) and {_OLMO}:107-110 (T7: the base has no chat template "
                   f"and never saw the chat special tokens)")
_BASE_BOS = f"{_OLMO}:107 (T7: the base tokenizer's bos_token is null); the template emits none"

_OLMO_SOURCES = (
    _olmo("olmo3/think", OLMO_THINK, OLMO_THINK_REV, ("main", "step_*"), "after_close", _THINK_CHANNEL,
          decoding={"temperature": 1.0}, decoding_cite=f"{_OLMO}:115-116 (T8: Think RL training temperature 1.0)",
          extra={"tokenizer_revision": (f"{_OLMO}:22-26 (the Hub tree API gives the same blob ids for chat_template.jinja, "
                              f"tokenizer.json, tokenizer_config.json, special_tokens_map.json, vocab.json and "
                              f"merges.txt in all 28 step refs used and main)")}),
    _olmo("olmo3/think_dpo", "allenai/Olmo-3-7B-Think-DPO", "7b18bf927b430ff06376fdfa5610eb3b1b6a5c38", ("main",),
          "after_close", _THINK_CHANNEL),
    _olmo("olmo3/think_sft", "allenai/Olmo-3-7B-Think-SFT", "6ff857587e040d6d523a3d5f3a56e918f5401d66", ("main",),
          "after_close", f"{_OLMO}:124 (Think-SFT row: training format unverified, OLMo-core pre-tokenized; the SFT "
          f"data puts the answer after the block); {_THINK_CHANNEL}",
          template_cite=(f"{_SYNTH}:72 (N7: Think-SFT is prompted with the DPO/RLVR template 6d549883, not its own "
                         f"fb2b8736); {_OLMO_THINK_TEMPLATE}")),
    *(_olmo(f"olmo3/rlzero_{k}", f"allenai/Olmo-3-7B-RL-Zero-{m}", rev, ("main",), "after_close_else_whole",
            _RLZERO_CHANNEL, stop_strings=("</answer>",), stop_cite=_RLZERO_STOP,
            decoding={"temperature": 1.0, "top_p": 1.0}, decoding_cite=_RLZERO_DECODING, bos_cite=_RLZERO_BOS,
            template_cite=(f"{_OLMO}:76,80-82 (T5: W&B chat_template_name olmo_thinker, the Hub Think template); "
                           f"{_SYNTH}:55 (V4); {_RUNNER_TPL}"))
      for k, m, rev in (("code", "Code", "a961af69d75f9c52b3ae4db7b1664d890229b7ca"),
                        ("if", "IF", "3cae007c5324a9a06ee6780f03b848bc7b8fd440"),
                        ("general", "General", "24e5814cb36944d3eb36a49679d02c2b3bb46195"))),
    _olmo("olmo3/rlzero_math", OLMO_MATH, OLMO_MATH_REV, ("main",), "whole",
          (f"{_OLMO}:83-86 (T5: Math 3.0 trained with olmo_thinker_dapo, bare text) and :128 (no <think> in the "
           f"prompt, no chat tokens): there is no block to split; the 3.0 math verifier's own reading was not read"),
          template_from=OLMO_MATH, template_rev=OLMO_MATH_REV, template_sha=OLMO_MATH_TPL, tool_slot="none",
          stop_cite=f"{_OLMO}:84 (T5: no stop strings)", decoding={"temperature": 1.0, "top_p": 1.0},
          decoding_cite=f"{_OLMO}:128 (trained 1.0/1.0/12000)", bos_cite=_RLZERO_BOS, legacy="bbff3bab94f2",
          template_cite=f"{_OLMO}:83-86 (T5: olmo_thinker_dapo hashes to bbff3bab94f2, the Hub file); {_RUNNER_TPL}",
          extra={"reasoning_channel": f"{_OLMO}:128 (bare template: no think block in the prompt or the training "
                                      f"template)"}),
    _olmo("olmo3/base_think", OLMO_BASE, OLMO_BASE_REV, ("main",), "untrained", _BASE_UNTRAINED,
          bos_cite=_BASE_BOS, stop_cite="a base model has no trained stop string; the runner's stops: " + _OLMO_STOPS,
          template_cite=(f"scripts/_rlzero_one.sh:7,23 (the base under the Think template, passed as text); "
                         f"{_SYNTH}:54 (V3); {_RUNNER_TPL}")),
    _olmo("olmo3/base_math", OLMO_BASE, OLMO_BASE_REV, ("main",), "untrained", _BASE_UNTRAINED,
          template_from=OLMO_MATH, template_rev=OLMO_MATH_REV, template_sha=OLMO_MATH_TPL, tool_slot="none",
          bos_cite=_BASE_BOS, stop_cite="a base model has no trained stop string; the runner's stops: " + _OLMO_STOPS,
          legacy="bbff3bab94f2",
          template_cite=f"withholding/score/think_registry.py:103-105 (base under the RL-Zero-Math template); "
                        f"{_RUNNER_TPL}",
          extra={"reasoning_channel": f"{_OLMO}:128 (bare template: no think block)"}),
)

# --- Qwen3 (C pilots, OOD, dose check, P2/P3, C smoke, results/smoke) -------------------------------------------------
QWEN_TPL = "a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8"
QWEN_BASE_TPL = "87a2728cb8dc9fe424d624542f6060ec05a1d285ebbec578bb078900e33396b5"
QWEN17, QWEN17_REV = "Qwen/Qwen3-1.7B", "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e"
_QWEN_TEMPLATE = ("withholding/score/think_registry.py:46,116-123 (Qwen3 entries; render hashes reproduced 14 Oct); "
                  + _RUNNER_TPL)
_QWEN_ON = {
    "trained_answer_channel": ("the Qwen3 thinking format: the template's assistant branch splits content at "
                               f"'</think>' into reasoning_content and content (template text); {_DESIGN}:1430"),
    "reasoning_channel": "thinking on: the generation prompt is <|im_start|>assistant\\n and the model opens the "
                         f"block itself ({_DESIGN}:1431)",
    "bos": f"bos_token null in tokenizer_config.json; no BOS id starts the prompt ({_DESIGN}:1430)",
    "trained_stop_strings": f"none beyond the stop ids the rows record ({_DESIGN}:1430)",
    "tool_slot": f"the template names tools ({_DESIGN}:1430)",
    "stop_ids": "scripts/run_pilot_gen.sh:11, scripts/run_c_pilot.sh:64 (--stop-token-ids 151645,151643)",
    "kwargs": "withholding/score/think_registry.py:116-123 (enable_thinking true)",
}


def _qwen(name: str, model: str, tok: str, tok_rev: str, channel_cite: str | None = None,
          channel: str = "after_close", extra: dict | None = None) -> Source:
    cites = {**_QWEN_ON, "template": _QWEN_TEMPLATE}
    if channel_cite:
        cites["trained_answer_channel"] = channel_cite
    cites.update(extra or {})
    return _src(name=name, model_pattern=model, revision_patterns=("main",), subfolder_pattern=None,
                template_from=QWEN17 if model.startswith("/root/") else model, template_file="tokenizer_config.json",
                template_subfolder=None, template_revision=QWEN17_REV if model.startswith("/root/") else tok_rev,
                template_sha=QWEN_TPL, tokenizer_from=tok, tokenizer_subfolder=None, tokenizer_revision=tok_rev,
                kwargs={"enable_thinking": True}, model_opens_block=True, trained_answer_channel=channel,
                trained_stop_strings=(), tool_slot="tools_kwarg", bos_expected_at_start=0,
                stop_ids=(151645, 151643), trained_decoding=None, cites=cites, legacy_template_key="a55ee1b16601",
                oracle_renderer="qwen3")


_C_TOKENIZER = ("the checkpoint's tokenizer is the base's: withholding/train/grpo_modal.py:480 (AutoTokenizer from "
                "the base) and :411 (saved beside the merged weights); raft_modal.py:155, :175; the local files were not read")
_QWEN_SOURCES = (
    _qwen("qwen3/1p7b", QWEN17, QWEN17, QWEN17_REV),
    _qwen("qwen3/4b", "Qwen/Qwen3-4B", "Qwen/Qwen3-4B", "1cfa9a7208912126459214e8b04321603b3df60c"),
    _qwen("qwen3/c_grpo", "/root/.cache/huggingface/grpo/*", QWEN17, QWEN17_REV,
          channel="after_close_else_whole",
          channel_cite=("the GRPO reward read the text after the last </think>, else the whole text: "
                        "withholding/train/c_rewards.py:82-85 (scorer_row) through grpo_modal.py:221"),
          extra={"tokenizer_from": _C_TOKENIZER,
                 "template": "--chat-template-from Qwen/Qwen3-1.7B (scripts/run_c_pilot.sh:125; withholding/train/grpo_modal.py:42); "
                             + _QWEN_TEMPLATE}),
    _qwen("qwen3/c_raft", "/root/.cache/huggingface/raft/*", QWEN17, QWEN17_REV,
          channel="after_close_else_whole",
          channel_cite=("RAFT kept the samples score_reliablemath rewarded on the runner row (answer after the last "
                        "</think>, else the output): scripts/pilot_p3_select.py:9-10,44-46"),
          extra={"tokenizer_from": _C_TOKENIZER,
                 "template": "--chat-template-from Qwen/Qwen3-1.7B (scripts/run_pilot_p3.sh:58); "
                             + _QWEN_TEMPLATE}),
)
_OFF_CHANNEL = ("thinking off: the template pre-fills an empty closed block (<think>\\n\\n</think>\\n\\n) and the "
                "turn is the answer (template text; " + _CASCADE + ":59-60 for the 87a2728c template)")
_SMOKE_SOURCES = (
    _src(name="qwen3/0p6b_smoke", model_pattern="Qwen/Qwen3-0.6B", revision_patterns=("main",),
         subfolder_pattern=None, template_from="Qwen/Qwen3-0.6B", template_file="tokenizer_config.json",
         template_subfolder=None, template_revision="c1899de289a04d12100db370d81485cdf75e47ca", template_sha=QWEN_TPL,
         tokenizer_from="Qwen/Qwen3-0.6B", tokenizer_subfolder=None,
         tokenizer_revision="c1899de289a04d12100db370d81485cdf75e47ca", kwargs={"enable_thinking": False},
         model_opens_block=True, trained_answer_channel="whole", trained_stop_strings=(), tool_slot="tools_kwarg",
         bos_expected_at_start=0, stop_ids=None, trained_decoding=None, oracle_renderer="qwen3",
         cites={**_QWEN_ON, "template": f"results/smoke/outputs_modal.jsonl rows (own template, revision main); "
                                        f"{_RUNNER_TPL}",
                "trained_answer_channel": _OFF_CHANNEL, "stop_ids": _VLLM_EOS,
                "kwargs": "results/smoke/outputs_modal.jsonl sampling.chat_template_kwargs (enable_thinking false)"}),
    _src(name="qwen3/0p6b_mlx_smoke", model_pattern="mlx-community/Qwen3-0.6B-4bit", revision_patterns=(None,),
         subfolder_pattern=None, template_from="mlx-community/Qwen3-0.6B-4bit", template_file="tokenizer_config.json",
         template_subfolder=None, template_revision="73e3e38d981303bc594367cd910ea6eb48349da8",
         template_sha=QWEN_BASE_TPL, tokenizer_from="mlx-community/Qwen3-0.6B-4bit", tokenizer_subfolder=None,
         tokenizer_revision="73e3e38d981303bc594367cd910ea6eb48349da8", kwargs={"enable_thinking": False},
         model_opens_block=True, trained_answer_channel="whole", trained_stop_strings=(), tool_slot="tools_kwarg",
         bos_expected_at_start=0, stop_ids=None, trained_decoding=None, kwargs_from_thinking=True,
         oracle_renderer="qwen3",
         cites={**_QWEN_ON,
                "template": ("withholding/run/local_mlx.py:24-33 (mlx_lm load; the tokenizer's own template, "
                             "apply_chat_template(tokenize=False)); the only cached snapshot of the repo"),
                "trained_answer_channel": _OFF_CHANNEL,
                "stop_ids": "withholding/run/local_mlx.py:34 (mlx_lm generate stops on the tokenizer's eos)",
                "kwargs": ("withholding/run/local_mlx.py:27,33 (enable_thinking=think from --thinking, recorded as "
                           "the row's `thinking`; the rows carry no sampling)")}),
)

# --- Tülu 3 / 3.1 and Llama-3.1-8B-Instruct ---------------------------------------------------------------------------
TULU_TPL = "ac7498a36a719da630e99d48e6ebc4409de85a77556c2b6159eeb735bcbd11df"
LLAMA_TPL = "e10ca381b1ccc5cf9db52e371f3b6651576caee0a630b452e2816b2d404d4b65"
_TULU_CITES = {
    "template": (f"{_TULU}:13 (tokenizer_config.json chat_template sha ac7498a3 in all four repos; paper Appendix "
                 f"B.3) and :43 (render hash 144881cb8b653772 reproduced on all 73 trajectory dirs); {_RUNNER_TPL}"),
    "trained_answer_channel": f"{_TULU}:13 and :32 (no thinking mode: the turn is the answer)",
    "reasoning_channel": f"{_TULU}:32 (no thinking mode); withholding/score/think_registry.py:124-126",
    "bos": (f"{_TULU}:17-20 (training add_bos off at every stage) and :44 (276,110 of 276,110 rows equal the no-BOS "
            f"render length); {_SYNTH}:58 (V7)"),
    "trained_stop_strings": f"{_TULU}:32 (stop: EOS <|end_of_text|> only)",
    "tool_slot": f"{_TULU}:13 (the template reads no tools)",
    "stop_ids": _VLLM_EOS,
}


def _tulu(name: str, model: str, rev: str, revs: tuple, decoding: dict | None = None, extra=None) -> Source:
    cites = dict(_TULU_CITES)
    if decoding:
        cites["trained_decoding"] = f"{_TULU}:35-36 (PPO and GRPO at temperature 1.0)"
    cites.update(extra or {})
    return _src(name=name, model_pattern=model, revision_patterns=revs, subfolder_pattern=None, template_from=model,
                template_file="tokenizer_config.json", template_subfolder=None, template_revision=rev,
                template_sha=TULU_TPL, tokenizer_from=model, tokenizer_subfolder=None, tokenizer_revision=rev,
                kwargs={}, model_opens_block=False, trained_answer_channel="whole", trained_stop_strings=(),
                tool_slot="none", bos_expected_at_start=0, stop_ids=None, trained_decoding=decoding, cites=cites)


_TULU_BRANCHES = (f"{_TULU}:37 (the step branches of the PPO and GRPO series; the released checkpoints are step_200 "
                  f"and step_1920, equal to main) and :124 (every stored Tülu prompt has the no-BOS Hub render length "
                  f"with the main tokenizer)")
_TULU_SOURCES = (
    _tulu("tulu3/sft", "allenai/Llama-3.1-Tulu-3-8B-SFT", "f2a0b46b0cfda21003c6141b1ff837b7e165524d", ("main",)),
    _tulu("tulu3/dpo", "allenai/Llama-3.1-Tulu-3-8B-DPO", "a7beb67e33ffd01cc87ac3b46cadc1000985b8db", ("main",)),
    _tulu("tulu3/8b_ppo", "allenai/Llama-3.1-Tulu-3-8B", "666943798adbde0b1aff34626007e26986a3c107",
          ("main", "step_*"), decoding={"temperature": 1.0}, extra={"tokenizer_revision": _TULU_BRANCHES}),
    _tulu("tulu31/8b_grpo", "allenai/Llama-3.1-Tulu-3.1-8B", "46239c2d07db76b412e1f1b0b4542f65b81fe01f",
          ("main", "step_*"), decoding={"temperature": 1.0}, extra={"tokenizer_revision": _TULU_BRANCHES}),
    _src(name="llama31/8b_instruct", model_pattern="meta-llama/Llama-3.1-8B-Instruct", revision_patterns=("main",),
         subfolder_pattern=None, template_from="meta-llama/Llama-3.1-8B-Instruct",
         template_file="tokenizer_config.json", template_subfolder=None,
         template_revision="0e9e39f249a16976918f6564b8830bc894c89659", template_sha=LLAMA_TPL,
         tokenizer_from="meta-llama/Llama-3.1-8B-Instruct", tokenizer_subfolder=None,
         tokenizer_revision="0e9e39f249a16976918f6564b8830bc894c89659", kwargs={}, model_opens_block=False,
         trained_answer_channel="whole", trained_stop_strings=(), tool_slot="tools_kwarg", bos_expected_at_start=1,
         stop_ids=None, trained_decoding=None,
         cites={"template": (f"tokenizer_config.json chat_template (e10ca381b1cc, {_DESIGN}:135); {_TULU}:44 (2,024 "
                             f"of 2,024 Instruct rows match the single-BOS render); {_RUNNER_TPL}"),
                "trained_answer_channel": "an instruct model with no reasoning block in its template: the turn is "
                                          "the answer (template text)",
                "reasoning_channel": "the template has no think markers (template text)",
                "bos": (f"the template starts with '{{{{- bos_token }}}}' and llm.chat adds none ({_SYNTH}:60, V9; "
                        f"{_TULU}:25-26)"),
                "trained_stop_strings": "eos_token <|eot_id|> in tokenizer_config.json; no stop string",
                "tool_slot": "the template reads tools and custom_tools (template text)",
                "stop_ids": _VLLM_EOS}),
)

SOURCES: tuple[Source, ...] = (*_CASCADE_SOURCES, *_OLMO_SOURCES, *_QWEN_SOURCES, *_SMOKE_SOURCES, *_TULU_SOURCES)
DESIGN_DISTINCT_GROUPS: tuple[tuple[str, ...], ...] = (
    # design 2.1 and re-review (c): these must get distinct spec ids
    ("cascade/final/think", "cascade/final/no_think"),
    *((f"cascade/{f.rsplit('-', 1)[1].lower()}/think", f"cascade/{f.rsplit('-', 1)[1].lower()}/no_think")
      for f in CASCADE_STAGE_FOLDERS),
    ("olmo3/think", "olmo3/rlzero_code", "olmo3/rlzero_if", "olmo3/rlzero_general", "olmo3/base_think"),
    ("olmo3/rlzero_math", "olmo3/base_math"),
)


# ====================================================================================================== hub files
TOKENIZER_FILES = ("tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "chat_template.jinja")
# A hub cache that holds the registry's tokenizer files only, read instead of the default one when this variable is set.
# 25 Oct 2026 (design step 5): the trainer image sets it, because the volume mounted at its Hugging Face home holds no
# file at the pinned revisions the image can rely on (withholding/train/grpo_modal.py, TOKENIZER_CACHE).
TOKENIZER_CACHE_ENV = "WITHHOLDING_TOKENIZER_CACHE"


def tokenizer_cache() -> Path:
    """The hub cache root the registry reads its tokenizer files from: $WITHHOLDING_TOKENIZER_CACHE, else the default."""
    from huggingface_hub import constants
    return Path(os.environ.get(TOKENIZER_CACHE_ENV) or constants.HF_HUB_CACHE)


def hub_file(repo: str, filename: str, revision: str, subfolder: str | None = None, *, required: bool = True):
    """The cached file `subfolder/filename` of `repo` at the 40-hex `revision`, offline, from `tokenizer_cache()`.
    RegistryError when a required file is not in the cache (fetch it with `python -m withholding.typed.registry
    fetch`); None when an optional file is absent."""
    from huggingface_hub import hf_hub_download
    if not HEX40.fullmatch(revision):
        raise RegistryError(f"{repo}: revision {revision!r} is not a 40-hex commit (design 2.1 invariant 4)")
    try:
        return Path(hf_hub_download(repo, filename, subfolder=subfolder, revision=revision, local_files_only=True,
                                    cache_dir=tokenizer_cache()))
    except Exception as e:  # noqa: BLE001 (LocalEntryNotFoundError and friends: not cached at that commit)
        if not required:
            return None
        raise RegistryError(f"{repo}@{revision[:8]}/{subfolder or ''}{'/' if subfolder else ''}{filename} is not in "
                            f"the local Hugging Face cache ({type(e).__name__}); run `python -m "
                            f"withholding.typed.registry fetch`") from None


def file_sha(path: Path) -> str:
    """sha256 of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def template_text(src: Source) -> str:
    """The template text at the pinned revision, read the way the runner reads it (modal_vllm.py:178-189): the
    declared file, chat_template.jinja's text or tokenizer_config.json's chat_template."""
    p = hub_file(src.template_from, src.template_file, src.template_revision, src.template_subfolder)
    if src.template_file == "chat_template.jinja":
        return p.read_text(encoding="utf-8")
    tpl = json.loads(p.read_text(encoding="utf-8")).get("chat_template")
    if not isinstance(tpl, str):
        raise RegistryError(f"{src.name}: {src.template_from} tokenizer_config.json holds no chat_template string")
    return tpl


@dataclass(frozen=True)
class Tok:
    """A tokenizer as the runner's prompts saw it: the `tokenizers` object of the cached tokenizer.json, the named
    special-token strings transformers passes to every render, and the sha256 of each file read."""

    tk: Any
    special_strings: Mapping[str, str]
    file_shas: Mapping[str, str]

    def encode(self, text: str):
        return self.tk.encode(text, add_special_tokens=False)

    def ids(self, text: str) -> tuple[int, ...]:
        return tuple(self.encode(text).ids)

    def decode(self, ids, skip_special_tokens: bool = True) -> str:
        return self.tk.decode(list(ids), skip_special_tokens=skip_special_tokens)

    def id_of(self, token: str | None) -> int | None:
        return None if token is None else self.tk.token_to_id(token)

    @property
    def special_id_set(self) -> frozenset[int]:
        """Ids of the added tokens marked special (stripped by decode with skip_special_tokens=True)."""
        return frozenset(i for i, t in self.tk.get_added_tokens_decoder().items() if t.special)


@cache
def load_tok(repo: str, revision: str, subfolder: str | None) -> Tok:
    """The tokenizer files of `repo` at `revision` (offline): tokenizer.json through `tokenizers`, the special-token
    strings from tokenizer_config.json, else special_tokens_map.json."""
    from tokenizers import Tokenizer
    tj = hub_file(repo, "tokenizer.json", revision, subfolder)
    tc = hub_file(repo, "tokenizer_config.json", revision, subfolder)
    sm = hub_file(repo, "special_tokens_map.json", revision, subfolder, required=False)
    cfg = json.loads(tc.read_text(encoding="utf-8"))
    smap = json.loads(sm.read_text(encoding="utf-8")) if sm else {}

    def content(v):
        return v.get("content") if isinstance(v, dict) else v
    special = {}
    for k in SPECIAL_TOKEN_ATTRS:
        v = content(cfg.get(k)) if k in cfg else content(smap.get(k))
        if isinstance(v, str):
            special[k] = v
    shas = {"tokenizer.json": file_sha(tj), "tokenizer_config.json": file_sha(tc)}
    if sm:
        shas["special_tokens_map.json"] = file_sha(sm)
    tk = Tokenizer.from_str(tj.read_text(encoding="utf-8"))
    _add_config_tokens(tk, cfg, f"{repo}@{revision[:8]}{'/' + subfolder if subfolder else ''}")
    return Tok(tk=tk, special_strings=special, file_shas=shas)


def _add_config_tokens(tk: Any, cfg: Mapping[str, Any], where: str) -> None:
    """Add the tokens that tokenizer_config.json's `added_tokens_decoder` declares and tokenizer.json lacks, in id
    order and with their declared flags, as transformers' fast tokenizer does when it loads
    (transformers/tokenization_utils_tokenizers.py:468-473 at 5.18.0). The runner's prompts were tokenized that way
    (vLLM loads the tokenizer through transformers), so without this step the raw `tokenizers` object reads such a
    token as BPE pieces: Qwen/Qwen3-8B-Base@49e3418f declares <tool_response>, </tool_response>, <think> and </think>
    (151665 to 151668) only in tokenizer_config.json, and its offline prompt lengths came out one longer than the
    stored `prompt_tokens` on every RLCR prompt. RegistryError when a token does not land on its declared id."""
    from tokenizers import AddedToken
    present = {t.content for t in tk.get_added_tokens_decoder().values()}
    todo = sorted((int(i), v) for i, v in (cfg.get("added_tokens_decoder") or {}).items()
                  if isinstance(v, dict) and v.get("content") not in present)
    for tid, v in todo:
        special = bool(v.get("special", False))
        at = AddedToken(v["content"], single_word=bool(v.get("single_word", False)), lstrip=bool(v.get("lstrip", False)),
                        rstrip=bool(v.get("rstrip", False)), normalized=bool(v.get("normalized", not special)),
                        special=special)
        (tk.add_special_tokens if special else tk.add_tokens)([at])
        if tk.token_to_id(v["content"]) != tid:
            raise RegistryError(f"{where}: added token {v['content']!r} lands on id {tk.token_to_id(v['content'])}, "
                                f"not its declared {tid} (tokenizer_config.json added_tokens_decoder)")


def render(tpl: str, tok: Tok, messages: list[dict], *, add_generation_prompt: bool, kwargs: Mapping[str, Any],
           tools: list[dict] | None = None) -> str:
    """One prompt rendered exactly as transformers' apply_chat_template(tokenize=False) renders it for vLLM's
    llm.chat: its own jinja environment, the named special tokens, then the chat kwargs."""
    from transformers.utils.chat_template_utils import render_jinja_template
    res = render_jinja_template([messages], tools=tools, chat_template=tpl, add_generation_prompt=add_generation_prompt,
                                **{**tok.special_strings, **dict(kwargs)})
    out = res[0] if isinstance(res, tuple) else res
    return out[0] if isinstance(out, list) else out


def _common_affixes(a: str, b: str) -> tuple[int, int]:
    """Lengths of the longest common prefix and of the longest common suffix that does not overlap it."""
    p = 0
    n = min(len(a), len(b))
    while p < n and a[p] == b[p]:
        p += 1
    s = 0
    while s < n - p and a[len(a) - 1 - s] == b[len(b) - 1 - s]:
        s += 1
    return p, s


def _replaced(a: str, b: str) -> str:
    """The text of `a` that `b` replaces: `a` without its longest common prefix and suffix with `b`."""
    p, s = _common_affixes(a, b)
    return a[p:len(a) - s]


def _tokens_from(enc, start: int, end: int) -> list[tuple[int, int, int]]:
    """(id, start, end) of the tokens whose offsets lie in [start, end); RegistryError when one straddles a bound."""
    out = []
    for tid, (s, e) in zip(enc.ids, enc.offsets):
        if (s < start < e) or (s < end < e):
            raise RegistryError(f"a token ({s}, {e}) straddles a probe boundary at {start} or {end}")
        if start <= s and e <= end and e > s:
            out.append((tid, s, e))
    return out


# ====================================================================================================== derivation
@dataclass(frozen=True)
class Derived:
    """What the render probe computes for one Source (design 2.1, DERIVED fields and invariant 6)."""

    template_sha: str
    tokenizer_file_shas: Mapping[str, str]
    generation_prefix_text: str
    generation_prefix_ids: tuple[int, ...]
    bos_at_start: int
    special_ids: Mapping[str, int | None]
    open_ids: tuple[int, ...]
    close_ids: tuple[int, ...]
    role_names: tuple[str, ...]
    turn_start_ids: tuple[int, ...]
    no_tools_marker: str | None
    default_system_line: str | None
    accepted_kwargs: frozenset[str]
    kwargs_named: tuple[str, ...]          # jinja2.meta names beyond the standard render names
    kwargs_flip: Mapping[str, str]         # per named or stored kwarg: "changes", "raises" or "unchanged"

    def as_pin(self) -> dict:
        d = {k: getattr(self, k) for k in self.__dataclass_fields__}
        d["generation_prefix_ids"] = list(self.generation_prefix_ids)
        d["open_ids"], d["close_ids"] = list(self.open_ids), list(self.close_ids)
        d["role_names"], d["turn_start_ids"] = list(self.role_names), list(self.turn_start_ids)
        d["accepted_kwargs"], d["kwargs_named"] = sorted(self.accepted_kwargs), list(self.kwargs_named)
        d["tokenizer_file_shas"], d["special_ids"] = dict(self.tokenizer_file_shas), dict(self.special_ids)
        d["kwargs_flip"] = dict(self.kwargs_flip)
        return d


STORED_ROW_KWARGS = ("enable_thinking",)   # the only chat kwarg any stored row carries (the 15 Oct row-key scan)


def _flip(tpl: str, tok: Tok, name: str) -> str:
    """'changes' when rendering the one-turn probe with name=True or name=False differs from the render without it,
    'raises' when either render raises, else 'unchanged' (design 2.1 invariant 3, the flip half). Only 'changes' makes
    the kwarg accepted: chat kwargs are booleans (TemplateSpec.kwargs), and one whose boolean value breaks the render
    (Llama's date_string, custom_tools, builtin_tools) is read, but not as a boolean a run may pass."""
    probe = [{"role": "user", "content": S_USER1}]
    base = render(tpl, tok, probe, add_generation_prompt=True, kwargs={})
    try:
        on = render(tpl, tok, probe, add_generation_prompt=True, kwargs={name: True})
        off = render(tpl, tok, probe, add_generation_prompt=True, kwargs={name: False})
    except Exception:  # noqa: BLE001 (a template that fails on the flipped value reads the kwarg)
        return "raises"
    return "changes" if (on != base or off != base) else "unchanged"


def _kwargs(tpl: str, tok: Tok) -> tuple[frozenset[str], tuple[str, ...], dict[str, str]]:
    import jinja2
    import jinja2.meta
    env = jinja2.Environment(extensions=["jinja2.ext.loopcontrols"])
    named = tuple(sorted(jinja2.meta.find_undeclared_variables(env.parse(tpl)) - STANDARD_RENDER_NAMES))
    flips = {n: _flip(tpl, tok, n) for n in sorted(set(named) | set(STORED_ROW_KWARGS))}
    accepted = frozenset(n for n in named if flips[n] == "changes")
    return accepted, named, flips


def _role_header_facts(tpl: str, tok: Tok, kwargs) -> tuple[tuple[str, ...], tuple[int, ...], int | None, int | None]:
    """Role names, turn-start ids and the turn start/end special ids from a two-turn probe (design 2.1: role_names,
    turn_start_ids). The probe [system, user, assistant, user] is rendered with the generation prompt, and the text
    between consecutive message contents (and after the last) is a header segment. A role's name is the one line of
    its segment's decoded text (special tokens skipped, as the runner's completions are decoded) that contains the
    role's word; a segment with no such line has no header (a bare template). The turn start is the special token
    that ends exactly where the role name begins in the render (none when the header is plain text, as in Tülu's
    <|user|>); a turn end is the first special token in the segment after a message's content."""
    msgs = [{"role": "system", "content": S_SYS}, {"role": "user", "content": S_USER1},
            {"role": "assistant", "content": S_ASST}, {"role": "user", "content": S_USER2}]
    text = render(tpl, tok, msgs, add_generation_prompt=True, kwargs=kwargs)
    enc = tok.encode(text)
    specials = tok.special_id_set
    bounds, pos = [], 0
    for m in msgs:
        i = text.find(m["content"], pos)
        if i < 0:
            raise RegistryError(f"two-turn probe: the {m['role']} content is not in the render")
        bounds.append((i, i + len(m["content"])))
        pos = i + len(m["content"])
    segments = [(m["role"], (bounds[k - 1][1] if k else 0), bounds[k][0]) for k, m in enumerate(msgs)]
    segments.append(("assistant", bounds[-1][1], len(text)))
    names, starts, ends = set(), set(), set()
    for role, a, b in segments:
        toks = _tokens_from(enc, a, b)
        lines = [ln.strip() for ln in tok.decode([t for t, _, _ in toks]).splitlines() if role in ln]
        if len(lines) > 1:
            raise RegistryError(f"two-turn probe: {len(lines)} header lines name {role!r}: {lines}")
        if lines:
            names.add(lines[0])
            w = text.find(lines[0], a, b)
            adjacent = [t for t, s, e in toks if e == w and t in specials]
            if w >= 0 and adjacent:
                starts.add(adjacent[0])
    for k, (_, end) in enumerate(bounds[:-1]):
        after = [t for t, s, e in _tokens_from(enc, end, bounds[k + 1][0]) if t in specials]
        if after:
            ends.add(after[0])

    def one(xs: set, what: str) -> int | None:
        if len(xs) > 1:
            raise RegistryError(f"two-turn probe: several {what} ids {sorted(xs)}")
        return next(iter(xs), None)
    return tuple(sorted(names)), tuple(sorted(starts)), one(starts, "turn-start"), one(ends, "turn-end")


def _no_tools_marker(src: Source, tpl: str, tok: Tok, kwargs) -> str | None:
    """Text in the no-tools render that a render with a probe tool lacks (design 2.1, derived), after checking that
    the declared tool slot is the one the template reads: a probe tool in the slot changes the render and its name
    appears; with slot none, neither a tools kwarg nor a system functions field changes it."""
    user = {"role": "user", "content": S_USER1}
    system = {"role": "system", "content": S_SYS}
    fn = json.dumps([{"name": PROBE_TOOL_NAME, "description": S_TOOLDESC}])
    tool = {"type": "function", "function": {"name": PROBE_TOOL_NAME, "description": S_TOOLDESC,
                                             "parameters": {"type": "object", "properties": {}}}}
    r_kw0 = render(tpl, tok, [system, user], add_generation_prompt=True, kwargs=kwargs)
    r_kw1 = render(tpl, tok, [system, user], add_generation_prompt=True, kwargs=kwargs, tools=[tool])
    r_fn1 = render(tpl, tok, [{**system, "functions": fn}, user], add_generation_prompt=True, kwargs=kwargs)
    reads = {"tools_kwarg": r_kw1 != r_kw0, "system_functions_field": r_fn1 != r_kw0}
    if src.tool_slot == "none":
        if any(reads.values()):
            raise RegistryError(f"{src.name}: tool_slot none, but the template reads {[k for k, v in reads.items() if v]}")
        return None
    if not reads[src.tool_slot]:
        raise RegistryError(f"{src.name}: tool_slot {src.tool_slot}, but a probe tool there leaves the render unchanged")
    with_tool = r_kw1 if src.tool_slot == "tools_kwarg" else r_fn1
    if PROBE_TOOL_NAME not in with_tool:
        raise RegistryError(f"{src.name}: the probe tool's name is not in the {src.tool_slot} render")
    marker, inserted = _replaced(r_kw0, with_tool), _replaced(with_tool, r_kw0)
    if not marker.strip() or marker in inserted:   # the tool render only adds text: the no-tools render lacks nothing
        return None
    if marker in with_tool:
        raise RegistryError(f"{src.name}: the no-tools text {marker!r} also occurs in the render with a tool")
    return marker


def derive(src: Source) -> Derived:
    """Run the render probe for one Source on the cached files at its pinned revisions (design 2.1 invariant 6)."""
    tpl = template_text(src)
    tsha = sha256_hex(tpl)
    if tsha != src.template_sha:
        raise RegistryError(f"{src.name}: template at {src.template_revision[:8]} hashes to {tsha[:12]}, pinned "
                            f"{src.template_sha[:12]} (design 2.1 invariant 6)")
    tok = load_tok(src.tokenizer_from, src.tokenizer_revision, src.tokenizer_subfolder)
    accepted, named, flips = _kwargs(tpl, tok)
    probe = [{"role": "user", "content": S_USER1}]
    text = render(tpl, tok, probe, add_generation_prompt=True, kwargs=src.kwargs)
    cut = text.rfind(S_USER1) + len(S_USER1)
    if cut < len(S_USER1):
        raise RegistryError(f"{src.name}: the probe content is not in the render")
    enc = tok.encode(text)
    tail = tuple(t for t, _, _ in _tokens_from(enc, cut, len(text)))
    bos_id = tok.id_of(tok.special_strings.get("bos_token"))
    bos_at_start = 0
    while bos_id is not None and bos_at_start < len(enc.ids) and enc.ids[bos_at_start] == bos_id:
        bos_at_start += 1
    roles, turn_starts, ts, te = _role_header_facts(tpl, tok, src.kwargs)
    d0 = render(tpl, tok, probe, add_generation_prompt=True, kwargs=src.kwargs)
    d1 = render(tpl, tok, [{"role": "system", "content": S_SYS}, *probe], add_generation_prompt=True, kwargs=src.kwargs)
    default_line = _replaced(d0, d1).strip() or None
    special = {k[:-6]: tok.id_of(tok.special_strings.get(k)) for k in ("bos_token", "eos_token", "pad_token",
                                                                         "unk_token")}
    special.update(turn_start=ts, turn_end=te)
    return Derived(template_sha=tsha, tokenizer_file_shas=dict(tok.file_shas), generation_prefix_text=text[cut:],
                   generation_prefix_ids=tail, bos_at_start=bos_at_start, special_ids=special,
                   open_ids=tok.ids(OPEN), close_ids=tok.ids(CLOSE), role_names=roles, turn_start_ids=turn_starts,
                   no_tools_marker=_no_tools_marker(src, tpl, tok, src.kwargs), default_system_line=default_line,
                   accepted_kwargs=accepted, kwargs_named=named, kwargs_flip=flips)


# ====================================================================================================== specs and pins
def _ends_with(seq: tuple[int, ...], tail: tuple[int, ...]) -> bool:
    return bool(tail) and len(seq) >= len(tail) and tuple(seq[-len(tail):]) == tuple(tail)


def _find(seq: tuple[int, ...], sub: tuple[int, ...], start: int = 0) -> int:
    for i in range(start, len(seq) - len(sub) + 1):
        if tuple(seq[i:i + len(sub)]) == tuple(sub):
            return i
    return -1


def reasoning_channel_of(src: Source, d: Derived) -> str:
    """template_opens when the prefix ids end with the open ids; template_closed when the prefix ends, in text and in
    ids, with a close after an open (Qwen3 thinking off); else the declared model_opens or none (design 2.1)."""
    if _ends_with(d.generation_prefix_ids, d.open_ids):
        return "template_opens"
    t = d.generation_prefix_text.rstrip()
    i = _find(d.generation_prefix_ids, d.open_ids)
    if (t.endswith(CLOSE) and OPEN in t[:len(t) - len(CLOSE)] and i >= 0
            and _find(d.generation_prefix_ids, d.close_ids, i + len(d.open_ids)) >= 0):
        return "template_closed"
    return "model_opens" if src.model_opens_block else "none"


RULE_D_CHANNEL = models.RULE_D_CHANNEL   # design 2.1 invariant 2 (the channel is rule D's, never declared)


def build_spec(src: Source, d: Derived) -> TemplateSpec:
    """The TemplateSpec of one Source from its derived probe values; models.TemplateSpec's validator enforces
    invariants 1 to 5. The BOS count of the render must equal the cited policy (invariant 6)."""
    if d.bos_at_start != src.bos_expected_at_start:
        raise RegistryError(f"{src.name}: the render starts with {d.bos_at_start} BOS ids, the cited policy says "
                            f"{src.bos_expected_at_start} (design 2.1 invariant 6; section 4 item 4)")
    if src.legacy_template_key is not None:
        from withholding.typed import legacy
        if d.template_sha[:12] != src.legacy_template_key:
            raise RegistryError(f"{src.name}: template {d.template_sha[:12]} is not the 14 Oct key "
                                f"{src.legacy_template_key}")
        if legacy.TEMPLATES[src.legacy_template_key]["think_forced"] != _ends_with(d.generation_prefix_ids, d.open_ids):
            raise RegistryError(f"{src.name}: the derived forced-open flag disagrees with the frozen 14 Oct TEMPLATES")
    channel = reasoning_channel_of(src, d)
    cites = dict(src.cites)
    sub = f"{src.template_subfolder}/" if src.template_subfolder else ""
    cites["template"] = (f"hf:{src.template_from}@{src.template_revision}/{sub}{src.template_file} "
                         f"(sha256 {src.template_sha}); " + cites.get("template", ""))
    stop_ids = src.stop_ids if src.stop_ids is not None else (d.special_ids["eos"],)
    return TemplateSpec(
        model_pattern=src.model_pattern, subfolder_pattern=src.subfolder_pattern, template_from=src.template_from,
        template_revision=src.template_revision, template_sha=d.template_sha, tokenizer_from=src.tokenizer_from,
        tokenizer_subfolder=src.tokenizer_subfolder, tokenizer_revision=src.tokenizer_revision,
        accepted_kwargs=frozenset(d.accepted_kwargs), kwargs=dict(src.kwargs),
        generation_prefix_text=d.generation_prefix_text, generation_prefix_ids=tuple(d.generation_prefix_ids),
        think_open_in_prompt=_ends_with(d.generation_prefix_ids, d.open_ids), reasoning_channel=channel,
        answer_channel=RULE_D_CHANNEL[channel], trained_answer_channel=src.trained_answer_channel,
        open_marker=OPEN, close_marker=CLOSE, open_ids=tuple(d.open_ids), close_ids=tuple(d.close_ids),
        special_ids=dict(d.special_ids), stop_ids=tuple(stop_ids), trained_stop_strings=tuple(src.trained_stop_strings),
        role_names=tuple(d.role_names), turn_start_ids=tuple(d.turn_start_ids),
        bos=BosPolicy(bos_id=d.special_ids["bos"], expected_at_start=src.bos_expected_at_start),
        tool_slot=src.tool_slot, no_tools_marker=d.no_tools_marker, default_system_line=d.default_system_line,
        trained_decoding=None if src.trained_decoding is None else {k: float(v) for k, v in src.trained_decoding.items()},
        citations={k: Citation(source=v, retrieved=RETRIEVED) for k, v in cites.items()})


def read_pins(path: Path = PINS_PATH) -> dict:
    """The pinned probe values: {name: {derived fields..., spec_id}}; RegistryError when the file is missing."""
    if not path.exists():
        raise RegistryError(f"{path} is missing: run `python -m withholding.typed.registry pin` once")
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["entries"]


def write_pins(path: Path = PINS_PATH) -> dict:
    """Derive every Source, build its spec, and write the pins (the values the render probe must reproduce)."""
    entries = {}
    for src in SOURCES:
        d = derive(src)
        entries[src.name] = {**d.as_pin(), "spec_id": build_spec(src, d).spec_id}
    body = {"version": 1, "pinned_on": RETRIEVED.isoformat(),
            "note": "derived by withholding/typed/registry.py from the cached tokenizer files at each entry's pinned "
                    "revisions; load_registry() derives them again and refuses any value that differs",
            "entries": entries}
    path.write_text(json.dumps(body, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return entries


def check_against_pin(src: Source, d: Derived, pin: Mapping[str, Any]) -> None:
    """Invariant 6: every derived value equals its pin."""
    have = d.as_pin()
    bad = sorted(k for k in have if json.dumps(have[k], sort_keys=True) != json.dumps(pin.get(k), sort_keys=True))
    if bad:
        raise RegistryError(f"{src.name}: the render probe does not reproduce {bad} (design 2.1 invariant 6)")


# ====================================================================================================== delivery probe
RULE_KEYS = {"2a": ingest.RULE_D_2A, "2b": ingest.RULE_D_2B, "2c": ingest.RULE_D_2C, "post": ingest.RULE_D_POST_2D}


@dataclass(frozen=True)
class Case:
    """One synthetic completion of the delivery probe, built from an entry's markers ({O}, {C}) and a role line ({R})
    of its own role names, with the state it must be labelled and its outcome under each registered rule D id
    (design 2.3's outcome table, written here from the owner's decisions, never read from the registry). An outcome
    is (mode, text) or an undelivered reason; `rlcr` holds the outcomes that differ for an RLCR row (rlcr.close)."""

    name: str
    kind: Literal["template_opened", "not_template_opened"]
    raw: str
    finish: str
    state: str
    expect: Mapping[str, Any]
    rlcr: Mapping[str, Any] = field(default_factory=dict)
    needs_role: bool = False


def _all(v):
    return {k: v for k in RULE_KEYS}


def _ac(t):
    return ("after_close", t)


def _wt(t):
    return ("whole_turn", t)


_MULTI = {"2a": _ac("ANS"), "2b": _ac("MID{C}ANS"), "2c": _ac("MID{C}ANS"), "post": _ac("MID{C}ANS")}
_MULTI_RLCR = {"2b": _ac("ANS"), "2c": _ac("ANS"), "post": _ac("ANS")}
_D15 = {"2a": _ac("POST"), "2b": _ac("PREPOST"), "2c": _ac("PREPOST"), "post": _ac("PREPOST")}
_D15_RLCR = {"2b": _ac("POST"), "2c": _ac("POST"), "post": _ac("POST")}
_D15_EMPTY = {"2a": "empty_after_close", "2b": "empty_outside_blocks", "2c": "empty_outside_blocks",
              "post": "empty_outside_blocks"}
_D15_EMPTY_RLCR = {"2b": "empty_after_close", "2c": "empty_after_close", "post": "empty_after_close"}
_T, _M = "template_opened", "not_template_opened"
CASES: tuple[Case, ...] = (
    # the template opened the block (template_opens): the completion starts inside it
    Case("empty", _T, " \n\t", "stop", "empty", _all("empty_output")),
    Case("forced_open_unclosed_stop", _T, "r1 reasoning", "stop", "forced_open_unclosed", _all("unclosed_block")),
    Case("forced_open_unclosed_cap", _T, "r1 reasoning", "length", "forced_open_unclosed", _all("unclosed_block")),
    Case("closed", _T, "r1{C}\n\nANS", "stop", "closed", _all(_ac("\n\nANS"))),
    Case("closed_blank_after", _T, "r1{C} \n", "stop", "closed", _all("empty_after_close")),
    Case("closed_inner_open", _T, "r1{C}PRE{O}r2", "length", "closed", _all(_ac("PRE"))),
    Case("closed_inner_open_nothing_before", _T, "r1{C}\n{O}r2", "stop", "closed", _all("empty_before_inner_open")),
    Case("multiple_close", _T, "r1{C}MID{C}ANS", "stop", "multiple_close", _MULTI, _MULTI_RLCR),
    Case("closed_block_in_region", _T, "r1{C}PRE{O}r2{C}POST", "stop", "multiple_close", _D15, _D15_RLCR),
    Case("closed_block_nothing_outside", _T, "r1{C} {O}r2{C}\n", "stop", "multiple_close", _D15_EMPTY, _D15_EMPTY_RLCR),
    Case("invented_turn_after_close", _T, "r1{C}ANS\n{R}\nINVENTED", "stop", "invented_turns",
         {"2a": _ac("ANS\n{R}\nINVENTED"), "2b": _ac("ANS\n{R}\nINVENTED"), "2c": _ac("ANS\n{R}\nINVENTED"),
          "post": _ac("ANS\n")}, needs_role=True),
    Case("invented_turn_before_close", _T, "r1\n{R}\nr2{C}ANS", "stop", "invented_turns",
         {"2a": _ac("ANS"), "2b": _ac("ANS"), "2c": _ac("ANS"), "post": "unclosed_block"}, needs_role=True),
    Case("leading_role_header", _T, " {R}\nr1{C}ANS", "stop", "closed", _all(_ac("ANS")), needs_role=True),
    # the prefix did not open the block (model_opens, template_closed, none): the model may open one itself
    Case("empty", _M, "\n \n", "stop", "empty", _all("empty_output")),
    Case("unclosed_stop", _M, "{O}r1", "stop", "unclosed_stop", _all("unclosed_block")),
    Case("unclosed_cap", _M, "{O}r1", "length", "unclosed_cap", _all("unclosed_block")),
    Case("closed", _M, "{O}r1{C}ANS", "stop", "closed", _all(_ac("ANS"))),
    Case("closed_after_whitespace", _M, "\n\n{O}r1{C}ANS", "stop", "closed", _all(_ac("ANS"))),
    Case("closed_blank_after", _M, "{O}r1{C}  ", "stop", "closed", _all("empty_after_close")),
    Case("closed_inner_open", _M, "{O}r1{C}PRE{O}r2", "length", "closed", _all(_ac("PRE"))),
    Case("closed_inner_open_nothing_before", _M, "{O}r1{C}\n{O}r2", "stop", "closed", _all("empty_before_inner_open")),
    Case("multiple_close", _M, "{O}r1{C}MID{C}ANS", "stop", "multiple_close", _MULTI, _MULTI_RLCR),
    Case("closed_block_in_region", _M, "{O}r1{C}PRE{O}r2{C}POST", "stop", "multiple_close", _D15, _D15_RLCR),
    Case("closed_block_nothing_outside", _M, "{O}r1{C} {O}r2{C}\n", "stop", "multiple_close", _D15_EMPTY,
         _D15_EMPTY_RLCR),
    Case("stray_close", _M, "PRE{C}POST", "stop", "stray_close",
         {"2a": _ac("POST"), "2b": _ac("POST"), "2c": _wt("PRE{C}POST"), "post": _wt("PRE{C}POST")}),
    Case("stray_close_after_closed_block", _M, "PRE{O}r{C}POST", "stop", "stray_close",   # the e370ba13 shape (D15)
         {"2a": _ac("POST"), "2b": _ac("POST"), "2c": _wt("PREPOST"), "post": _wt("PREPOST")}),
    Case("stray_close_inner_open", _M, "PRE{C}MID{O}r", "length", "stray_close",
         {"2a": _ac("MID"), "2b": _ac("MID"), "2c": _wt("PRE{C}MID"), "post": _wt("PRE{C}MID")}),
    Case("no_tags", _M, "ANS", "stop", "no_tags", _all(_wt("ANS"))),
    Case("no_tags_inner_open", _M, "PRE{O}r", "length", "no_tags", _all(_wt("PRE"))),
    Case("invented_turn_no_tags", _M, "ANS\n{R}\nINVENTED", "stop", "invented_turns",
         {"2a": _wt("ANS\n{R}\nINVENTED"), "2b": _wt("ANS\n{R}\nINVENTED"), "2c": _wt("ANS\n{R}\nINVENTED"),
          "post": _wt("ANS\n")}, needs_role=True),
    Case("invented_turn_after_close", _M, "{O}r1{C}ANS\n{R}\nINVENTED", "stop", "invented_turns",
         {"2a": _ac("ANS\n{R}\nINVENTED"), "2b": _ac("ANS\n{R}\nINVENTED"), "2c": _ac("ANS\n{R}\nINVENTED"),
          "post": _ac("ANS\n")}, needs_role=True),
    Case("leading_role_header", _M, "{R}\nANS", "stop", "no_tags", _all(_wt("{R}\nANS")), needs_role=True),
)


def _fill(t: str, role: str) -> str:
    return t.replace("{O}", OPEN).replace("{C}", CLOSE).replace("{R}", role)


def _expected(v, role: str):
    """An outcome of the table with the role line filled in: an undelivered reason, or (mode, text)."""
    if isinstance(v, str):
        if v not in models.UNDELIVERED_REASONS:
            raise RegistryError(f"outcome table: {v!r} is not an undelivered reason")
        return v
    return v[0], _fill(v[1], role)


def probe_role(spec: TemplateSpec) -> str | None:
    """The role line the probe writes: the role name naming the user, else the first role name, else None."""
    users = [n for n in spec.role_names if "user" in n]
    return (users or list(spec.role_names) or [None])[0]


def delivery_cases(spec: TemplateSpec) -> list[tuple[Case, str]]:
    """The cases this spec's channel allows, with the role line filled in (design 2.1 invariant 7)."""
    kind = _T if spec.reasoning_channel == "template_opens" else _M
    role = probe_role(spec)
    return [(c, role or "") for c in CASES if c.kind == kind and (role is not None or not c.needs_role)]


def run_case(spec: TemplateSpec, case: Case, role: str, rule_key: str, family: str):
    """(facts, state, outcome) of one case under one rule key, through ingest's content core."""
    m = ingest.markers_of(spec)
    raw = _fill(case.raw, role)
    facts = ingest.compute_facts(raw, m, chat_kwargs={}, accepted_kwargs=spec.accepted_kwargs)
    state = ingest.derive_state(facts, case.finish)
    o = ingest.deliver_spans(raw, facts, m, RULE_KEYS[rule_key], family, case.finish)
    return raw, facts, state, o


def delivery_probe(name: str, spec: TemplateSpec) -> list[str]:
    """Invariant 7: every case's state and its outcome under every registered rule D id, for an RLCR row and for a
    row of any other family, equal the outcome table. Returns the list of mismatches (empty when the probe passes)."""
    bad = []
    for case, role in delivery_cases(spec):
        for fam in ("reliablemath", "rlcr"):
            for key in RULE_KEYS:
                raw, _facts, state, o = run_case(spec, case, role, key, fam)
                want = _expected((case.rlcr if fam == "rlcr" else {}).get(key, case.expect[key]), role)
                got = o.undelivered_reason if not o.delivered else (o.mode, ingest.join_spans(raw, o.spans))
                if state != case.state:
                    bad.append(f"{name}: {case.name}: state {state}, the table says {case.state}")
                if got != want:
                    bad.append(f"{name}: {case.name} [{fam}, {key}]: {got!r}, the table says {want!r}")
    return sorted(set(bad))


def sensitivity_modes(spec: TemplateSpec) -> dict[str, set[tuple[str, bool]]]:
    """Design 2.3: each SensitivityRule's modes, the set of (mode, includes_reasoning) it issues across the probe
    cases, per base (step 2a's id and the post-2d id). S_whole_turn reads the turn (cut under its base's D4);
    S_reasoning_incl the raw completion; S_rule_F reads an unclosed row that finished on stop as the turn, every other
    row as rule D (which never includes reasoning). A reading includes reasoning when the text read overlaps the
    turn's own block or an inner block or unclosed block (content facts of ThinkFacts)."""
    out: dict[str, set] = {}
    for case, role in delivery_cases(spec):
        for key in ("2a", "post"):
            raw, f, _state, o = run_case(spec, case, role, key, "reliablemath")
            if f["empty"]:
                continue
            base = RULE_KEYS[key]
            turn_end = f["turn_boundary_at"] if (base.turn == "cut_at_boundary" and f["turn_boundary_at"]) else len(raw)
            reasoning = [s for s in o.reasoning_spans if s[0] < turn_end]
            if f["inner_open_at"] is not None and f["inner_open_at"] < turn_end:
                reasoning.append((f["inner_open_at"], turn_end))
            in_turn = bool(reasoning) or (f["opened_by"] is not None)
            in_raw = in_turn or bool(o.reasoning_spans) or f["inner_open_at"] is not None
            out.setdefault(f"S_whole_turn@{base.rule_id}", set()).add(("whole_turn", in_turn))
            out.setdefault(f"S_reasoning_incl@{base.rule_id}", set()).add(("raw", in_raw))
            if f["unclosed"] and case.finish == "stop":
                out.setdefault(f"S_rule_F@{base.rule_id}", set()).add(("whole_turn", True))
            elif o.delivered:
                out.setdefault(f"S_rule_F@{base.rule_id}", set()).add((o.mode, False))
    return out


# ====================================================================================================== owner decisions
INDEX_ROW = re.compile(r"^\| (OD-\d+|D\d+) \|", re.MULTILINE)


@dataclass(frozen=True)
class OwnerDecisions:
    """The OwnerDecision registry (design 2.8) over `models.load_decisions`, which parses every record, its grants
    (each line checked against the step 0 metric ids and coordinate scheme) and the Confirmation section. This layer
    adds the record index check, re-reads each source by heading and content sha, and owns the pin file: the first
    load with pin_on_first_load after the owner's line pins every record's sha, the Confirmation section's sha and the
    owner's lines; a record edited, added or removed later fails the load until a new dated line is added and `check`
    re-pins (models.DecisionsNote.check_pin). While the note is unsigned, `status` is "unsigned", the records and
    grants can be read, and `pin()` and `require_confirmed()` refuse."""

    note: models.DecisionsNote
    status: Literal["unsigned", "confirmed", "confirmed_unpinned"]
    problems: tuple[str, ...]

    @property
    def records(self) -> tuple[models.OwnerDecisionRef, ...]:
        return self.note.records

    @property
    def grants(self) -> tuple[models.Grant, ...]:
        return self.note.grants

    @property
    def rule_ids(self) -> frozenset[str]:
        """Every read rule a grant registers (`rule:` lines): rule D ids and sensitivity ids."""
        return self.note.rule_ids

    def record(self, rid: str) -> models.OwnerDecisionRef:
        return self.note.record(rid)

    def require_confirmed(self) -> None:
        """RegistryError unless the owner's line is present and every record is pinned (design 2.8, D11)."""
        if self.status != "confirmed":
            raise RegistryError(f"OwnerDecision registry is {self.status}: " + "; ".join(self.problems))

    def pin(self, path: Path = OWNER_PINS_PATH) -> Path:
        """Write the pin (record shas, Confirmation sha, the owner's lines, date of the newest line), naming the note by
        its repo-relative path. Refused while the note is unsigned (models.DecisionsNote.pin raises RegistryError
        naming the Confirmation heading)."""
        pin = self.note.pin()
        note = Path(pin.path)
        if note.is_absolute() and ROOT in note.parents:
            pin = pin.model_copy(update={"path": note.relative_to(ROOT).as_posix()})
        path.write_text(pin.model_dump_json(indent=1) + "\n", encoding="utf-8")
        return path


def load_owner_decisions(path: Path = DECISIONS_NOTE, pins_path: Path = OWNER_PINS_PATH, *,
                         pin_on_first_load: bool = False) -> OwnerDecisions:
    """Read the decisions note through `models.load_decisions`, check its Index against its record headings and
    every source by heading and content sha, then check it against the pin (design 2.8, Revision 6). The pin is
    written only with pin_on_first_load (`check`): when none exists, or when a new dated line allows a re-pin;
    otherwise such a note loads "confirmed_unpinned"."""
    text = path.read_text(encoding="utf-8")
    note = models.load_decisions(path, text=text)
    index = [b for h, _, b in models.split_sections(text) if h == "## Index"]
    ids = sorted(r.id for r in note.records)
    if len(index) != 1 or sorted(INDEX_ROW.findall(index[0])) != ids:
        raise RegistryError(f"{path.name}: the Index rows and the record headings differ")
    for r in note.records:
        r.source.verify(text)
    if note.status == "unsigned":
        why = (f"unsigned: {path.name} carries no line beginning 'Confirmed: Ahmed Bakr, ' and a YYYY-MM-DD date in "
               f"its {models.CONFIRMATION_HEADING} section (D11)")
        return OwnerDecisions(note=note, status="unsigned", problems=(why,))
    status = "confirmed_unpinned"
    if pins_path.exists():
        try:
            old = models.RegistryPin.model_validate_json(pins_path.read_text(encoding="utf-8"), strict=False)
        except ValueError as e:   # pydantic ValidationError: a pin without a field Revision 6 added, or a malformed one
            raise RegistryError(f"{pins_path.name} does not parse as a RegistryPin: {e}") from None
        note.check_pin(old)   # RegistryError: a pinned owner's line edited, or anything moved with no new line
        if old == note.pin().model_copy(update={"path": old.path}):
            status = "confirmed"
        elif pin_on_first_load:
            OwnerDecisions(note=note, status=status, problems=()).pin(pins_path)
            status = "confirmed"
    elif pin_on_first_load:
        OwnerDecisions(note=note, status=status, problems=()).pin(pins_path)
        status = "confirmed"
    return OwnerDecisions(note=note, status=status, problems=() if status == "confirmed" else
                          ("confirmed, not pinned",))


# ====================================================================================================== the registry
@dataclass(frozen=True)
class Entry:
    """One loaded registry entry: its declared Source, its derived probe values and its TemplateSpec."""

    source: Source
    derived: Derived
    spec: TemplateSpec

    @property
    def name(self) -> str:
        return self.source.name


@dataclass(frozen=True)
class Resolution:
    """The registry entry of one stored output row, and what the row's kwargs mean under its template."""

    entry: Entry
    kwargs_read: Mapping[str, bool]
    ignored_kwargs: tuple[str, ...]    # stored chat kwargs the template does not read (audit 28)
    kwargs_recorded: bool              # False: the row carries no chat kwargs (the local MLX smoke)
    tokenizer_revision: Literal["not_recorded"] = "not_recorded"   # no stored row records a tokenizer commit (R12)

    @property
    def spec(self) -> TemplateSpec:
        return self.entry.spec


def _match(pattern: str | None, value) -> bool:
    if pattern is None:
        return value in (None, "")
    return isinstance(value, str) and fnmatch.fnmatchcase(value, pattern)


@dataclass(frozen=True)
class Registry:
    """The loaded registry (design 2.1, 2.8, section 3 "registry load")."""

    entries: tuple[Entry, ...]
    owner_decisions: OwnerDecisions
    probe: Mapping[str, Any]

    @property
    def specs(self) -> dict[str, TemplateSpec]:
        return {e.name: e.spec for e in self.entries}

    @property
    def rule_ids(self) -> tuple[str, ...]:
        """The registered rule D ids of design 2.3, in step order (step 2a's first). The grants hold the same four
        (checked at load); step 0 reads the design's set, never a signed registry (standing rule)."""
        return ingest.REGISTERED_RULE_IDS

    def entry(self, name: str) -> Entry:
        return next(e for e in self.entries if e.name == name)

    def spec_by_id(self, spec_id: str) -> TemplateSpec:
        """A spec by its id. Entries sharing an id share every identity field, so any of them reads the same."""
        for e in self.entries:
            if e.spec.spec_id == spec_id:
                return e.spec
        raise KeyError(spec_id)

    def resolve(self, row: Mapping[str, Any]) -> Resolution:
        """The one entry whose row key matches a stored output row (design section 3, "ingest, stored rows"): model,
        revision, subfolder and template source by pattern, then the chat kwargs the template reads equal to the
        entry's. ingest.IngestError when no entry or several match."""
        model, sub = row.get("model"), row.get("subfolder")
        tfrom = row.get("chat_template_from") or model
        samp = row.get("sampling")
        recorded = isinstance(samp, dict) and isinstance(samp.get("chat_template_kwargs"), dict)
        stored = dict(samp["chat_template_kwargs"]) if recorded else {}
        hits = []
        for e in self.entries:
            s = e.source
            if not (_match(s.model_pattern, model) and _match(s.subfolder_pattern, sub) and tfrom == s.template_from
                    and any(_match(p, row.get("revision")) for p in s.revision_patterns)):
                continue
            eff = stored
            if not recorded and s.kwargs_from_thinking and isinstance(row.get("thinking"), bool):
                eff = {"enable_thinking": row["thinking"]}
            read = {k: v for k, v in eff.items() if k in e.spec.accepted_kwargs}
            if read == dict(s.kwargs):
                hits.append(Resolution(entry=e, kwargs_read=read,
                                       ignored_kwargs=tuple(sorted(set(eff) - set(e.spec.accepted_kwargs))),
                                       kwargs_recorded=recorded))
        if len(hits) != 1:
            key = (model, row.get("revision"), sub, tfrom, stored)
            raise ingest.IngestError(f"row key {key} matches {len(hits)} registry entries "
                                     f"({[h.entry.name for h in hits]})", row_id=row.get("id"))
        return hits[0]

    def spec_for_row(self, row: Mapping[str, Any]) -> TemplateSpec:
        """The TemplateSpec of a stored output row (resolve(row).spec)."""
        return self.resolve(row).spec

    def entry_for_spec(self, spec: TemplateSpec) -> Entry:
        """An entry with this spec's id (entries sharing an id render and read identically)."""
        for e in self.entries:
            if e.spec.spec_id == spec.spec_id:
                return e
        raise KeyError(spec.spec_id)

    def prompt_tokenizer(self, spec: TemplateSpec, prompt: Any, chat_kwargs: Mapping[str, Any] | None = None):
        """(prompt ids, template text) of a PromptRecord rendered offline under `spec` (design section 3, "ingest,
        stored rows"; section 4 item 1): the stored messages as the runner passed them, the spec's kwargs (a stored
        kwarg the template does not read changes nothing: its flip is "unchanged"), add_special_tokens=False. A
        prompt whose tools are declared for a template slot is refused: no stored row carries one (every stored
        tool block is system text, `tool_render = system_text_legacy`), and rendering a slot is the runner's step."""
        if getattr(prompt, "tool_render", None) == "slot" and getattr(prompt.tools, "state", None) == "declared":
            raise ingest.IngestError("a prompt with declared tools in a template slot is not rendered offline at "
                                     "step 0", row_id=getattr(prompt, "id", None))
        e = self.entry_for_spec(spec)
        msgs = [{"role": m.role, "content": m.content} for m in prompt.messages]
        _, ids = self.render_prompt(e.name, msgs)
        return ids, _template_cached(e.name)

    def render_prompt(self, name: str, messages: list[dict], tools: list[dict] | None = None) -> tuple[str, tuple]:
        """(text, ids) of one prompt rendered and tokenized offline as the runner did (add_special_tokens=False)."""
        s = self.entry(name).source
        tok = load_tok(s.tokenizer_from, s.tokenizer_revision, s.tokenizer_subfolder)
        text = render(_template_cached(s.name), tok, messages, add_generation_prompt=True, kwargs=s.kwargs,
                      tools=tools)
        return text, tok.ids(text)


@cache
def _template_cached(name: str) -> str:
    return template_text(next(s for s in SOURCES if s.name == name))


def check_distinct(entries: tuple[Entry, ...]) -> list[str]:
    """Spec ids are distinct wherever the design says they must be (DESIGN_DISTINCT_GROUPS), and two entries share
    an id only when every identity field is equal (no collision). Returns the problems found."""
    by = {e.name: e.spec for e in entries}
    bad = []
    for group in DESIGN_DISTINCT_GROUPS:
        ids = [by[n].spec_id for n in group]
        if len(set(ids)) != len(ids):
            bad.append(f"spec ids not distinct in {group}: {ids}")
    ident = {}
    for e in entries:
        key = canonical_json({k: v for k, v in e.spec.model_dump(mode="json").items()
                              if k in ("template_sha", "generation_prefix_text", "generation_prefix_ids",
                                       "think_open_in_prompt", "answer_channel", "trained_answer_channel",
                                       "tokenizer_from", "tokenizer_subfolder", "tokenizer_revision", "special_ids",
                                       "open_ids", "close_ids", "kwargs", "bos")})
        prev = ident.setdefault(e.spec.spec_id, key)
        if prev != key:
            bad.append(f"spec id {e.spec.spec_id} is shared by entries with different identity fields")
    return bad


def shared_spec_ids(entries: tuple[Entry, ...]) -> dict[str, list[str]]:
    """Spec ids that several entries share (they read identically by construction), with the entry names."""
    groups: dict[str, list[str]] = {}
    for e in entries:
        groups.setdefault(e.spec.spec_id, []).append(e.name)
    return {k: v for k, v in groups.items() if len(v) > 1}


@cache
def load_registry(pins_path: str | None = None, *, pin_owner_decisions: bool = False) -> Registry:
    """Load and check the registry (design 2.1 invariants 1 to 8, section 3 "registry load"): each Source's render
    probe must reproduce its pins and its spec_id; its spec must validate; the delivery probe must reproduce the
    outcome table; the spec ids must be distinct where the design requires it; the grants' rule D ids must be the
    design's four. The OwnerDecision registry loads beside it and reports its own status; nothing here needs it
    signed, and its pin is written only with pin_owner_decisions (`check`), never by the import-time load. Any failure
    is a RegistryError."""
    pins = read_pins(Path(pins_path) if pins_path else PINS_PATH)
    if sorted(pins) != sorted(s.name for s in SOURCES):
        raise RegistryError(f"pins and sources differ: {sorted(set(pins) ^ {s.name for s in SOURCES})}")
    entries, failures = [], []
    for src in SOURCES:
        d = derive(src)
        check_against_pin(src, d, pins[src.name])
        try:
            spec = build_spec(src, d)
        except ValueError as e:   # pydantic ValidationError: invariants 1 to 5
            raise RegistryError(f"{src.name}: TemplateSpec refused: {e}") from None
        spec.check_pinned(pins[src.name]["spec_id"])
        failures += delivery_probe(src.name, spec)
        entries.append(Entry(source=src, derived=d, spec=spec))
    if failures:
        raise RegistryError("delivery probe (design 2.1 invariant 7): " + "; ".join(failures[:20]))
    entries = tuple(entries)
    distinct = check_distinct(entries)
    if distinct:
        raise RegistryError("; ".join(distinct))
    od = load_owner_decisions(pin_on_first_load=pin_owner_decisions)
    grant_rule_d = sorted(r for r in od.rule_ids if models.rule_kind(r) == "rule_d")
    if grant_rule_d != sorted(ingest.REGISTERED_RULE_IDS):
        raise RegistryError(f"the grants' rule D ids {grant_rule_d} are not the design's {ingest.REGISTERED_RULE_IDS}")
    modes = {}
    for e in entries:
        for rid, ms in sensitivity_modes(e.spec).items():
            modes.setdefault(rid, {})[e.name] = sorted(ms)
    probe = {"cases": {e.name: len(delivery_cases(e.spec)) for e in entries},
             "rule_ids": list(ingest.REGISTERED_RULE_IDS), "shared_spec_ids": shared_spec_ids(entries),
             "sensitivity_modes": modes, "sensitivity_grants": sensitivity_grants(entries, od, modes)}
    return Registry(entries=entries, owner_decisions=od, probe=probe)


def sensitivity_grants(entries: tuple[Entry, ...], od: OwnerDecisions, modes: Mapping) -> dict[str, dict]:
    """Design 2.3 and D1: a sensitivity rule that reads with reasoning on some rows and without on others needs a
    grant holding `mixed_modes:<id>`. Per registered sensitivity id: whether its grant holds that line, the entries
    on which the probe found it two-way, and whether it is one-way on every template-opened entry (S_whole_turn's
    cells are the four section 7 lineages, all template-opened). `consistent` is False only for a rule without
    mixed_modes that is two-way on a template-opened entry; it is reported here, not raised (the refusal is the
    ReportCell's mixed_modes check, design 2.8's table)."""
    opened = [e.name for e in entries if e.spec.reasoning_channel == "template_opens"]
    out = {}
    for rid in sorted(r for r in od.rule_ids if models.rule_kind(r) == "sensitivity"):
        per = modes.get(rid, {})
        two_way = sorted(n for n, ms in per.items() if len({inc for _, inc in ms}) > 1)
        mixed = any(rid in g.mixed_modes for g in od.grants if rid in g.rules)
        one_way_opened = not (set(two_way) & set(opened))
        out[rid] = {"mixed_modes_granted": mixed, "two_way_entries": len(two_way),
                    "one_way_on_template_opened": one_way_opened, "consistent": mixed or one_way_opened}
    return out


# ====================================================================================================== CLI
def _hub_pairs() -> list[tuple[str, str, str | None]]:
    """(repo, revision, subfolder) of every entry's tokenizer and template, sorted: where the registry reads files."""
    pairs = {(s.tokenizer_from, s.tokenizer_revision, s.tokenizer_subfolder) for s in SOURCES}
    pairs |= {(s.template_from, s.template_revision, s.template_subfolder) for s in SOURCES}
    return sorted(pairs, key=str)


def tokenizer_files() -> list[tuple[Path, str]]:
    """Every cached tokenizer file of every entry (TOKENIZER_FILES at each tokenizer and template repo's pinned
    revision), as (cached path, path under the cache root). A runtime without this machine's Hugging Face cache needs
    these to load the registry: the trainer image ships them under its own cache root (design step 5, 25 Oct 2026)."""
    root = tokenizer_cache()
    out = []
    for repo, rev, sub in _hub_pairs():
        for f in TOKENIZER_FILES:
            p = hub_file(repo, f, rev, sub, required=False)
            if p is not None:
                out.append((p, p.relative_to(root).as_posix()))
    return out


def _fetch() -> None:
    """Download each entry's tokenizer files (tokenizer.json, tokenizer_config.json, special_tokens_map.json,
    chat_template.jinja) at its pinned revisions into `tokenizer_cache()`. No weights."""
    from huggingface_hub import hf_hub_download
    for repo, rev, sub in _hub_pairs():
        for f in TOKENIZER_FILES:
            try:
                hf_hub_download(repo, f, subfolder=sub, revision=rev, cache_dir=tokenizer_cache())
                print(f"ok {repo}@{rev[:8]}/{sub or ''}{f}")
            except Exception as e:  # noqa: BLE001 (an optional file, chat_template.jinja or special_tokens_map.json, may not exist)
                print(f"-- {repo}@{rev[:8]}/{sub or ''}{f}: {type(e).__name__}")


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "check"
    if cmd == "derive":
        for s in SOURCES:
            if argv[1:] and s.name not in argv[1:]:
                continue
            print(json.dumps({"name": s.name, **derive(s).as_pin()}, ensure_ascii=False))
        return 0
    if cmd == "pin":
        entries = write_pins()
        print(f"pinned {len(entries)} entries in {PINS_PATH}")
        return 0
    if cmd == "fetch":
        _fetch()
        return 0
    if cmd == "check":
        reg = load_registry(pin_owner_decisions=True)
        od = reg.owner_decisions
        print(json.dumps({"entries": {e.name: e.spec.spec_id for e in reg.entries},
                          "probe": reg.probe, "owner_decisions": {"status": od.status, "records": len(od.records),
                                                                  "grants": len(od.grants),
                                                                  "rule_ids": sorted(od.rule_ids),
                                                                  "problems": list(od.problems)}},
                         indent=1, default=list))
        return 0
    if cmd == "report":   # report [DIR] [--date YYYY-MM-DD]: the date names the file and its title (default RETRIEVED)
        rest = list(argv[1:])
        on = RETRIEVED
        if "--date" in rest:
            i = rest.index("--date")
            on = date.fromisoformat(rest[i + 1])
            del rest[i:i + 2]
        out = write_report(Path(rest[0]) if rest else ROOT / "results" / "_ingest", on=on)
        print(f"wrote {out}.json and {out}.md")
        return 0
    print(__doc__)
    return 2


def write_report(directory: Path, on: date = RETRIEVED) -> Path:
    """results/_ingest/registry_<on>.{json,md}: every entry with its spec id, derived and declared fields and
    citations; the rows each covers (tests/fixtures/registry/row_keys.json); the probe summary; the owner-decision
    status; and the renderers oracle's agreement on the probe cases with its listed diffs (D6), or why it did not run.
    `on` is the report's date (17 Oct 2026: the report after the owner's confirmation line); the citations keep the
    date they were read (RETRIEVED, printed as such)."""
    from withholding.typed import oracle
    reg = load_registry()
    manifest = json.loads((ROOT / "tests" / "fixtures" / "registry" / "row_keys.json").read_text())
    rows: dict[str, dict] = {}
    for rel, d in manifest["by_file"].items():
        for k, n in d["keys"]:
            model, revision, subfolder, ctf, kw, thinking = k
            row = {"model": model, "revision": revision, "subfolder": subfolder, "chat_template_from": ctf,
                   "thinking": thinking, **({"sampling": {"chat_template_kwargs": json.loads(kw)}} if kw else {})}
            c = rows.setdefault(reg.resolve(row).entry.name, {"rows": 0, "dirs": set()})
            c["rows"] += n
            c["dirs"].add(rel.rsplit("/", 1)[0])
    orc = oracle.probe_report(reg)
    od = reg.owner_decisions
    body = {"date": on.isoformat(), "citations_retrieved": RETRIEVED.isoformat(), "pins": str(PINS_PATH.relative_to(ROOT)),
            "pins_sha256": file_sha(PINS_PATH),
            "census": {"files": manifest["files"], "rows": manifest["rows"], "excluded": manifest["excluded"]},
            "entries": [{"name": e.name, "spec_id": e.spec.spec_id, "rows": rows.get(e.name, {}).get("rows", 0),
                         "dirs": sorted(rows.get(e.name, {}).get("dirs", ())),
                         "revision_patterns": list(e.source.revision_patterns),
                         **e.spec.model_dump(mode="json", exclude={"citations"}),
                         "citations": {k: c.source for k, c in e.spec.citations.items()}} for e in reg.entries],
            "design_distinct_groups": [list(g) for g in DESIGN_DISTINCT_GROUPS], "probe": reg.probe,
            "owner_decisions": {"status": od.status, "records": len(od.records), "grants": len(od.grants),
                                "rule_ids": sorted(od.rule_ids), "problems": list(od.problems)},
            "oracle": orc}
    directory.mkdir(parents=True, exist_ok=True)
    stem = directory / f"registry_{on.isoformat()}"
    stem.with_suffix(".json").write_text(json.dumps(body, indent=1, ensure_ascii=False, default=sorted) + "\n",
                                         encoding="utf-8")
    cmd = "python -m withholding.typed.registry report" + ("" if on == RETRIEVED else f" --date {on.isoformat()}")
    intro = (f"Written by `{cmd}` (withholding/typed/registry.py). "
             f"{len(reg.entries)} entries over {manifest['files']} output files and {manifest['rows']:,} rows "
             f"(results/c_full excluded). Every render probe reproduced its pins ({body['pins']}, sha256 "
             f"{body['pins_sha256'][:16]}), every delivery probe reproduced design 2.3's outcome table under the "
             f"four registered rule D ids, and the spec ids are distinct in every group the design names.")
    status = (f"OwnerDecision registry: {od.status} ({len(od.records)} records, {len(od.grants)} grants, "
              f"{len(od.rule_ids)} rule ids). " + " ".join(od.problems))
    md = [f"# Typed registry, {on.isoformat()}", "", intro + f" Citations read {RETRIEVED.isoformat()}.", "", status, "",
          "| entry | spec_id | rows | channel | forced open | trained channel | tokenizer | template | BOS |",
          "|---|---|---|---|---|---|---|---|---|"]
    for e in body["entries"]:
        tok = f"{e['tokenizer_from']}@{e['tokenizer_revision'][:8]}" + (f"/{e['tokenizer_subfolder']}"
                                                                         if e["tokenizer_subfolder"] else "")
        md.append(f"| {e['name']} | {e['spec_id']} | {e['rows']:,} | {e['reasoning_channel']} | "
                  f"{e['think_open_in_prompt']} | {e['trained_answer_channel']} | {tok} | {e['template_sha'][:12]} | "
                  f"{e['bos']['bos_id']}x{e['bos']['expected_at_start']} |")
    if orc.get("ran"):
        line = (f"renderers oracle ({orc['env']['renderers']}, {orc['env']['transformers']}, lock "
                f"{orc['env']['lock_sha']}): {orc['requests']} probe cases compared with rule D under step "
                f"{orc['compared_rule']}'s id; {len(orc['diffs'])} listed diffs, {len(orc['errors'])} errors (D6: a "
                f"diff is listed, never a failure).")
        md += ["", line, "", "| case | agree | differ |", "|---|---|---|"]
        md += [f"| {c} | {v['agree']} | {v['differ']} |" for c, v in sorted(orc["by_case"].items())]
    else:
        md += ["", f"renderers oracle not run: {orc['env'].get('reason')}"]
    stem.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return stem


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


# Design 2.1 invariant 8: a render or delivery probe that does not reproduce raises RegistryError at import, so nothing
# that imports the registry runs or scores. Run as a script, the file skips this load (`pin` must work on stale pins).
if __name__ != "__main__":
    REGISTRY: Registry = load_registry()
