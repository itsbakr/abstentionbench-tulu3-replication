"""Typed ingestion: classification, delivery under rule D, and the only issuer of sealed delivered text.

Design: `notes/typed_ingestion_design_2026-10-15.md` (cited "design N", as committed in 9e10244), with the decisions of
`notes/typed_layer_decisions_2026-10-15.md` (OD-1 to OD-5, D1 to D16).

Three layers, in this file:
1. Rule ids (design 2.3, "Rule ids"). The rule D parameters are `withholding.typed.models.RuleD`; its id is computed,
   never written by hand. Step 0's registered set holds the four ids the design names, step 2a's first:
   `RULE_D_2A` (OD-1's grant), `RULE_D_2B` (D2's), `RULE_D_2C` (D3's) and `RULE_D_POST_2D` (D4's, the adopted id).
   `tests/typed/test_ingest.py` checks that these are exactly the rule D ids the decisions note's `rule:` grant lines
   hold. Nothing here reads a signed registry: step 0 must not depend on the owner's confirmation line (D11).
2. The content core on raw text: `compute_facts` (ThinkFacts), `derive_state` (the precedence table of 2.3) and
   `deliver_spans` (2.3's `deliver`: the region, D15's closed inner blocks and OD-1's inner-open cut; section 9 (a)'s
   forced branch as the spot check requires it). Every rule reads a marker, a template role line or the end of the
   text; no count, window or position cut-off enters a read (CLAUDE.md rule 8).
3. The typed layer. `register` keeps a completion in this process's store; `classify` builds the `Completion`;
   `deliver(completion_key, rule_id)` issues the sealed `DeliveredText` (the family is read from the completion key's
   prompt id, never passed); `check_delivered` re-verifies one; `sidecar_record` writes offsets and hashes, never
   text; `classify_stored_row` does all of it for one stored output row (the backfill's entry point). Step 1 adds
   the legacy read views: `register_legacy` reads the frozen 14 Oct reading off a stored row once, and
   `read_legacy(completion_key, binding)` issues the sealed `LegacyReadText` an entry of that binding reads. Step 2r
   (19 Oct 2026) adds the recognition harness's view: `trace_view(completion_key, rule_id)` issues the sealed
   `TraceView` (the reasoning and the delivered segments, numbered in text order, under one rule id), and
   `trace_view_sha` names it for a verdict.

The seal (design 2.0). This module claims the ingest issuer of `models.py` once, at import
(`models.claim_issuer("ingest", instance_check=...)`): the HMAC key and the validation-context token are minted by
that call, so per process and when ingest is imported, and are never stored or exported. Sidecars hold offsets, and
`deliver` re-issues an instance from the store. The MAC is models' (every declared field but text and mac); the
instance check is this module's (`_instance_check`): the text is its completion's raw text over its spans, and
re-running delivery on the stored completion under the text's own rule id and family gives the same spans, mode and
flags. One protocol only: this module exposes no `is_ingest_issuer`, `verify_sealed` or `verify_delivered`, so
models' integration bridge (which would accept those) stays unused. The registered rule-id set is models' active
registry, read from the decisions note's grants (unsigned is fine in step 0); `REGISTERED_RULE_IDS` lists the same
four in step order, and the registry load and tests/typed/test_ingest.py check that they agree.

Step 0 changes no behaviour: no scorer, judge builder, reward or report reads anything here. Delivery is computed
into the backfill sidecar only (task brief; design section 6, step 0). Step 1 changes none either: the typed entries
read LegacyReadText under today's readings, proven byte-identical by diff (design section 6, step 1). Step 2a (17 Oct
2026) is the behaviour change: every scorer and judge builder of record reads `deliver`'s DeliveredText under
`primary_rule_id()` (design section 6, step 2a, and its Revision 7). Step 2b (17 Oct 2026, D2) moves the primary id to
close=first with rlcr.close=last; step 2c (17 Oct 2026, D3) to stray=content; step 2d (18 Oct 2026, D4) to
turn=cut_at_boundary, the adopted post-2d id: a turn is cut at its first boundary, a line holding only one of the
template's derived role names with non-whitespace text before it, before the think split.
"""
from __future__ import annotations

import hashlib as _hashlib
import json as _json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date as _date
from functools import cache
from typing import Any

from withholding.typed import models as _M

ThinkState = _M.ThinkState
UndeliveredReason = _M.UndeliveredReason
DeliveryMode = _M.DeliveryMode
THINK_STATES: tuple[str, ...] = _M.THINK_STATES  # the precedence order of design 2.3's table
UNDELIVERED_REASONS: frozenset[str] = _M.UNDELIVERED_REASONS
NOT_RECORDED = "not_recorded"


class RuleError(ValueError):
    """A rule D id that is not the canonical form of a RuleD, or not in the registered set (design 2.3)."""


class IngestError(ValueError):
    """A row the typed layer refuses, reported as file:line:id:reason (design section 3, "ingest, stored rows").
    `where` is "file:line"; `file` and `line` build it when given apart."""

    def __init__(self, reason: str, *, where: str | None = None, row_id: str | None = None, file: str | None = None,
                 line: int | None = None):
        if where is None and file is not None:
            where = f"{file}:{'-' if line is None else line}"
        self.reason, self.where, self.row_id = reason, where, row_id
        super().__init__(f"{where or '-'}:{row_id or '-'}:{reason}")


class UnclassifiableError(IngestError):
    """A row whose facts reach no state of the precedence table (design 2.3): listed by the backfill, never scored."""


# ================================================================================================ rule D ids (2.3)
_RULE_DATE = _date(2026, 10, 15)
RULE_D_2A = _M.RuleD(date=_RULE_DATE, close="last", stray="after_tag", turn="none")
RULE_D_2B = _M.RuleD(date=_RULE_DATE, close="first", stray="after_tag", turn="none", overrides=(("rlcr", "last"),))
RULE_D_2C = _M.RuleD(date=_RULE_DATE, close="first", stray="content", turn="none", overrides=(("rlcr", "last"),))
RULE_D_POST_2D = _M.RuleD(date=_RULE_DATE, close="first", stray="content", turn="cut_at_boundary",
                          overrides=(("rlcr", "last"),))
# Step 0's registered set, in step order (design 2.3: "The four rule D ids are step 2a's (OD-1), 2b's (D2), 2c's (D3)
# and 2d's (D4)"). Step 2a's id is first: it is the id step 0's sidecar and every Completion are read under.
REGISTERED_RULE_IDS: tuple[str, ...] = tuple(r.rule_id for r in (RULE_D_2A, RULE_D_2B, RULE_D_2C, RULE_D_POST_2D))
STEP_2A_RULE_ID: str = RULE_D_2A.rule_id
POST_2D_RULE_ID: str = RULE_D_POST_2D.rule_id
# The primary read rule of every scorer and judge builder (design section 6, step 2a, 17 Oct 2026): the step whose rule
# D id the stored score files and every new score line are read under. Steps 2b to 2d move it one parameter each.
# Step 2b (17 Oct 2026; D2): close=first, with the RLCR override rlcr.close=last (scripts/rescore_rule_d_2b.py).
# Step 2c (17 Oct 2026; D3): stray=content, a close with no opener is content (scripts/rescore_rule_d_2c.py).
# Step 2d (18 Oct 2026; D4): turn=cut_at_boundary, the adopted post-2d id; an invented turn is cut at the first
# boundary the template's derived role names mark (TemplateSpec.role_names, design 2.1), before the think split
# (scripts/rescore_rule_d_2d.py). D21 names this id for C's reward.
PRIMARY_STEP = "post-2d"


def parse_rule_id(rule_id: str) -> _M.RuleD:
    """The RuleD whose canonical id is exactly `rule_id`, registered or not; RuleError for anything else (a prefix, a
    reordering, a sensitivity id, an override equal to the default)."""
    if not isinstance(rule_id, str):
        raise RuleError(f"a rule id is a str, got {type(rule_id).__name__}")
    try:
        return _M.parse_rule_d(rule_id)
    except ValueError as e:
        raise RuleError(f"not a canonical rule D id: {rule_id!r} ({e})") from e


def primary_rule_id() -> str:
    """The primary rule D id (design 2.3 and section 6, step 2a): the canonical id the registry derives for
    `PRIMARY_STEP`'s parameters (models.RULE_D_STEPS), checked to be registered by a grant of the decisions note and to
    be one of step 0's four. Every scorer and judge builder of record reads DeliveredText under this id; nothing types
    the string by hand. RuleError when the active registry does not register it."""
    rule_id = dict(_M.RULE_D_STEPS)[PRIMARY_STEP].rule_id
    registered_rule(rule_id)
    return rule_id


def registered_rule(rule_id: str) -> _M.RuleD:
    """The RuleD of a registered rule D id, matched exactly (design 2.3: a prefix or a substring never matches): a
    canonical rule D id that a grant of the decisions note registers (models' active registry) and that is one of
    step 0's four. RuleError for a non-canonical or unregistered id, or for anything that is not a str."""
    rule = parse_rule_id(rule_id)
    if rule_id not in REGISTERED_RULE_IDS or rule_id not in _M.active_registry().decisions.rule_d_ids:
        raise RuleError(f"rule D id not registered: {rule_id!r}")
    return rule


# ================================================================================================ template facts read
@dataclass(frozen=True)
class Markers:
    """What rule D reads from a TemplateSpec (design 2.1): the markers, the role names of its turn headers, and
    whether the generation prefix opened the block (`think_open_in_prompt`) or holds an empty closed one
    (`reasoning_channel == "template_closed"`, Qwen3 thinking off)."""

    open_marker: str
    close_marker: str
    role_names: tuple[str, ...]
    opened_in_prompt: bool
    prefix_closed: bool

    def __post_init__(self) -> None:
        if not self.open_marker or not self.close_marker or self.open_marker == self.close_marker:
            raise ValueError("open and close markers must be distinct and non-empty")
        if self.opened_in_prompt and self.prefix_closed:
            raise ValueError("a prefix cannot both open the block and hold a closed one")
        if any((not n) or n != n.strip() or "\n" in n for n in self.role_names):
            raise ValueError(f"role names must be one-line, stripped and non-empty: {self.role_names!r}")


def markers_of(spec: Any) -> Markers:
    """The Markers of a TemplateSpec: its markers, its derived role names, `think_open_in_prompt` and whether its
    reasoning channel is `template_closed` (design 2.1)."""
    return Markers(open_marker=spec.open_marker, close_marker=spec.close_marker, role_names=tuple(spec.role_names),
                   opened_in_prompt=bool(spec.think_open_in_prompt),
                   prefix_closed=spec.reasoning_channel == "template_closed")


@cache
def _role_line(role_names: tuple[str, ...]) -> re.Pattern[str] | None:
    """A line holding only one of the role names, with spaces or tabs around it (the census rule of
    /tmp/typed_design/classify_v2.py, with the spec's own role names in place of its fixed three)."""
    if not role_names:
        return None
    alt = "|".join(re.escape(n) for n in sorted(set(role_names), key=lambda s: (-len(s), s)))
    return re.compile(rf"^[ \t]*(?:{alt})[ \t]*$", re.MULTILINE)


def role_lines(raw: str, role_names: tuple[str, ...], start: int = 0, end: int | None = None) -> list[int]:
    """Start offsets of every role line inside raw[start:end] (offsets into raw)."""
    rx = _role_line(tuple(role_names))
    if rx is None:
        return []
    return [m.start() for m in rx.finditer(raw, start, len(raw) if end is None else end)]


def _first_non_ws(raw: str) -> int:
    """Offset of the first non-whitespace character of raw, or len(raw) when there is none."""
    return len(raw) - len(raw.lstrip())


def _find_all(raw: str, marker: str, start: int, end: int) -> list[int]:
    """Start offsets of every occurrence of `marker` inside raw[start:end], left to right, non-overlapping."""
    out, i = [], raw.find(marker, start, end)
    while i >= 0:
        out.append(i)
        i = raw.find(marker, i + len(marker), end)
    return out


def _scan_blocks(raw: str, m: Markers, start: int, end: int,
                 skip: int | None) -> tuple[list[tuple[int, int]], int | None]:
    """Closed blocks inside raw[start:end], found left to right, each open marker paired with the first close marker
    after it, as (open start, close end); and the first open marker with no close after it. `skip` is the turn's own
    opener, which is no inner block (design 2.3, ThinkFacts.inner_blocks and inner_open_at)."""
    blocks: list[tuple[int, int]] = []
    pos = start
    while True:
        o = raw.find(m.open_marker, pos, end)
        if o < 0:
            return blocks, None
        if o == skip:
            pos = o + len(m.open_marker)
            continue
        c = raw.find(m.close_marker, o + len(m.open_marker), end)
        if c < 0:
            return blocks, o
        blocks.append((o, c + len(m.close_marker)))
        pos = c + len(m.close_marker)


_QUOTES = "`'\"“”‘’"
_ELLIPSIS = re.compile(r"[\s.…]*")


def _quotes_format(raw: str, m: Markers, first_close: int, prompt_texts: tuple[str, ...]) -> bool:
    """The first close sits in a quoted format mention (nit 20; a fact, never a rule): the close is wrapped in quote
    characters, or the open marker before it on its own line starts a pair `<open>X<close>` that is quoted from a
    prompt message or whose X is only whitespace and dots (the RLCR prompt's "<think> reasoning process here </think>"
    and its paraphrases "<think> ... </think>")."""
    end = first_close + len(m.close_marker)
    if first_close > 0 and end < len(raw) and raw[first_close - 1] in _QUOTES and raw[end] in _QUOTES:
        return True
    line_start = raw.rfind("\n", 0, first_close) + 1
    o = raw.rfind(m.open_marker, line_start, first_close)
    if o < 0:
        return False
    inner = raw[o + len(m.open_marker):first_close]
    return bool(_ELLIPSIS.fullmatch(inner)) or any(raw[o:end] in t for t in prompt_texts)


def compute_facts(raw: str, m: Markers, *, chat_kwargs: Mapping[str, Any] | None = None,
                  accepted_kwargs: frozenset[str] | None = None, prompt_texts: tuple[str, ...] = ()) -> dict:
    """ThinkFacts of design 2.3, computed from text (the rule for stored rows). Offsets index `raw` (str positions).

    The turn is raw up to its first boundary (a role line with non-whitespace text before it), else all of raw; the
    close counts, the inner blocks and the inner open are read inside that turn. A role line with only whitespace
    before it is a leading role header, a fact and never a boundary (the 373 RL-Zero Code rows, design 2.3).
    `opened_by` is "template" whenever the generation prefix opened the block (a fact of the template, so it holds on
    an empty completion too), "model" when the first non-whitespace text is the open marker, else None (a
    template_closed prefix opens nothing in the completion). `ignored_kwargs` lists stored chat kwargs the template
    does not read (audit 28); a row that carries chat kwargs needs the spec's accepted kwargs, which are never assumed.
    """
    if chat_kwargs and accepted_kwargs is None:
        raise ValueError("accepted_kwargs is required when the row carries chat kwargs")
    fnw = _first_non_ws(raw)
    empty = fnw == len(raw)
    lines = role_lines(raw, m.role_names)
    boundary = next((p for p in lines if fnw < p), None)  # non-whitespace text sits before the role line
    leading = any(p <= fnw for p in lines)
    turn_end = len(raw) if boundary is None else boundary
    if m.opened_in_prompt:
        opened_by: str | None = "template"
    elif not empty and raw.startswith(m.open_marker, fnw):
        opened_by = "model"
    else:
        opened_by = None
    own_open = fnw if opened_by == "model" else None
    closes = _find_all(raw, m.close_marker, 0, turn_end)
    n = len(closes)
    if opened_by is not None and closes:  # inside the turn's own block nothing is an inner block
        inner_blocks, inner_open = _scan_blocks(raw, m, closes[0] + len(m.close_marker), turn_end, None)
    elif opened_by is not None:  # an unclosed turn: any other open marker has no close after it
        inner_blocks, inner_open = [], _scan_blocks(raw, m, 0, turn_end, own_open)[1]
    else:
        inner_blocks, inner_open = _scan_blocks(raw, m, 0, turn_end, None)
    first = closes[0] if closes else None
    ignored = tuple(sorted(k for k in (chat_kwargs or {}) if k not in (accepted_kwargs or frozenset())))
    return {
        "empty": empty,
        "turn_boundary_at": boundary,
        "leading_role_header": leading,
        "opened_by": opened_by,
        "prefix_closed": m.prefix_closed,
        "n_close_in_turn": n,
        "first_close_at": first,
        "last_close_at": closes[-1] if closes else None,
        "close_after_odd_fence": first is not None and raw.count("```", 0, first) % 2 == 1,
        "close_quotes_format": first is not None and _quotes_format(raw, m, first, tuple(prompt_texts)),
        "inner_open_at": inner_open,
        "forced_open": opened_by == "template",
        "unclosed": opened_by is not None and n == 0,
        "has_turn_boundary": boundary is not None,
        "multiple_close": opened_by is not None and n >= 2,
        "stray_close": opened_by is None and n >= 1,
        "inner_open_unclosed": inner_open is not None,
        "inner_blocks": tuple(inner_blocks),
        "inner_block_closed": bool(inner_blocks),
        "ignored_kwargs": ignored,
    }


def derive_state(facts: Mapping[str, Any], finish_reason: str) -> str:
    """The one think_state label, by the fixed precedence of design 2.3's table. Reads the facts and finish_reason,
    never a channel. A model-opened unclosed turn whose finish_reason is not recorded fits neither state 4 nor 5 and
    is unclassifiable (no stored row: the 4 rows without finish_reason open no block)."""
    if facts["empty"]:
        return "empty"
    if facts["turn_boundary_at"] is not None:
        return "invented_turns"
    ob, n = facts["opened_by"], facts["n_close_in_turn"]
    if ob == "template" and n == 0:
        return "forced_open_unclosed"
    if ob == "model" and n == 0:
        if finish_reason == "length":
            return "unclosed_cap"
        if finish_reason == "stop":
            return "unclosed_stop"
        raise UnclassifiableError(f"model-opened unclosed turn with finish_reason {finish_reason!r}")
    if ob is not None:
        return "multiple_close" if n >= 2 else "closed"
    return "stray_close" if n >= 1 else "no_tags"


# ============================================================================================ delivery (2.3, D15, 9a)
@dataclass(frozen=True)
class ForcedOrigin:
    """What delivery reads of a forced_close row's origin (design 9 (a)): where our close was appended in the stitched
    raw text, and its text (never model text)."""

    boundary_char: int
    appended_text: str


@dataclass(frozen=True)
class Outcome:
    """Rule D's reading of one completion under one rule id: the delivered spans (offsets into raw, joined with nothing
    inserted) or the undelivered reason, the mode, the closed blocks D15 removed, whether the region ended at an inner
    open or ran into the token cap, the reasoning spans (the turn's own block, then each removed block), and the
    region before the in-region scan. `inner_open` (step 2r, 19 Oct 2026) is the block OD-1's cut ended the region at:
    from its open marker to the region's end, reasoning that never closed (the recognition harness reads it, design
    step 2r; no delivery field reads it, so the sidecars are unchanged)."""

    spans: tuple[tuple[int, int], ...]
    mode: str | None
    undelivered_reason: str | None
    removed_blocks: tuple[tuple[int, int], ...]
    cut_at_inner_open: bool
    cut_at_cap: bool
    reasoning_spans: tuple[tuple[int, int], ...]
    region: tuple[int, int] | None
    inner_open: tuple[int, int] | None = None

    @property
    def delivered(self) -> bool:
        """True when rule D delivers a non-blank text."""
        return self.undelivered_reason is None

    @property
    def blocks_removed(self) -> int:
        """D15: how many closed blocks were dropped from the region."""
        return len(self.removed_blocks)


def _undelivered(reason: str, *, reasoning: tuple[tuple[int, int], ...] = (), region: tuple[int, int] | None = None,
                 removed: tuple[tuple[int, int], ...] = (), cut: bool = False,
                 inner: tuple[int, int] | None = None) -> Outcome:
    return Outcome(spans=(), mode=None, undelivered_reason=reason, removed_blocks=tuple(removed),
                   cut_at_inner_open=cut, cut_at_cap=False,
                   reasoning_spans=tuple(s for s in tuple(reasoning) + tuple(removed) if s[1] > s[0]), region=region,
                   inner_open=inner)


def _stray_start(raw: str, m: Markers, s: int, e: int) -> int:
    """For a forced row under after_tag: where the region starts, after the last close in raw[s:e] that closes no
    block opened inside raw[s:e] (blocks paired left to right, as D15 pairs them); s when there is none (the spot
    check's required fix to design 9 (a): a close the model writes after ours is read under D3)."""
    pos, last = s, None
    while True:
        o, k = raw.find(m.open_marker, pos, e), raw.find(m.close_marker, pos, e)
        if k >= 0 and (o < 0 or k < o):
            last = pos = k + len(m.close_marker)
            continue
        if o < 0:
            return s if last is None else last
        k2 = raw.find(m.close_marker, o + len(m.open_marker), e)
        if k2 < 0:
            return s if last is None else last
        pos = k2 + len(m.close_marker)


def turn_end_under(raw: str, facts: Mapping[str, Any], rule: _M.RuleD) -> int:
    """Where the turn ends under the rule: the first boundary when D4 is cut_at_boundary, else the end of raw."""
    b = facts["turn_boundary_at"]
    return b if (rule.turn == "cut_at_boundary" and b is not None) else len(raw)


def deliver_spans(raw: str, facts: Mapping[str, Any], m: Markers, rule: _M.RuleD, family: str, finish_reason: str,
                  provenance: str = "first_pass", origin: ForcedOrigin | None = None) -> Outcome:
    """Design 2.3's `deliver` on raw text: the region rule D reads (D2 close, D3 stray, D4 turn, the task override of
    `family`), then, every spec, D15's closed inner blocks dropped and OD-1's inner-open cut. The family picks the task
    close override; callers read it from the prompt id, never from a scorer's argument (2.3, "The task is the
    family"). A forced_close row reads only the model's text after our appended close, with D4, D3, D15 and the
    inner-open cut applied inside it (the spot check's fix to 9 (a)); D2 does not apply there."""
    if facts["empty"]:
        return _undelivered("empty_output")
    own: tuple[tuple[int, int], ...] = ()
    if provenance == "forced_close":
        if origin is None:
            raise ValueError("a forced_close row needs its origin")
        s = origin.boundary_char + len(origin.appended_text)
        if rule.turn == "cut_at_boundary":
            nb = next(iter(role_lines(raw, m.role_names, s)), None)
            turn_end = len(raw) if nb is None else nb
        else:
            turn_end = len(raw)
        if s > turn_end:
            raise ValueError("a forced row's appended close ends after its turn")
        if rule.stray == "after_tag":
            s2 = _stray_start(raw, m, s, turn_end)
            if s2 > s:
                own = ((s, s2),)
            s = s2
        region, mode = (s, turn_end), "after_close"
        own = ((0, origin.boundary_char),) + own
    else:
        turn_end = turn_end_under(raw, facts, rule)
        closes = _find_all(raw, m.close_marker, 0, turn_end)
        if facts["opened_by"] is None:
            if rule.stray == "after_tag" and closes:
                split = closes[-1] + len(m.close_marker)
                region, mode = (split, turn_end), "after_close"
                own = ((0, split),)  # after_tag reads the text before the tag as a block it closed
            else:
                region, mode = (0, turn_end), "whole_turn"
        else:
            start = 0 if facts["opened_by"] == "template" else _first_non_ws(raw)
            if not closes:
                return _undelivered("unclosed_block", reasoning=((start, turn_end),))
            k = closes[0] if rule.close_for(family) == "first" else closes[-1]
            split = k + len(m.close_marker)
            region, mode = (split, turn_end), "after_close"
            own = ((start, split),)
    s, e = region
    if rule.turn == "cut_in_delivered":
        fnw = _first_non_ws(raw)
        nb = next((p for p in role_lines(raw, m.role_names, s, e) if fnw < p), None)
        e = e if nb is None else nb
    pieces: list[tuple[int, int]] = []
    removed: list[tuple[int, int]] = []
    pos, cut, inner = s, False, None
    while True:
        o = raw.find(m.open_marker, pos, e)
        if o < 0:
            pieces.append((pos, e))
            break
        pieces.append((pos, o))
        c = raw.find(m.close_marker, o + len(m.open_marker), e)
        if c < 0:  # OD-1: a block opened inside the region and never closed ends the region at its open marker
            cut, inner = True, (o, e)
            break
        removed.append((o, c + len(m.close_marker)))  # D15: a closed block inside the region is reasoning
        pos = c + len(m.close_marker)
    spans = tuple(p for p in pieces if p[1] > p[0])
    if not "".join(raw[a:b] for a, b in spans).strip():
        reason = "empty_before_inner_open" if cut else ("empty_outside_blocks" if removed else "empty_after_close")
        return _undelivered(reason, reasoning=own, region=(s, e), removed=tuple(removed), cut=cut, inner=inner)
    cap = finish_reason == "length" and not cut and e == len(raw)
    reasoning = tuple(x for x in own + tuple(removed) if x[1] > x[0])
    return Outcome(spans=spans, mode=mode, undelivered_reason=None, removed_blocks=tuple(removed),
                   cut_at_inner_open=cut, cut_at_cap=cap, reasoning_spans=reasoning, region=(s, e), inner_open=inner)


def join_spans(raw: str, spans: Sequence[Sequence[int]]) -> str:
    """The delivered text: raw over each span, joined with nothing inserted."""
    return "".join(raw[a:b] for a, b in spans)


def sha256_hex(text: str) -> str:
    """sha256 of a str's UTF-8 bytes, 64 hex (raw_sha, text_sha)."""
    return _hashlib.sha256(text.encode("utf-8")).hexdigest()


# ================================================================================================ keys and identities
def run_identity(*, model: str, subfolder: str | None, revision: str | None, spec_id: str, generation_config_id: str,
                 draw: str) -> _M.RunIdentity:
    """Design 2.3's RunIdentity (Revision 4): the weights, the spec, the generation config and the draw (the output
    file's real path relative to results/). The subfolder is part of it, so the Cascade stages never collapse (2.5); the
    draw is, so two files of one configuration never share a key. A row that recorded no revision (the 4 local MLX
    smoke rows) is not_recorded."""
    return _M.RunIdentity(model=model, subfolder=subfolder, revision=NOT_RECORDED if revision is None else revision,
                          spec_id=spec_id, generation_config_id=generation_config_id, draw=draw)


def run_id_of(**identity: Any) -> str:
    """The run id of `run_identity(**identity)`: the first 16 hex of its canonical sha."""
    return run_identity(**identity).run_id


# One key rule, models' (design 2.3, Revision 4): `<run_id>/<prompt_sha>/<prompt id>#<sample>`.
completion_key = _M.completion_key
split_key = _M.split_completion_key


def family_of_key(key: str) -> str:
    """The family of a completion: its prompt id's family prefix (design 2.2 ties it to the PromptRecord's gold)."""
    return _M.family_of(split_key(key).prompt_id)


# ============================================================================================== the completion store
@dataclass(frozen=True)
class _Entry:
    """What deliver() re-reads for one completion key: the raw text and the facts it was classified with."""

    key: str
    raw: str
    raw_sha: str
    spec_id: str
    markers: Markers
    facts: dict
    family: str
    finish_reason: str
    provenance: str
    origin: ForcedOrigin | None
    prompt_sha: str
    same: str
    stitch_at: int | None = None  # a continuation's stitch_char (design 9 (b)): kept for its TraceView, never read by rule D


_STORE: dict[str, _Entry] = {}
_SAME: dict[str, set[str]] = {}  # same_completion_id -> the keys in the store that hold that completion (Revision 4)


def _forced_origin(origin: Any) -> ForcedOrigin | None:
    if origin is None or isinstance(origin, (_M.Continuation, _M.Redraw)):
        return None
    if isinstance(origin, _M.ForcedClose):
        return ForcedOrigin(boundary_char=origin.boundary_char, appended_text=origin.appended_text)
    if isinstance(origin, ForcedOrigin):
        return origin
    raise IngestError(f"unknown origin type {type(origin).__name__}")


def _check_origin(key: str, raw: str, provenance: str, origin: Any, m: Markers) -> None:
    """The issuer's checks of design 9 (a) and (b) with the spot check's fixes: the origin is set exactly when the
    provenance is forced_close or continuation (a redraw may carry a Redraw record, a first pass none); a forced row's
    first_pass_reason is re-derived from its first pass under `selected_under`, its boundary is that first pass's turn
    end under that rule, and its raw is the first pass's turn, our close, then the continuation; a continuation
    continues a cut first pass from its end; a redraw's first pass, when it is in the store, was cut at its budget."""
    if provenance == "redraw":
        if origin is None:
            return
        if not isinstance(origin, _M.Redraw):
            raise IngestError("a redraw's origin is a Redraw record", row_id=key)
        first = _STORE.get(origin.first_pass_key) if origin.first_pass_key else None
        if first is not None and (split_key(first.key)[1:] != split_key(key)[1:] or first.finish_reason != "length"):
            raise IngestError("a redraw replaces a first pass of its (prompt sha, prompt id, sample) that was cut",
                              row_id=key)
        return
    want = {"forced_close": _M.ForcedClose, "continuation": _M.Continuation}.get(provenance)
    if want is None:
        if origin is not None:
            raise IngestError(f"provenance {provenance} carries no origin", row_id=key)
        return
    if not isinstance(origin, want):
        raise IngestError(f"provenance {provenance} needs a {want.__name__} origin", row_id=key)
    first = _STORE.get(origin.first_pass_key)
    if first is None:
        raise IngestError("the first pass is not in this process's store", row_id=key)
    if split_key(first.key)[1:] != split_key(key)[1:]:  # every key part but the run id: prompt sha, prompt id, sample
        raise IngestError("a forced or continuation row and its first pass differ in (prompt sha, prompt id, sample)",
                          row_id=key)
    if provenance == "continuation":
        if first.finish_reason != "length":
            raise IngestError(f"a continuation needs a cut first pass, not {first.finish_reason}", row_id=key)
        if origin.stitch_char != len(first.raw) or not raw.startswith(first.raw):
            raise IngestError("stitch_char is not the first pass's length, or raw does not begin with it", row_id=key)
        return
    if first.provenance == "forced_close":
        raise IngestError("a forced row's first pass is itself a forced row", row_id=key)
    rule = registered_rule(origin.selected_under)
    o = deliver_spans(first.raw, first.facts, first.markers, rule, first.family, first.finish_reason,
                      first.provenance, first.origin)
    if o.undelivered_reason not in ("unclosed_block", "empty_before_inner_open"):
        raise IngestError(f"the first pass reads {o.undelivered_reason or 'delivered'} under selected_under: "
                          "not forcible", row_id=key)
    if o.undelivered_reason != origin.first_pass_reason:
        raise IngestError(f"first_pass_reason {origin.first_pass_reason!r}, the first pass reads "
                          f"{o.undelivered_reason!r} under selected_under", row_id=key)
    te = turn_end_under(first.raw, first.facts, rule)
    if origin.boundary_char != te:
        raise IngestError(f"boundary_char {origin.boundary_char} is not the first pass's turn end ({te})", row_id=key)
    if raw[:te] != first.raw[:te] or not raw.startswith(origin.appended_text, te):
        raise IngestError("raw is not the first pass's turn, our appended close, then the continuation", row_id=key)
    if origin.appended_text.count(m.close_marker) != 1:
        raise IngestError("the appended text holds the close marker exactly once", row_id=key)


def register(*, key: str, run: _M.RunIdentity, raw: str, spec: Any, finish_reason: str, prompt: Any,
             provenance: str = "first_pass", origin: Any = None, chat_kwargs: Mapping[str, Any] | None = None) -> dict:
    """Classify one raw completion into this process's store and return its ThinkFacts fields.

    The key must be `run`'s, under `spec`, and name the PromptRecord by id and by content: its prompt sha is the
    record's (design 2.3, Revision 4; this closes the spot check's residual, a row keyed under another prompt's id
    read under that prompt's task). The family is read from the key's prompt id. A key registered twice must carry the
    same raw text, spec and provenance. The store indexes the completion under its same-completion id, so
    `copies_of` names the other keys that hold it."""
    if not isinstance(raw, str):
        raise IngestError("raw text must be a str", row_id=key)
    k = split_key(key)
    prompt_id = k.prompt_id
    if prompt_id != prompt.id:
        raise IngestError(f"key prompt id {prompt_id!r} is not the PromptRecord's {prompt.id!r}", row_id=key)
    if k.prompt_sha != prompt.prompt_sha:
        raise IngestError("the key's prompt sha is not the PromptRecord's (design 2.3, Revision 4)", row_id=key)
    if (k.run_id, run.spec_id) != (run.run_id, spec.spec_id):
        raise IngestError("the key is not its RunIdentity's, or the run names another spec", row_id=key)
    family = _M.family_of(prompt_id)
    if family != prompt.family:
        raise IngestError(f"prompt family {prompt.family!r} differs from the key's {family!r}", row_id=key)
    m = markers_of(spec)
    _check_origin(key, raw, provenance, origin, m)
    facts = compute_facts(raw, m, chat_kwargs=chat_kwargs or {}, accepted_kwargs=frozenset(spec.accepted_kwargs),
                          prompt_texts=tuple(x.content for x in prompt.messages))
    raw_sha = sha256_hex(raw)
    entry = _Entry(key=key, raw=raw, raw_sha=raw_sha, spec_id=spec.spec_id, markers=m, facts=facts,
                   family=family, finish_reason=finish_reason, provenance=provenance,
                   origin=_forced_origin(origin), prompt_sha=prompt.prompt_sha,
                   same=_M.same_completion_id(run, key, raw_sha),
                   stitch_at=origin.stitch_char if isinstance(origin, _M.Continuation) else None)
    old = _STORE.get(key)
    if old is not None and (old.raw_sha, old.spec_id, old.provenance) != (entry.raw_sha, entry.spec_id,
                                                                          entry.provenance):
        raise IngestError("completion key already registered with another text, spec or provenance", row_id=key)
    _STORE[key] = entry
    _SAME.setdefault(entry.same, set()).add(key)
    return facts


def copies_of(completion_key: str) -> tuple[str, ...]:
    """The other keys in this process's store that hold the same completion (design 2.3, Revision 4: one set of weights
    under one spec wrote the same raw text for the same prompt and sample), sorted. A copy in another output file, or
    a merged extension row beside the outputs_ext.jsonl row it was copied from, has its own key and is named here."""
    e = _entry(completion_key)
    return tuple(sorted(_SAME.get(e.same, set()) - {completion_key}))


def forget(keys: Sequence[str] | None = None) -> None:
    """Drop completions from this process's store (all of them when `keys` is None); the backfill calls it per
    directory so the store never holds a whole corpus."""
    if keys is None:
        _STORE.clear()
        _SAME.clear()
        _LEGACY.clear()
        return
    for k in keys:
        _LEGACY.pop(k, None)
        e = _STORE.pop(k, None)
        if e is not None:
            group = _SAME.get(e.same)
            if group is not None:
                group.discard(k)
                if not group:
                    del _SAME[e.same]


def _entry(completion_key: str) -> _Entry:
    try:
        return _STORE[completion_key]
    except (KeyError, TypeError):
        raise IngestError("completion not in this process's store (register or classify it first)",
                          row_id=str(completion_key)) from None


def outcome(completion_key: str, rule_id: str) -> Outcome:
    """Rule D's offsets for a stored completion under a registered rule id (the sidecar's content; no text)."""
    e = _entry(completion_key)
    rule = registered_rule(rule_id)
    return deliver_spans(e.raw, e.facts, e.markers, rule, e.family, e.finish_reason, e.provenance, e.origin)


# ================================================================================================= sealed delivery
_SEALED_FIELDS = ("completion_key", "spec_id", "family", "spans", "text_sha", "blocks_removed", "provenance", "mode",
                  "rule_id", "finish_reason", "includes_reasoning", "cut_at_cap", "cut_at_inner_open")


def _check_delivered_against_store(dt: Any) -> None:
    """The DeliveredText instance check (design 2.0; review item 4; Revision 3): the text equals the join of its
    completion's raw text over its spans; family, spec, provenance and finish_reason are the stored completion's; a
    forced row's text never starts before the end of our appended close; re-running rule D on the stored completion
    under the text's own rule id gives the same spans, mode and flags. ValueError on any mismatch."""
    fields = {k: getattr(dt, k) for k in _SEALED_FIELDS}
    fields["spans"] = tuple((int(a), int(b)) for a, b in fields["spans"])
    e = _entry(dt.completion_key)
    if dt.text != join_spans(e.raw, fields["spans"]):
        raise ValueError("DeliveredText text is not its completion's raw text over its spans")
    if (dt.family, dt.spec_id, dt.provenance, dt.finish_reason) != (e.family, e.spec_id, e.provenance,
                                                                    e.finish_reason):
        raise ValueError("DeliveredText family, spec, provenance or finish_reason differs from its Completion's")
    if e.origin is not None and fields["spans"][0][0] < e.origin.boundary_char + len(e.origin.appended_text):
        raise ValueError("a forced row's span starts before the end of our appended close")
    if _delivered_fields(e, dt.rule_id, outcome(dt.completion_key, dt.rule_id)) != fields:
        raise ValueError("re-running rule D under the text's own rule id and family gives other spans or flags")


def _instance_check(inst: Any) -> None:
    """The ingest issuer's instance check (models.claim_issuer): DeliveredText since step 0, LegacyReadText since
    step 1 (``_check_legacy_against_store``), TraceView since step 2r (``_check_trace_against_store``),
    SensitivityText since step 3 (``_check_sensitivity_against_store``)."""
    if isinstance(inst, _M.DeliveredText):
        _check_delivered_against_store(inst)
        return
    if isinstance(inst, _M.LegacyReadText):
        _check_legacy_against_store(inst)
        return
    if isinstance(inst, _M.TraceView):
        _check_trace_against_store(inst)
        return
    if isinstance(inst, _M.SensitivityText):   # step 3 (22 Oct 2026)
        _check_sensitivity_against_store(inst)
        return
    raise _M.SealError(f"ingest issues no {type(inst).__name__}")


_ISSUER = _M.claim_issuer("ingest", instance_check=_instance_check)


def _delivered_fields(e: _Entry, rule_id: str, o: Outcome) -> dict:
    return {"completion_key": e.key, "spec_id": e.spec_id, "family": e.family,
            "spans": tuple((int(a), int(b)) for a, b in o.spans), "text_sha": sha256_hex(join_spans(e.raw, o.spans)),
            "blocks_removed": o.blocks_removed, "provenance": e.provenance, "mode": o.mode, "rule_id": rule_id,
            "finish_reason": e.finish_reason, "includes_reasoning": False, "cut_at_cap": o.cut_at_cap,
            "cut_at_inner_open": o.cut_at_inner_open}


def deliver(completion_key: str, rule_id: str) -> tuple[Any, str | None]:
    """(DeliveredText, None) or (None, undelivered reason): design 2.3's `deliver` on a registered completion.

    Takes the completion key and the rule id, nothing else (a task keyword raises TypeError): the family, and so a
    task override such as rlcr.close, is read from the key's prompt id, and the rule id must be registered and
    canonical, matched exactly. Step 0 computes it into the sidecar only; no scorer reads it (task brief)."""
    e = _entry(completion_key)
    o = outcome(completion_key, rule_id)
    if not o.delivered:
        return None, o.undelivered_reason
    return _ISSUER.issue(_M.DeliveredText, text=join_spans(e.raw, o.spans), **_delivered_fields(e, rule_id, o)), None


def check_delivered(dt: Any) -> Any:
    """Re-verify a DeliveredText (design 2.0): models' MAC under the live ingest issuer, its shape checks (non-blank,
    never reasoning, a registered rule D id, the family of its prompt id) and this module's instance check against
    the store. SealError on any failure; returns the instance."""
    return _M.verify_seal(dt)


# =========================================================================================== trace views (step 2r, 2.4)
# What the recognition harness reads (design 2.4 and section 6, step 2r; review item 11; CLAUDE.md design rule 2): the
# completion's reasoning and its delivered text as separate typed segments, numbered in text order, with offsets into
# the raw text, under one registered rule D id. The segments are rule D's own offsets (`deliver_spans`), so a view and
# the DeliveredText it carries can never disagree; nothing here is a length, a window or a position cut-off.
def _turn_end(e: _Entry, rule: _M.RuleD) -> int:
    """Where the turn read under `rule` ends, as `deliver_spans` cuts it: the first boundary under D4 cut_at_boundary
    (for a forced row, the continuation's first role line after our appended close), else the end of the raw text."""
    if e.provenance == "forced_close" and e.origin is not None:
        if rule.turn != "cut_at_boundary":
            return len(e.raw)
        s = e.origin.boundary_char + len(e.origin.appended_text)
        nb = next(iter(role_lines(e.raw, e.markers.role_names, s)), None)
        return len(e.raw) if nb is None else nb
    return turn_end_under(e.raw, e.facts, rule)


def trace_segments(completion_key: str, rule_id: str) -> tuple[tuple[str, int, int], ...]:
    """The (kind, start, end) segments of a stored completion's TraceView under a registered rule id, in text order.

    - reasoning: the turn's own block read up to and including its close (from the template's opening, or from the
      model's open marker); the whole turn when that block never closed (OD-1); a forced row's first pass; under
      stray=after_tag, the text before the stray close; each closed block D15 removed from the delivered region; and
      the block OD-1's inner-open cut ended the region at, from its open marker to the region's end;
    - appended: the close a forced_close pass appended (design 9 (e)), never model text;
    - delivered: each span of rule D's DeliveredText.

    Text after the turn's end (an invented turn, cut at its boundary under D4) and whitespace outside every segment lie
    in none. IngestError when the segments overlap, or leave a non-whitespace character of the turn outside them, or
    run past the turn's end: a bug of this function, never a fact of a row (design step 2r, proof 2)."""
    e = _entry(completion_key)
    rule = registered_rule(rule_id)
    o = deliver_spans(e.raw, e.facts, e.markers, rule, e.family, e.finish_reason, e.provenance, e.origin)
    segs = [("reasoning", a, b) for a, b in o.reasoning_spans]
    if o.inner_open is not None:
        segs.append(("reasoning", *o.inner_open))
    if e.provenance == "forced_close" and e.origin is not None:
        b0 = e.origin.boundary_char
        segs.append(("appended", b0, b0 + len(e.origin.appended_text)))
    segs += [("delivered", a, b) for a, b in o.spans]
    segs = sorted(((k, a, b) for k, a, b in segs if b > a), key=lambda x: (x[1], x[2]))
    end, pos = _turn_end(e, rule), 0
    for k, a, b in segs:
        if a < pos:
            raise IngestError(f"trace segments overlap at ({a}, {b}) under {rule_id}", row_id=completion_key)
        if e.raw[pos:a].strip():
            raise IngestError(f"text at ({pos}, {a}) lies in no trace segment under {rule_id}", row_id=completion_key)
        pos = b
    if pos > end or e.raw[pos:end].strip():
        raise IngestError(f"the trace segments end at {pos}, the turn at {end}, under {rule_id}", row_id=completion_key)
    return tuple(segs)


def trace_view(completion_key: str, rule_id: str) -> Any:
    """The sealed TraceView of a registered completion under a registered rule id (design 2.4, step 2r): its
    `trace_segments` numbered 1..n, each with its raw text and sha, and rule D's DeliveredText under the same id (None
    when the row delivers nothing; its reasoning segments are still there). Takes the key and the rule id only; the
    family, and so a task override, is read from the key's prompt id, as `deliver` reads it."""
    e = _entry(completion_key)
    segs = trace_segments(completion_key, rule_id)
    dt, _ = deliver(completion_key, rule_id)
    segments = tuple(_M.TraceSegment(n=n, kind=k, start=a, end=b, text=e.raw[a:b], text_sha=sha256_hex(e.raw[a:b]))
                     for n, (k, a, b) in enumerate(segs, 1))
    return _ISSUER.issue(_M.TraceView, completion_key=e.key, spec_id=e.spec_id, rule_id=rule_id,
                         provenance=e.provenance, segments=segments, stitch_at=e.stitch_at, delivered=dt)


def trace_view_sha(tv: Any) -> str:
    """sha256 of a TraceView's identity (RecognitionVerdict.trace_view_sha, design 2.6): its completion key, spec,
    rule id, provenance, stitch, every segment's number, kind, offsets and text sha, and its delivered text's sha. Two
    views with one sha show a reader the same text in the same segments."""
    payload = {"completion_key": tv.completion_key, "spec_id": tv.spec_id, "rule_id": tv.rule_id,
               "provenance": tv.provenance, "stitch_at": tv.stitch_at,
               "segments": [[s.n, s.kind, s.start, s.end, s.text_sha] for s in tv.segments],
               "delivered_text_sha": None if tv.delivered is None else tv.delivered.text_sha}
    return sha256_hex(_json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _check_trace_against_store(tv: Any) -> None:
    """The TraceView instance check (design 2.0; step 2r): its completion is in the store under its spec, provenance and
    stitch; re-reading that completion under the view's own rule id gives the same segments, each the raw text over its
    offsets; and its DeliveredText is rule D's under that id (re-verified), or absent exactly when rule D delivers
    nothing. ValueError on any mismatch."""
    e = _entry(tv.completion_key)
    if (tv.spec_id, tv.provenance, tv.stitch_at) != (e.spec_id, e.provenance, e.stitch_at):
        raise ValueError("TraceView spec, provenance or stitch differs from its Completion's")
    if tuple((s.kind, s.start, s.end) for s in tv.segments) != trace_segments(tv.completion_key, tv.rule_id):
        raise ValueError("re-reading the completion under the view's own rule id gives other segments")
    if any(s.text != e.raw[s.start:s.end] for s in tv.segments):
        raise ValueError("a TraceView segment is not its completion's raw text over its offsets")
    delivers = outcome(tv.completion_key, tv.rule_id).delivered
    if (tv.delivered is not None) != delivers:
        raise ValueError("the view's delivered text is not rule D's under its rule id")
    if tv.delivered is not None:
        _M.verify_seal(tv.delivered)


# ============================================================================ sensitivity readings (step 3, design 2.3)
# A reading other than rule D is a named SensitivityRule `<name>@<rule D id>` (design 2.3, "Sensitivity rules"; OD-5,
# D1), issued as the sealed SensitivityText only under an id a grant of the decisions note registers, with the record
# that registers it. Step 3 (22 Oct 2026) issues the two readings its judges need:
# - S_whole_turn (D1, section 7; W2.2): the turn, cut under its base's D4 exactly as `deliver_spans` cuts it, whatever
#   the tags, as one span from the turn's first character; mode whole_turn.
# - S_reasoning_incl (D1, W2.1's secondary judge column): the raw completion as one span; mode raw.
# includes_reasoning is read from rule D's own offsets under the base id: the span overlaps a reasoning span, the block
# OD-1's inner-open cut ended the region at, or (a block never closed) the whole turn rule D reads as reasoning. An
# empty completion is no reading (OD-2's empty_output, as rule D writes it). A forced row has no sensitivity reading
# (design 2.7: a cell under a sensitivity id has no budget_forced view). S_rule_F (two section 2 cells, programmatic
# scorers only) is not issued here: no judge reads it.
SENSITIVITY_READINGS: tuple[str, ...] = ("S_whole_turn", "S_reasoning_incl")


def _sensitivity_fields(e: _Entry, rule_id: str) -> tuple[dict | None, str | None]:
    """(the SensitivityText fields but text, owner_decision and mac; None) or (None, the undelivered reason) of a stored
    completion under a registered sensitivity id. IngestError for a reading this module does not issue."""
    name, base = _M.registered_sensitivity(rule_id)
    rule = registered_rule(base.rule_id)
    if name not in SENSITIVITY_READINGS:
        raise IngestError(f"ingest issues no SensitivityText under {name} (step 3 issues {SENSITIVITY_READINGS})",
                          row_id=e.key)
    if e.provenance == "forced_close":
        raise IngestError("a forced row has no sensitivity reading (design 2.7)", row_id=e.key)
    if e.facts["empty"]:
        return None, "empty_output"
    span = (0, _turn_end(e, rule)) if name == "S_whole_turn" else (0, len(e.raw))
    mode = "whole_turn" if name == "S_whole_turn" else "raw"
    o = deliver_spans(e.raw, e.facts, e.markers, rule, e.family, e.finish_reason, e.provenance, e.origin)
    marked = tuple(o.reasoning_spans) + ((o.inner_open,) if o.inner_open is not None else ())
    includes = any(a < span[1] and b > span[0] for a, b in marked)
    return {"completion_key": e.key, "spec_id": e.spec_id, "family": e.family, "spans": (span,),
            "text_sha": sha256_hex(e.raw[span[0]:span[1]]), "provenance": e.provenance, "mode": mode,
            "includes_reasoning": includes, "rule_id": rule_id, "finish_reason": e.finish_reason}, None


def read_sensitivity(completion_key: str, rule_id: str) -> tuple[Any, str | None]:
    """(SensitivityText, None) or (None, undelivered reason): a registered completion read under a registered
    sensitivity id (design 2.3, 2.4; step 3). Takes the key and the rule id only; the family is read from the key's
    prompt id, as `deliver` reads it. The text carries the record whose grant registers the id (D1)."""
    e = _entry(completion_key)
    fields, reason = _sensitivity_fields(e, rule_id)
    if fields is None:
        return None, reason
    a, b = fields["spans"][0]
    return _ISSUER.issue(_M.SensitivityText, text=e.raw[a:b],
                         owner_decision=_M.active_registry().decisions.record_registering(rule_id), **fields), None


def _check_sensitivity_against_store(st: Any) -> None:
    """The SensitivityText instance check: its text is its completion's raw text over its spans, and re-reading the
    stored completion under the text's own sensitivity id gives the same spans, mode, flags and stored facts."""
    e = _entry(st.completion_key)
    fields, _ = _sensitivity_fields(e, st.rule_id)
    if fields is None:
        raise ValueError("re-reading the completion under the text's own sensitivity id gives no reading")
    mine = {k: getattr(st, k) for k in fields}
    mine["spans"] = tuple((int(a), int(b)) for a, b in mine["spans"])
    if mine != fields:
        raise ValueError("re-reading the completion under the text's own sensitivity id gives other spans or flags")
    if st.text != join_spans(e.raw, fields["spans"]):
        raise ValueError("SensitivityText text is not its completion's raw text over its spans")


# ================================================================================ legacy read views (step 1, design 2.4)
# Step 1's sealed text (design 2.4, 2.5a; section 6 step 1): one raw slice under the frozen 14 Oct reading of
# `withholding.typed.legacy`, with the row facts today's bodies read (finish_reason as stored; delivered_answer's flag
# on view delivered_20261014 only). A stored row is first classified (`classify_stored_row(..., keep=True)`), then
# `register_legacy` reads the frozen reading off the row once and keeps its offsets beside the completion; the
# LegacyReadText instance check holds every issued text to that reading. Removed from every scorer signature at
# step 2a.
#
# A binding names what an entry reads (design 2.4's row-fact table, "which reading the frozen rule applies"): the
# three views themselves, and the two SCORERS_DELIVERED bindings, for which the issuer picks the view from the frozen
# ENTRIES so that the wrapper branches on the view instead of calling thinking_rule:
#   delivered_else_answer_or_output  ReliableMath v1.2 and MATH-500 v1.1: delivered_20261014 where the frozen rule
#                                    covers the row (thinking_rule is not None), else answer_or_output (v1.1 / v1);
#   rlcr_delivered_wrapper           RLCR v2.1: whole_output whenever the wrapper scores (the frozen rule does not cover
#                                    the row, or the row delivers), delivered_20261014 only on undelivered rows
#                                    (design 2.4, Revision 3; re-review 2 item 6).
LEGACY_BINDINGS: tuple[str, ...] = ("answer_or_output", "whole_output", "delivered_20261014",
                                    "delivered_else_answer_or_output", "rlcr_delivered_wrapper")


@dataclass(frozen=True)
class _LegacyReading:
    """The frozen 14 Oct reading of one stored row: each view's (start, end) on the raw text, delivered_answer's flag,
    whether the frozen rule covers the row, and finish_reason as stored (None where the row has no such key)."""

    views: tuple[tuple[str, int, int], ...]
    delivered: bool
    rule_applies: bool
    finish_reason: str | None

    def span(self, view: str) -> tuple[int, int]:
        for v, s, e in self.views:
            if v == view:
                return s, e
        raise KeyError(view)


_LEGACY: dict[str, _LegacyReading] = {}


def _suffix_span(raw: str, text: str, view: str, key: str) -> tuple[int, int]:
    """(start, end) of a legacy reading on the raw text. Every legacy reading is a suffix of the output (the text after
    the last close, the whole output, or nothing), so the slice is located by its length and then compared."""
    start = len(raw) - len(text)
    if start < 0 or raw[start:] != text:
        raise IngestError(f"the legacy {view} reading is not a slice of the completion's raw text", row_id=key)
    return start, len(raw)


def register_legacy(completion_key: str, row: Mapping[str, Any]) -> None:
    """Read the frozen 14 Oct reading (`withholding.typed.legacy`) off a stored output row whose completion is in the
    store, and keep its offsets beside it (design 2.4). The row's `output` must be the completion's raw text and its
    finish_reason the completion's (a missing key is not_recorded). The three views are what today's bodies read:
    answer_or_output = `r.get("answer") or r.get("output", "")`; whole_output = the output; delivered_20261014 =
    `legacy.delivered_answer(r)`, with its delivered flag and whether `legacy.thinking_rule(r)` covers the row.
    IngestError on any mismatch, or when the same key is registered again with another reading."""
    from withholding.typed import legacy as L

    e = _entry(completion_key)
    r = dict(row)
    if r.get("output") != e.raw:
        raise IngestError("the row's output is not its completion's raw text", row_id=completion_key)
    fr = r.get("finish_reason")
    if (NOT_RECORDED if fr is None else fr) != e.finish_reason:
        raise IngestError("the row's finish_reason is not its completion's", row_id=completion_key)
    text, delivered = L.delivered_answer(r)
    readings = (("answer_or_output", r.get("answer") or r.get("output", "")), ("whole_output", e.raw),
                ("delivered_20261014", text))
    rec = _LegacyReading(views=tuple((v, *_suffix_span(e.raw, t, v, completion_key)) for v, t in readings),
                         delivered=bool(delivered), rule_applies=L.thinking_rule(r) is not None, finish_reason=fr)
    old = _LEGACY.get(completion_key)
    if old is not None and old != rec:
        raise IngestError("legacy reading registered again with other facts", row_id=completion_key)
    _LEGACY[completion_key] = rec


def _legacy(completion_key: str) -> _LegacyReading:
    try:
        return _LEGACY[completion_key]
    except (KeyError, TypeError):
        raise IngestError("no legacy reading for this completion (register_legacy it first)",
                          row_id=str(completion_key)) from None


def legacy_view(completion_key: str, binding: str) -> str:
    """The view the issuer gives an entry of this binding on this completion (LEGACY_BINDINGS)."""
    rec = _legacy(completion_key)
    if binding in _M.LEGACY_VIEWS:
        return binding
    if binding == "delivered_else_answer_or_output":
        return "delivered_20261014" if rec.rule_applies else "answer_or_output"
    if binding == "rlcr_delivered_wrapper":
        return "delivered_20261014" if (rec.rule_applies and not rec.delivered) else "whole_output"
    raise IngestError(f"unknown legacy binding {binding!r}", row_id=completion_key)


def read_legacy(completion_key: str, binding: str) -> Any:
    """The sealed LegacyReadText an entry of `binding` reads on a registered completion (design 2.4): the view
    `legacy_view` picks, its raw slice, finish_reason as stored, and on view delivered_20261014 the frozen delivered
    flag. Takes the completion key and the binding, nothing else."""
    e = _entry(completion_key)
    rec = _legacy(completion_key)
    view = legacy_view(completion_key, binding)
    s, t = rec.span(view)
    text = e.raw[s:t]
    return _ISSUER.issue(_M.LegacyReadText, text=text, completion_key=completion_key, spec_id=e.spec_id, start=s,
                         end=t, text_sha=sha256_hex(text), view=view, finish_reason=rec.finish_reason,
                         delivered=rec.delivered if view == "delivered_20261014" else None)


def _check_legacy_against_store(lt: Any) -> None:
    """The LegacyReadText instance check (design 2.0): the text is its completion's raw text over its offsets, the
    spec is the completion's, and the offsets, finish_reason and delivered flag are the registered frozen reading's for
    its view. ValueError on any mismatch."""
    e = _entry(lt.completion_key)
    rec = _legacy(lt.completion_key)
    if lt.spec_id != e.spec_id:
        raise ValueError("LegacyReadText spec differs from its Completion's")
    if lt.text != e.raw[lt.start:lt.end]:
        raise ValueError("LegacyReadText text is not its completion's raw text over its offsets")
    if (lt.start, lt.end) != rec.span(lt.view):
        raise ValueError(f"LegacyReadText offsets are not the frozen {lt.view} reading")
    if lt.finish_reason != rec.finish_reason:
        raise ValueError("LegacyReadText finish_reason is not the row's as stored")
    if lt.view == "delivered_20261014" and lt.delivered != rec.delivered:
        raise ValueError("LegacyReadText delivered is not the frozen delivered_answer flag")


# ======================================================================================================= Completion
def classify(*, run: _M.RunIdentity, prompt: Any, sample: int, raw: str, spec: Any,
             finish_reason: str, stop_reason: Any = NOT_RECORDED, prompt_tokens: Any = NOT_RECORDED,
             completion_tokens: Any = NOT_RECORDED, prompt_token_hash: str = NOT_RECORDED,
             prompt_token_hash_source: str = NOT_RECORDED, completion_token_hash: str | None = None,
             chat_kwargs: Mapping[str, Any] | None = None, provenance: str = "first_pass", origin: Any = None,
             rule_id: str = STEP_2A_RULE_ID, renderer_check: Any = None) -> Any:
    """Build the typed Completion of one raw completion (design 2.3) and keep it in the store.

    The facts are computed from the text under the spec's markers and role names; the think_state is derived from
    them; the delivery fields (delivered, delivery_mode, undelivered_reason, reasoning_spans) are rule D's under
    `rule_id` (default: step 2a's id, the first registered). The key is `<run.run_id>/<prompt.prompt_sha>/<prompt.id>#
    <sample>` (Revision 4), and the generation config id is the run's."""
    rule = registered_rule(rule_id)
    key = completion_key(run.run_id, prompt.id, sample, prompt_sha=prompt.prompt_sha)
    facts = register(key=key, run=run, raw=raw, spec=spec, finish_reason=finish_reason, prompt=prompt,
                     provenance=provenance, origin=origin, chat_kwargs=chat_kwargs)
    state = derive_state(facts, finish_reason)
    e = _STORE[key]
    o = deliver_spans(e.raw, e.facts, e.markers, rule, e.family, e.finish_reason, e.provenance, e.origin)
    dt = deliver(key, rule.rule_id)[0] if o.delivered else None
    return _M.Completion(
        key=key, run_id=run.run_id, run=run, spec_id=spec.spec_id, template_sha12=spec.template_sha12,
        generation_config_id=run.generation_config_id, prompt_sha=prompt.prompt_sha, prompt_token_hash=prompt_token_hash,
        prompt_token_hash_source=prompt_token_hash_source, completion_token_hash=completion_token_hash,
        raw_sha=e.raw_sha, finish_reason=finish_reason, stop_reason=stop_reason, prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens, facts=_M.ThinkFacts(**facts), think_state=state,
        reasoning_spans=o.reasoning_spans, origin=origin, delivered=dt, delivery_mode=o.mode,
        undelivered_reason=o.undelivered_reason, renderer_check=renderer_check, provenance=provenance)


def delivery_record(completion_key: str, rule_id: str) -> dict:
    """One rule id's delivery for the sidecar: offsets, mode or reason, D15 and cut flags, the delivered sha. No text."""
    o = outcome(completion_key, rule_id)
    e = _STORE[completion_key]
    return {"mode": o.mode, "reason": o.undelivered_reason, "spans": [list(s) for s in o.spans],
            "reasoning_spans": [list(s) for s in o.reasoning_spans], "blocks_removed": o.blocks_removed,
            "cut_at_inner_open": o.cut_at_inner_open, "cut_at_cap": o.cut_at_cap,
            "delivered_sha": sha256_hex(join_spans(e.raw, o.spans)) if o.delivered else None}


def sidecar_record(completion: Any, rule_ids: Sequence[str] = REGISTERED_RULE_IDS,
                   delivery: Mapping[str, dict] | None = None, **extra: Any) -> dict:
    """The backfill sidecar line of one Completion (design 6 step 0): keys, spec id, facts, state, offsets and hashes
    for every registered rule id, never text. `delivery` passes records already computed with delivery_record;
    `extra` adds row-level facts (file and line, tool_render, ...). The draw and the same-completion id (design 2.3,
    Revision 4) let a reader tell a copy from another completion without the text."""
    k = split_key(completion.key)
    out = {"key": completion.key, "prompt_id": k.prompt_id, "sample": k.sample, "run_id": completion.run_id,
           "draw": completion.draw, "same_completion_id": completion.same_completion_id,
           "spec_id": completion.spec_id, "template_sha12": completion.template_sha12,
           "generation_config_id": completion.generation_config_id, "prompt_sha": completion.prompt_sha,
           "raw_sha": completion.raw_sha, "finish_reason": completion.finish_reason,
           "think_state": completion.think_state, "facts": completion.facts.model_dump(mode="json"),
           "delivery": dict(delivery) if delivery is not None else {rid: delivery_record(completion.key, rid)
                                                                    for rid in rule_ids}}
    out.update(extra)
    return out


# ================================================================== the runner's ingestion stamp (step 6, plan W7.2)
# Design section 6, step 6 ("In the runner (W7.2)"), built 25 Oct 2026. Every output row `withholding/run/modal_vllm.py`
# writes from then on carries, beside prompt_token_hash, think_forced and vllm_version, vLLM's stop_reason and the
# stamp below: the registry spec id the run resolved to before it started, and the think-tag accounting of the raw text
# under that spec. `runner_stamp` computes the accounting with `compute_facts`, the same facts every reader computes.
# `classify_stored_row` refuses a row whose stamp disagrees with its own reading. A reader types a row through its step 0
# sidecar line, or, where there is none, through these fields (`withholding.typed.dispatch.DirectoryDispatch`); a
# row with neither is refused. From the step 6 fix round (25 Oct 2026; design 9 (b)) the runner also writes the ids vLLM
# sampled and their hash (`completion_token_ids`, `completion_token_hash`); `classify_stored_row` checks the two against
# each other and against completion_tokens, and the Completion carries the hash.
RUNNER_STAMP_FIELDS: tuple[str, ...] = ("spec_id", "think_opened_by", "think_closed", "think_close_count",
                                        "empty_output", "invented_turn")
RUNNER_ROW_FIELDS: tuple[str, ...] = RUNNER_STAMP_FIELDS + ("prompt_token_hash", "think_forced", "vllm_version",
                                                            "stop_reason", "completion_token_ids",
                                                            "completion_token_hash")
_RUNNER_NULLABLE = frozenset({"think_opened_by", "stop_reason"})   # None is a value: no opener; EOS or the cap


def stamp_of_facts(spec_id: str, facts: Mapping[str, Any]) -> dict:
    """The runner's ingestion stamp of a completion with these ThinkFacts under spec `spec_id`: who opened the think
    block (`template`, `model`, or None), whether the turn holds a close marker and how many (the closes rule D reads,
    up to the turn's first boundary), the empty flag (no non-whitespace character) and the invented-turn flag (a role
    line with text before it)."""
    n = facts["n_close_in_turn"]
    return {"spec_id": spec_id, "think_opened_by": facts["opened_by"], "think_closed": n > 0, "think_close_count": n,
            "empty_output": facts["empty"], "invented_turn": facts["has_turn_boundary"]}


def runner_stamp(raw: str, spec: Any) -> dict:
    """The ingestion stamp the runner appends to an output row with raw text `raw`, rendered under TemplateSpec
    `spec` (design section 6, step 6): `stamp_of_facts` over `compute_facts` under the spec's markers and role names."""
    return stamp_of_facts(spec.spec_id, compute_facts(raw, markers_of(spec)))


def missing_runner_fields(row: Mapping[str, Any]) -> tuple[str, ...]:
    """The runner's fields (RUNNER_ROW_FIELDS) a stored output row lacks: absent, or None where None is no value (every
    field but think_opened_by and stop_reason). () for a row the runner of 25 Oct 2026 wrote and stamped."""
    return tuple(k for k in RUNNER_ROW_FIELDS if k not in row or (row[k] is None and k not in _RUNNER_NULLABLE))


def stored_completion_hash(mirror: Any) -> str | None:
    """The completion_token_hash of a stored output row (`adapters.StoredOutputRow`): None when it carries neither the
    runner's completion ids nor their hash (every row written before 25 Oct 2026's step 6 fix round). IngestError
    when it carries one without the other, when the hash is not its ids' (`adapters.completion_token_hash`), or when
    the ids are not completion_tokens long."""
    from withholding.typed import adapters as A

    ids, h = mirror.completion_token_ids, mirror.completion_token_hash
    if ids is None and h is None:
        return None
    if ids is None or h is None:
        raise IngestError("the runner writes completion_token_ids and completion_token_hash together; the row holds "
                          f"only {'the hash' if ids is None else 'the ids'}")
    if A.completion_token_hash(ids) != h:
        raise IngestError(f"completion_token_hash {h} is not the hash of the row's completion_token_ids "
                          f"({A.completion_token_hash(ids)})")
    if mirror.completion_tokens is not None and len(ids) != mirror.completion_tokens:
        raise IngestError(f"the row holds {len(ids)} completion ids, not its completion_tokens "
                          f"({mirror.completion_tokens})")
    return h


def _check_runner_stamp(mirror: Any, spec: Any, facts: Mapping[str, Any]) -> None:
    """IngestError when a stamp field the row carries differs from the typed reading (type and value)."""
    want = stamp_of_facts(spec.spec_id, facts)
    bad = {k: (getattr(mirror, k), want[k]) for k in RUNNER_STAMP_FIELDS if k in mirror.model_fields_set
           and (type(getattr(mirror, k)), getattr(mirror, k)) != (type(want[k]), want[k])}
    if bad:
        raise IngestError("the runner's ingestion stamp disagrees with the typed reading (stored, typed): "
                          + ", ".join(f"{k} {v[0]!r} vs {v[1]!r}" for k, v in bad.items()))


# ================================================================================================ stored output rows
def _resolve_spec(registry: Any, row: Mapping[str, Any]) -> Any:
    """The TemplateSpec a stored row was rendered under, from the registry (design section 3, "ingest, stored rows").
    The registry module is built beside this one; its row resolver is looked up by the names it may carry, and a
    registry with none of them is an IngestError that names what is missing."""
    for name in ("spec_for_row", "resolve_row", "spec_for", "resolve", "lookup_row", "lookup", "match_row"):
        fn = getattr(registry, name, None)
        if callable(fn):
            got = fn(row)
            spec = getattr(got, "spec", got) if got is not None and not hasattr(got, "spec_id") else got
            if spec is None or not hasattr(spec, "spec_id"):
                raise IngestError(f"no TemplateSpec matches the row key (registry.{name})", row_id=row.get("id"))
            return spec
    raise IngestError("the registry exposes no row resolver (spec_for_row)", row_id=row.get("id"))


def classify_stored_row(row: Mapping[str, Any], *, draw: str, registry: Any = None, spec: Any = None,
                        where: str | None = None, item_status: Mapping[str, str] | None = None,
                        prompt_tokenizer: Callable[..., tuple[Sequence[int], str]] | None = None,
                        rule_ids: Sequence[str] = REGISTERED_RULE_IDS, want_oracle: bool = False,
                        keep: bool = True, ext_cap_first_pass: int | None = None) -> tuple[Any, dict]:
    """Type one stored output row: (Completion, extras). The backfill's entry point (design 6 step 0, section 3).

    `draw` is the output file the row was read from, its real path relative to results/ (design 2.3, Revision 4): it
    enters the run id, so the same (prompt, sample) in two files gets two keys. The row is read through
    `adapters.StoredOutputRow` (unknown keys refused), its prompt through
    `adapters.prompt_record` and its generation through `adapters.generation_config`; the spec comes from `spec` or
    the registry; the Completion is read under step 2a's id. `extras` holds what the backfill report counts:
    row_key (the frozen 14 Oct key), tool_render, reasoning_channel, prompt_parity, round_trip (the runner's stored
    answer and reasoning rebuilt from the raw text), d16 (ImpossibleBench: the frozen 14 Oct reading against rule D
    under step 2a's id), delivery per registered rule id, the sidecar line, and on request the oracle input.
    `prompt_tokenizer(spec, prompt, chat_kwargs) -> (prompt ids, template text)` (the registry's `prompt_tokenizer`)
    turns on the prompt-length parity check and the offline prompt token hash (`recomputed_offline`); without it
    parity is not_checked and the hash not_recorded.
    `keep=False` drops the row from the store once its extras are computed (the backfill: the store then never holds a
    directory's texts; the returned Completion's sealed text can no longer be re-verified). Raises IngestError, or
    its subclass, with `where`, for a row the layer refuses.
    `ext_cap_first_pass` is the merged twin's stored `cap_first_pass` of a row read from an extended pass's own
    `outputs_ext.jsonl` (D17: such a row is a re-draw by the file name; `adapters.generation_config`), and nothing
    for any other row. A row the runner stamped (step 6: RUNNER_STAMP_FIELDS) is refused when its stamp differs from
    this reading, and a row that carries the runner's completion ids when they disagree with their hash or with
    completion_tokens (`stored_completion_hash`); the Completion carries that hash."""
    from withholding.typed import adapters as A
    from withholding.typed import legacy as L

    try:
        mirror = A.StoredOutputRow.from_row(row)
        prompt = A.prompt_record(mirror, item_status=item_status)
        spec = spec if spec is not None else _resolve_spec(registry, row)
        gen = A.generation_config(mirror, spec, draw=draw, prompt_sha=prompt.prompt_sha,
                                  ext_cap_first_pass=ext_cap_first_pass)
        gen_id = gen.generation_config_id if gen is not None else NOT_RECORDED
        provenance = gen.provenance if gen is not None else "first_pass"
        origin = None
        if provenance == "redraw":  # audit 9: the first pass this row re-draws was cut at cap_first_pass
            first_cap = mirror.cap_first_pass if ext_cap_first_pass is None else ext_cap_first_pass
            origin = _M.Redraw(first_pass_key=gen.replaces, cut_reason="length", first_pass_max_tokens=first_cap)
        run = run_identity(model=mirror.model, subfolder=mirror.subfolder, revision=mirror.revision,
                           spec_id=spec.spec_id, generation_config_id=gen_id, draw=draw)
        parity: dict = {"status": "not_checked"}
        p_hash, p_source = NOT_RECORDED, NOT_RECORDED
        if prompt_tokenizer is not None:
            ids, template_text = prompt_tokenizer(spec, prompt, mirror.chat_kwargs)
            stored = mirror.prompt_tokens
            parity = {"status": "not_recorded" if stored is None else ("equal" if len(ids) == stored else "differs"),
                      "offline": len(ids), "stored": stored}
            p_hash, p_source = A.prompt_token_hash(template_text, mirror.chat_kwargs or {}, ids), "recomputed_offline"
        c = classify(run=run, prompt=prompt, sample=mirror.sample_or_default, raw=mirror.output, spec=spec,
                     finish_reason=mirror.finish_reason or NOT_RECORDED,
                     stop_reason=mirror.stop_reason_or_not_recorded,
                     prompt_tokens=NOT_RECORDED if mirror.prompt_tokens is None else mirror.prompt_tokens,
                     completion_tokens=NOT_RECORDED if mirror.completion_tokens is None else mirror.completion_tokens,
                     prompt_token_hash=p_hash, prompt_token_hash_source=p_source,
                     completion_token_hash=stored_completion_hash(mirror),
                     chat_kwargs=mirror.chat_kwargs, provenance=provenance, origin=origin)
        try:
            _check_runner_stamp(mirror, spec, c.facts.model_dump())
        except IngestError:
            forget([c.key])
            raise
    except IngestError as e:
        raise type(e)(e.reason, where=where, row_id=row.get("id")) from e
    except (ValueError, TypeError, KeyError) as e:  # a ValidationError is a ValueError
        raise IngestError(f"{type(e).__name__}: {e}", where=where, row_id=row.get("id")) from e
    round_trip = {}
    rebuilt_reasoning, rebuilt_answer = L.runner_split(mirror.output)
    for fld, rebuilt in (("answer", rebuilt_answer), ("reasoning", rebuilt_reasoning)):
        if fld in mirror.model_fields_set:
            round_trip[fld] = "equal" if getattr(mirror, fld) == rebuilt else "differs"
    delivery = {rid: delivery_record(c.key, rid) for rid in rule_ids}
    extras: dict = {"row_key": list(L.row_key(dict(row))), "tool_render": prompt.tool_render,
                    "reasoning_channel": spec.reasoning_channel, "prompt_parity": parity, "round_trip": round_trip,
                    "delivery": delivery}
    if prompt.family == "impossible_lcb":  # D16's guard, as a committed check over every ImpossibleBench row
        old_text, old_ok = L.delivered_answer(dict(row))
        new = delivery[STEP_2A_RULE_ID]
        new_text = join_spans(mirror.output, new["spans"]) if new["reason"] is None else None
        same = (old_ok and new_text is not None and old_text == new_text) or (not old_ok and new_text is None)
        extras["d16"] = "same" if same else "differs"
    replaces = {"replaces": gen.replaces} if gen is not None and gen.replaces is not None else {}
    # the runner's completion hash, on the line of a row that carries it (step 6 fix round); no stored row does, so
    # the backfill's lines are unchanged
    ids = {"completion_token_hash": c.completion_token_hash} if c.completion_token_hash is not None else {}
    extras["sidecar"] = sidecar_record(c, rule_ids, delivery, where=where, tool_render=prompt.tool_render,
                                       generation_provenance=provenance, **replaces, **ids)
    if want_oracle:
        extras["oracle_request"] = {"key": c.key, "spec_id": spec.spec_id, "raw": mirror.output,
                                    "think_open_in_prompt": spec.think_open_in_prompt,
                                    "open_marker": spec.open_marker, "close_marker": spec.close_marker}
    if not keep:
        forget([c.key])
    return c, extras

