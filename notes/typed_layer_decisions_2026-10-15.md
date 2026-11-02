<!-- Public copy, 2 Nov 2026: this file ships only because the typed registry reads it at import. The owner's verbatim chat lines, Modal workspace names and balances are withheld from this copy; the registry pins in withholding/typed/owner_decisions.pins.json were recomputed for it. The private original is unchanged. -->
# Typed layer decisions, 15 October 2026

Owner: Ahmed Bakr. This note is the record the OwnerDecision registry of the typed ingestion layer reads (`notes/typed_ingestion_design_2026-10-15.md`, section 2.8). It holds one dated record per decision: OD-1 to OD-5, the owner's standing decisions of 15 Oct, and D1 to D16, the design's recommendations (its section 7), adopted under the owner's 15 Oct delegation; D15 and D16 were added by the design's Revision 3. Each record gives the scope, the options, the adopted option, the reason, the lines of the design that depend on it and its registry scope. Design lines are cited as `notes/typed_ingestion_design_2026-10-15.md:N` at its Revision 2 unless a record says Revision 3; later edits to the design can move them, so each citation also names what sits there.

How the registry reads this note: each record's heading is its id, and the heading occurs once in this file. At step 0 the registry stores, per record, the sha256 of the text under the heading (`SectionCitation`, design 2.8). A record edited after that fails the registry load until it is re-pinned (Confirmation, below). A moved line changes nothing.

Registry scopes (Revision 3; re-review 2 item 1). Each record ends with a **Registry scope** entry. It is either "none", with the reason, or one or more fenced `text` blocks. Each block is one grant: the exact strings the loader reads, one per line, and nothing else. The blocks sit under the record's heading, so its content sha covers them. The loader reads scopes only from here, never from the design's tables or from prose. The string kinds and what checks each are defined in the design's 2.8:
- `rule:<full rule id>` registers a read rule: a rule D id, or a sensitivity id `<name>@<rule D id>`;
- `reason:<undelivered reason>` registers a reason a dispatcher may write;
- `mixed_modes:<sensitivity id>` lets that rule's cells and same-rule deltas read reasoning on some rows and not on others;
- `cell:<metric_id>@<coordinates>` names a cell a sensitivity rule of the same grant may fill; `<coordinates>` is the canonical `key=value` list sorted by key and joined by commas, or `any` for every coordinate of that metric;
- `delta:<rule id a>~<rule id b>` lets a DeltaCell pair two different read rules; no record holds one, so every cross-rule delta is refused;
- `view:<name>` registers a censoring view; `reward_rule:<rule id>` the read rule a reward adapter stamps; `scorer:<name>@<version>~<rule id>` a scorer stamp taken under another read rule and registered under this one too.

## Authority and confirmation

- **OD-1 to OD-5** are the owner's decisions of 15 Oct as given in the brief to the design and relayed again in the orchestrating session's Revise 2 brief. OD-1 and OD-4 are also written for the C reward in amendment 4 section 7, "The C reward (owner's decision, 15 Oct; pending)" (`notes/prereg_c_full_amendment4_2026-10-15.md:389-390`, committed in f179f6c). OD-2, OD-3 and OD-5 were on no file before this note.
- **D1 to D14** are adopted under the owner's 15 Oct delegation of the recommendations, "I agree with all of your recommendations overall", as relayed to this session by the orchestrating session's Revise 2 brief. Those words are not on file elsewhere in the repo (a search of `notes/` on 15 Oct found none).
- **D15 and D16** are recommendations of the design's Revision 3 (15 Oct), adopted under the same delegation as relayed again by the orchestrating session's Revise 3 brief: "recommendations are adopted as decisions, recorded by id with date, scope, options, adopted option and reason; the owner will add a confirmation line in his own words". D15's adopted option is the one that brief set.
- **Who wrote this note.** Design sessions (Revision 2, and Revision 3 for D15, D16, the registry scopes and the Confirmation block), on 15 Oct. D11's adopted option is "a short dated decisions note written or signed by the owner", so this note needs the owner's confirmation line below before the registry loads (design 2.8).
- **Applications this note records** beyond the design's text, for the owner to confirm with the rest: the inner-open cut keeps the text before the open (OD-1), and region pairs are counted, not declared (D13). They are listed again under Confirmation.

## Confirmation

**Status: signed 2026-10-17** (the owner's line is at the end of this section; the text above it is the design session's, kept as written). Before 17 Oct the section read UNSIGNED and the registry loaded unsigned (design 2.8).

What the loader accepts: a line in this section that begins `Confirmed: Ahmed Bakr, ` and then a date written YYYY-MM-DD. The rest of the line is his own words. A line that begins any other way, the placeholder below included, is not a confirmation. The first load after his line pins every record's content sha together with the sha of this section. A record edited after that fails the load until he adds a new dated line here; only then is it pinned again.

What the line confirms: every record OD-1 to OD-5 and D1 to D16 as written, and the two applications listed below. A record he wants changed is edited in place, with its date, before his line.

The text to add, in his own words. This is a placeholder, UNSIGNED and not the owner's; the loader ignores it because the line does not begin with `Confirmed:`:

```text
UNSIGNED PLACEHOLDER (replace with your own words): Confirmed: Ahmed Bakr, YYYY-MM-DD. <that you have read OD-1 to OD-5 and D1 to D16 as recorded in this note and confirm them; whether you confirm application 1 and application 2 below; any record you want changed first, by id>
```

Confirmed: Ahmed Bakr, 2026-10-17. "I agree with all of the other decisions" (his words, chat of 17 October 2026, replying to the twelve-item list of what waited on him; item 1 of that list was this line: confirm OD-1 to OD-5 and D1 to D16 as recorded, and both applications, the inner-open cut keeping the text before the open and region pairs counted rather than declared; the same reply adopted the recommendations of items 4, 5, 8 and 10 of that list, recorded today as D17 to D21). Written into this file by the session the same day under his standing delegation (Authority, above); no record was changed first.
Confirmed: Ahmed Bakr, 2026-10-18. "okay I confirm yeah" (his words, chat of 18 October 2026, answering the proposed text "Confirmed D22: the reader study reads the pinned legacy numbered view and takes the class-level construct; traces whose typed view differs under step 2r are re-read under the typed view"; this line confirms D22 as recorded below and re-pins OD-1 to OD-5 and D1 to D21 unchanged). Written into this file by the session the same day under his standing delegation.
Confirmed: Ahmed Bakr, 2026-10-21. "go with the recommendation and start the runs, we have enough credits" (his words, chat of 21 October 2026, as the orchestrating session relayed them, answering the (i)/(ii) question on step 2r's pending item (3): (i) keep the line "The text above stopped at the generation length limit." on a no-tags turn cut at the generation cap in the typed reader view, or (ii), the recommendation, no closing note, so readers read the cut text as delivered, consistent with D18; this line confirms D23 as recorded below, option (ii), and re-pins OD-1 to OD-5 and D1 to D22 unchanged). Written into this file by the session the same day under his standing delegation.
Confirmed: Ahmed Bakr, 2026-10-23. "we still have [balance withheld from this public copy] on the modal account you can run whatever will be within those limits and boundaries! and for the other parts espacially for the extentions and runs that is needed, we need to do whatever will be best for the paper work and needed runs, and for the 1.3 GB of runner-row copies go with the best option" (his words, chat of 23 October 2026, as the orchestrating session relayed them, after the step 3 Llama batch ran on the Modal workspace of that batch and its fix rounds reported the label-blind echo on the no-claim stratum and the two-axis draft of D24 (design Revisions 23 and 24): a go for GPU runs on that workspace within the dashboard balance of that day, and a delegation on the extensions and runs the records left owner-pending; this line enters D24 and D25 as recorded below, both adopted under that delegation (written by the session; he did not read their text first), and re-pins OD-1 to OD-5 and D1 to D23 unchanged). Written into this file by the session the same day under his standing delegation.

Applications awaiting his confirmation:
1. **OD-1, the inner-open cut.** A block opened inside the delivered region and never closed ends the region at its open marker, and the text before the marker is delivered (OD-1's record gives the options (i) to (iii)). Under step 2a's parameters it touches 1,140 stored rows: 1,015 become no_answer and 125 keep a shorter text (design 2.3).
2. **D13, region pairs.** In a DeltaCell, an after-close text paired with a whole-turn text under one rule D id is counted and printed beside the censoring pairs, not refused (D13's record). Under step 2a's parameters only the 13 Cascade no_think directories deliver both modes; after step 2c only `cascade/no_think/base` does (10 rows).

D15 and D16 are records adopted under the delegation, not applications of other records; the line confirms them with the rest.

## Index

| id | adopted | authority | gates |
|---|---|---|---|
| OD-1 | rule D for every primary cell in every lineage; the inner-open cut | owner's decision | step 2a and every step after it; the C reward |
| OD-2 | an empty completion delivers nothing | owner's decision | step 2a; every dispatcher |
| OD-3 | scorer version, rule date and censoring view on every number; the three views | owner's decision | step 4; every diff table |
| OD-4 | one scorer for training and evaluation | owner's decision | step 5; C's report tables |
| OD-5 | base_think read like its runs; other readings only as named sensitivity columns | owner's decision | step 2a, step 3 and step 4 for section 7 |
| D1 | S_whole_turn (section 7), S_reasoning_incl (W2.1), S_rule_F (two section 2 cells) | adopted recommendation | step 3 sensitivity calls; step 4 sensitivity cells |
| D2 | close: first by default, last for RLCR | adopted recommendation | step 2b |
| D3 | a close with no opener: content | adopted recommendation | step 2c |
| D4 | invented turns: cut at the first boundary | adopted recommendation | step 2d |
| D5 | Gemini cache records without finish_reason: the content rule | adopted recommendation | step 3 |
| D6 | renderers as an offline oracle only | adopted recommendation | step 0's oracle |
| D7 | quote a point only when the verdict label holds at both ends of the worst-case bracket | adopted recommendation | step 4's RESULTS rules |
| D8 | step 3 at about USD 15 to 17, inside the plan's standing rule | adopted recommendation | step 3 |
| D9 | the amendment 4 reward line as drafted | adopted recommendation | step 5 |
| D10 | label-blind judge on the no-claim stratum first | adopted recommendation | part of step 3 |
| D11 | this note | adopted recommendation | step 0's registry load |
| D12 | step 2r after the concurrent session commits | adopted recommendation | step 2r |
| D13 | censoring and region pairs counted; reading pairs refused unless declared | adopted recommendation | step 4b |
| D14 | ImpossibleBench content rules | adopted recommendation | step 2e |
| D15 | a closed block inside the delivered region is reasoning; the text before its open and after its close is delivered | adopted recommendation (Revision 3) | steps 2b, 2c and 3; every rule D id |
| D16 | ImpossibleBench v3 registered under step 2a's rule id too, with a per-row equality guard | adopted recommendation (Revision 3) | step 2a; step 0's taken-stamp list |
| D17 | the outputs_ext rows typed redraw by file name; the sidecars patched for those rows only | adopted recommendation (17 Oct) | step 0's completion key typing |
| D18 | censored means undelivered under the table's rule D id, for every metric; a point only when both ends and each end's interval give the label | adopted recommendation (17 Oct) | step 4's MetricSpecs and RESULTS rules; every bracket |
| D19 | section 7 lineages with no delivered rows: no number in the primary cell; S_whole_turn beside it with D1's id | adopted recommendation (17 Oct) | step 4 for section 7; the RL-Zero report |
| D20 | the XSTest grade re-parse of Batch A applied, under a new version | adopted recommendation (17 Oct) | the XSTest judged parse; step 3 |
| D21 | C's reward on the post-2d rule D id | adopted recommendation (17 Oct) | step 5; amendment 4 section 7 |
| D22 | adopted | owner's decision (18 Oct) | the reader study's input view and construct; the cloud seat's export gate; step 2r reconciliation |
| D23 | (ii): no closing note on a no-tags turn cut at the generation cap, in the typed reader view | adopted on the owner's word (21 Oct) | the typed reader view (`blind_text_typed`); D22's reconciliation recomputed; the reader study's rr2 (amendment 14) |
| D24 | (a) with the template-word replies in: one-word replies that name no option their item lists, the judge's template words not excluded (4,241 rows) | adopted under the owner's delegation (23 Oct) | D10's echo diagnostic and the label-blind column (design 2.7); step 4's typed cells |
| D25 | (a): the label-blind judge on every AbstentionBench row delivered under the primary rule id, as the arm `label_blind_all` | adopted under the owner's go and delegation (23 Oct) | step 3's label-blind run on the Modal workspace of the step 3 batch; the label-blind column per cell and the per-cell echo table |

## OD-1

- **Date:** 2026-10-15. **Decided by:** Ahmed Bakr. **Authority:** the owner's decision (see Authority); for the C reward also `notes/prereg_c_full_amendment4_2026-10-15.md:389-390`.
- **Decision:** rule D everywhere: a think block left unclosed delivers nothing.
- **Scope:** every primary cell in every lineage reads a registered rule D id (`D@2026-10-15|close=..|stray=..|turn=..`, with its task overrides); the undelivered reasons `unclosed_block` and `empty_before_inner_open`; the C reward, with OD-4.
- **Options:** (a) rule D, in every spec, with no exception; (b) a per-lineage trained channel (after the close, else the whole output: R10's channel, the first draft's D1 recommendation for RL-Zero and base_think); (c) rule F, unclosed stop-finished rows read as the turn (audit 1).
- **Adopted:** (a).
- **Reason:** one reading for every lineage removes the two cases where the reading decided a result: audit 1 (one rule decides two Cascade claims) and audit 11 (base_think read two ways). Text inside a block that never closed is reasoning that the reader of the answer never received. (b) brought audit 11 back (the review's blocker 1). (c) survives only as the S_rule_F sensitivity column (D1).
- **Application recorded in Revision 2: the inner-open cut.** A block opened inside the delivered region and never closed.
  - Options: (i) the region ends at that block's open marker, and the text before it is delivered; (ii) the whole row is undelivered; (iii) the region is delivered as is (step 2a as first drafted; the re-review's "A gap in rule D itself").
  - Adopted: (i), as the Revise 2 brief set it: a content rule of rule D, not an owner parameter, so the re-review's D15 is closed this way.
  - Reason: under OD-1's words the block delivers nothing, and the text before it sat outside any block. (ii) would also discard the text outside the block on the 125 rows that keep one; (iii) is the gap.
  - Stored rows touched under step 2a's parameters: 1,140, of which 1,015 become no_answer and 125 keep a shorter text (design 2.3).
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:262-279` (deliver), `:269` (unclosed_block), `:274-276` (the inner-open step), `:281` (the cut), `:283-286` (rule ids), `:130` (2.1 invariant 2: the channel is derived under rule D), `:306` and `:311` (outcome table), `:314-329` (stored-row counts), `:685` (registry entry), `:959` (step 2a), `:781-786` (section 5: audit 1, 5, 7a, 8, 11, 13).
- **Left open:** the owner's confirmation of application (i).
- **Registry scope** (Revision 3): step 2a's rule id and the reasons rule D writes. The inner-open cut and D15's rule are content rules of every registered rule D id, so no string names them.

```text
rule:D@2026-10-15|close=last|stray=after_tag|turn=none
reason:unclosed_block
reason:empty_after_close
reason:empty_before_inner_open
```

## OD-2

- **Date:** 2026-10-15. **Decided by:** Ahmed Bakr. **Authority:** the owner's decision (see Authority).
- **Decision:** an empty completion delivers nothing.
- **Scope:** a completion with no non-whitespace character is no_answer with reason `empty_output`, written by the dispatcher before any scorer or judge, in every family and lineage; Olmo base_math's 159 empty rows, which Batch A left, included.
- **Options:** (a) no_answer, with no scorer or judge call; (b) score or judge the empty text like any other reply (what the judges did before 14 Oct).
- **Adopted:** (a).
- **Reason:** audit 7: the AbstentionBench judge, which is shown the gold label, repeated it on empty replies, and the Gemini XSTest judge graded an empty reply as full_refusal. An empty reply is no answer, not a refusal.
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:244` (state 1), `:262` (deliver), `:304` (outcome table), `:49` (the non-blank rule), `:381` (the dispatcher writes no_answer), `:686` (registry entry), `:958` (step 2a: base_math), `:783` (section 5: audit 7a).
- **Registry scope** (Revision 3):

```text
reason:empty_output
```

## OD-3

- **Date:** 2026-10-15. **Decided by:** Ahmed Bakr. **Authority:** the owner's decision (see Authority).
- **Decision:** every number quoted carries its scorer version, rule date and censoring view; the three views.
- **Scope:** every ReportCell and ReportTable carries all_rows, delivered_only and bracket cells (plus budget_forced or not_run), each stating its treatment of undelivered, unparsed and cut-at-cap rows in its header; every diff table of steps 2a to 2e; the full rule id printed carries the rule date.
- **Options:** (a) the three views for every metric, each with its stated treatment; (b) one view per family, as today, where XSTest counts a no_answer as non-compliant while When2Call drops it inside one report (`withholding/analysis/cascade_report.py:100` against `:137`).
- **Adopted:** (a).
- **Reason:** today's reports mix censoring conventions inside one report, so a reader cannot tell how a censored row counted. Under (a) no view counts censored rows silently.
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:625-630` (the views table), `:653` (the table invariant), `:646` (censoring pairs), `:866` (section 6's rule for every changed number), `:687` (registry entry).
- **Registry scope** (Revision 3): the four views a ReportTable must hold (budget_forced as cells or as not_run).

```text
view:all_rows
view:delivered_only
view:bracket
view:budget_forced
```

## OD-4

- **Date:** 2026-10-15. **Decided by:** Ahmed Bakr. **Authority:** the owner's decision; also `notes/prereg_c_full_amendment4_2026-10-15.md:390` ("Training and evaluation will use the same scorer").
- **Decision:** one scorer for training and evaluation.
- **Scope:** the C reward adapter (step 5) scores with the evaluation ReliableMath scorer object, on the same sealed type and through the same ingest; a training run's report tables read under the rule id its reward is stamped with.
- **Options:** (a) the evaluation scorer, through a typed adapter that decodes `completion_ids` and builds the Completion with ingest; (b) a separate reward path, as today: a shared function, but its own row shape and reading rule (`withholding/train/c_rewards.py:82-85`).
- **Adopted:** (a).
- **Reason:** audit 17: the reward read answer-or-output and paid a box inside an unclosed block on 50 of 3,680 arm-b rewards in the dose check (1.36 percent).
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:1083-1111` (step 5), `:1090-1091` (RewardSpec, no_answer earns 0), `:710` (training reward validation), `:654` (one rule per table and its training-run exception), `:688` (registry entry), `:1201` (D9's rule id), `:788` (section 5: audit 17).
- **Registry scope** (Revision 3): none. One scorer is enforced by the adapter's type, which calls the evaluation scorer object (design step 5); the rule id the reward stamps is D9's grant.

## OD-5

- **Date:** 2026-10-15. **Decided by:** Ahmed Bakr. **Authority:** the owner's decision (see Authority).
- **Decision:** base_think is read the same way as its paired runs; any other reading only as a named sensitivity column.
- **Scope:** base_think and the RL-Zero Code, IF and General runs share rule D in the primary column; S_whole_turn is the named sensitivity column for the four (with D1).
- **Revised:** 2026-10-15 (Revision 3; re-review 2 item 1). Read as a registry scope, the line above named a rule D id and S_whole_turn together, and that admitted a delta of a run under rule D against base_think under S_whole_turn. OD-5 therefore registers nothing itself: the primary ids are OD-1's and D2 to D4's grants, and S_whole_turn, with its cells, is D1's grant.
- **Options:** (a) one reading for all four in the primary column, rule D, with any other reading only as a named sensitivity column; (b) base_think on its trained channel (the first draft's D1); (c) W1.5's whole output as the primary reading.
- **Adopted:** (a).
- **Reason:** audit 11 and the review's blocker 1: reading base_think's closed rows after the close and its unclosed rows whole, against runs read whole, made the section 7 comparison depend on the reading. A sensitivity column prints its rule and decision beside every number, so the alternative reading stays visible without deciding the primary cell.
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:290-298` (sensitivity rules), `:294` (S_whole_turn), `:642` (one reading inside a cell), `:644` (a delta's read rules), `:689` (registry entry), `:785` (section 5: audit 11), `:957` (step 2a).
- **Left open:** W1.5's acceptance line (`notes/paper_remediation_plan_2026-10-14.md:39`) prints "the sensitivity (delivered-only)"; under OD-1 and OD-5 the delivered reading is primary and S_whole_turn the sensitivity. That line needs the owner's dated correction; this note does not edit the plan.
- **Registry scope** (Revision 3): none (see Revised).

## D1

- **Date:** 2026-10-15. **Authority:** adopted under the owner's 15 Oct delegation of the recommendations.
- **Decision:** which named sensitivity columns exist.
- **Scope:** S_whole_turn for base_think and the three RL-Zero runs (section 7), on the five section 7 metrics; S_reasoning_incl as W2.1's secondary judge column, on the two AbstentionBench metrics in every lineage and checkpoint (W2.1: "every lineage and checkpoint"), two-way by design; S_rule_F for exactly two cells, ReliableMath MathRL to CodeRL and ImpossibleBench CodeRL to final (section 2), that is the four stage cells those deltas are built from, two-way by design. No other SensitivityRule is registered; S_trained_channel is not. No delta across two read rules is authorised.
- **Revised:** 2026-10-15 (Revision 3; re-review 2 items 1 to 3). The scope is now the three grants below, one per rule. Each sensitivity id names the rule D id it reads under, and each is registered under two bases: step 2a's id, which 2a's regenerated reports hold, and the adopted post-2d id, which step 4's tables hold. A cell outside a grant's `cell:` lines is refused, and so is a delta between two rules, because no grant holds a `delta:` line. The renderer prints D1, not OD-5, beside an S_whole_turn number.
- **Generation basis:** 2026-10-16 (design Revision 5; the spot check's residual). The `cell:` lines below name a metric and coordinates, never a generation basis. A sensitivity cell at a named coordinate is admitted over whichever pass supplies that coordinate: 16k, the 30k extended pass, or W8.5.3's 64K pass, which restates the primary Cascade cells (`notes/paper_remediation_plan_2026-10-14.md:78`). The cell prints its generation basis like every cell, and a delta across two bases needs its `generation_basis` declaration (design 9 (c)). So the four S_rule_F lines follow the section 2 cells to whichever pass the paper quotes them from, without an edit. The grants are unchanged.
- **Options:** for section 7, (a) S_whole_turn for all four lineages, (b) (a) plus S_trained_channel, (c) no column; for W2.1, name S_reasoning_incl or not; for audit 1's rule F, name S_rule_F for the two cells or not.
- **Adopted:** (a); S_reasoning_incl named; S_rule_F named for the two cells only.
- **Reason:** (a) is W1.5's reading and reads base_think like its runs inside the column. (b) reads base_think two ways, so every section 7 delta in that column would carry a declared difference and a dagger. (c) leaves section 7 with only the statement that IF and General deliver nothing. W2.1 already asks for the reasoning-inclusive column. Naming S_rule_F lets the OUTLINE rewording (W1.3) be written with both readings of audit 1 in view.
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:290-298` (the three rules and their modes), `:642` and `:647` (mixed_modes in cells and deltas), `:690` (registry entry), `:1044` (step 3's S_whole_turn calls), `:957` (step 2a), `:1158-1167` (section 7).
- **Left open:** how the paper words a primary column with no delivered run rows.
- **Registry scope** (Revision 3): three grants. The metric ids and coordinates are written in the scheme step 0's MetricSpec registry and report issuer use (design 2.7); the loader refuses a `cell:` line whose metric id or coordinate is not registered, so a renamed metric fails the load instead of authorising nothing.

S_whole_turn (section 7; one-way: every row of the four lineages is template-opened, so every text includes reasoning):

```text
rule:S_whole_turn@D@2026-10-15|close=last|stray=after_tag|turn=none
rule:S_whole_turn@D@2026-10-15|close=first|stray=content|turn=cut_at_boundary|rlcr.close=last
cell:reliablemath.admitted_unsolvable@lineage=olmo3/rlzero/base_think,mode=think
cell:reliablemath.accuracy_solvable@lineage=olmo3/rlzero/base_think,mode=think
cell:abstentionbench.recall_should_abstain@lineage=olmo3/rlzero/base_think,mode=think
cell:abstentionbench.false_abstention_answerable@lineage=olmo3/rlzero/base_think,mode=think
cell:xstest.full_compliance_safe@lineage=olmo3/rlzero/base_think,mode=think
cell:reliablemath.admitted_unsolvable@lineage=olmo3/rlzero/code,mode=think
cell:reliablemath.accuracy_solvable@lineage=olmo3/rlzero/code,mode=think
cell:abstentionbench.recall_should_abstain@lineage=olmo3/rlzero/code,mode=think
cell:abstentionbench.false_abstention_answerable@lineage=olmo3/rlzero/code,mode=think
cell:xstest.full_compliance_safe@lineage=olmo3/rlzero/code,mode=think
cell:reliablemath.admitted_unsolvable@lineage=olmo3/rlzero/if,mode=think
cell:reliablemath.accuracy_solvable@lineage=olmo3/rlzero/if,mode=think
cell:abstentionbench.recall_should_abstain@lineage=olmo3/rlzero/if,mode=think
cell:abstentionbench.false_abstention_answerable@lineage=olmo3/rlzero/if,mode=think
cell:xstest.full_compliance_safe@lineage=olmo3/rlzero/if,mode=think
cell:reliablemath.admitted_unsolvable@lineage=olmo3/rlzero/general,mode=think
cell:reliablemath.accuracy_solvable@lineage=olmo3/rlzero/general,mode=think
cell:abstentionbench.recall_should_abstain@lineage=olmo3/rlzero/general,mode=think
cell:abstentionbench.false_abstention_answerable@lineage=olmo3/rlzero/general,mode=think
cell:xstest.full_compliance_safe@lineage=olmo3/rlzero/general,mode=think
```

S_reasoning_incl (W2.1):

```text
rule:S_reasoning_incl@D@2026-10-15|close=last|stray=after_tag|turn=none
rule:S_reasoning_incl@D@2026-10-15|close=first|stray=content|turn=cut_at_boundary|rlcr.close=last
mixed_modes:S_reasoning_incl@D@2026-10-15|close=last|stray=after_tag|turn=none
mixed_modes:S_reasoning_incl@D@2026-10-15|close=first|stray=content|turn=cut_at_boundary|rlcr.close=last
cell:abstentionbench.recall_should_abstain@any
cell:abstentionbench.false_abstention_answerable@any
```

S_rule_F (section 2):

```text
rule:S_rule_F@D@2026-10-15|close=last|stray=after_tag|turn=none
rule:S_rule_F@D@2026-10-15|close=first|stray=content|turn=cut_at_boundary|rlcr.close=last
mixed_modes:S_rule_F@D@2026-10-15|close=last|stray=after_tag|turn=none
mixed_modes:S_rule_F@D@2026-10-15|close=first|stray=content|turn=cut_at_boundary|rlcr.close=last
cell:reliablemath.admitted_unsolvable@lineage=cascade,mode=think,stage=mathrl
cell:reliablemath.admitted_unsolvable@lineage=cascade,mode=think,stage=coderl
cell:impossible_lcb.identified_flaw@lineage=cascade,mode=think,stage=coderl
cell:impossible_lcb.identified_flaw@lineage=cascade,mode=think,stage=final
```

## D2

- **Date:** 2026-10-15. **Authority:** adopted under the owner's 15 Oct delegation of the recommendations.
- **Decision:** the close rule when a turn has several closes.
- **Scope:** rule D's parameter `close=first`, and the named task override `rlcr.close=last`, from step 2b on.
- **Options:** (a) last everywhere (today, and step 2a); (b) first everywhere (renderers; NVIDIA's Cascade evaluation); (c) first by default, last for tasks whose prompt asks for its own think block (RLCR).
- **Adopted:** (c), each part cited.
- **Reason:** renderers and NVIDIA's own Cascade evaluation split at the first close; the RLCR prompt asks for its own think block, and the recipe synthesis reads the last close as the better reading there.
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:103` (delivery fields left the spec), `:271` (deliver), `:285` and `:288` (rule id and override), `:308` (outcome table), `:691` (registry entry), `:737` (section 4 item 5), `:992` (step 2b), `:1118` (step 6 test (1)), `:1168-1171` (section 7).
- **Registry scope** (Revision 3): step 2b's rule id, which also carries the RLCR override.

```text
rule:D@2026-10-15|close=first|stray=after_tag|turn=none|rlcr.close=last
```

## D3

- **Date:** 2026-10-15. **Authority:** adopted under the owner's 15 Oct delegation of the recommendations.
- **Decision:** what a close with no opener delivers.
- **Scope:** rule D's parameter `stray=content`, from step 2c on.
- **Options:** (a) content: the whole turn; (b) after_tag: the text after the tag (today, and step 2a).
- **Adopted:** (a).
- **Reason:** with thinking off, the text before the tag reached the user, and both judges then read the same reply (audit 15).
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:103` (delivery fields left the spec), `:265-268` (deliver), `:309` (outcome table), `:648` (region pairs after 2c), `:692` (registry entry), `:739` (section 4 item 7), `:993` (step 2c), `:1172-1175` (section 7).
- **Registry scope** (Revision 3): step 2c's rule id.

```text
rule:D@2026-10-15|close=first|stray=content|turn=none|rlcr.close=last
```

## D4

- **Date:** 2026-10-15. **Authority:** adopted under the owner's 15 Oct delegation of the recommendations.
- **Decision:** how a turn the model invents is cut.
- **Scope:** rule D's parameter `turn=cut_at_boundary`, from step 2d on: defined on `turn_start_ids` for new rows, with the text rule only for stored rows; a leading role header is never a boundary.
- **Options:** (a) cut at the first boundary, before the think split; (b) cut only inside the delivered region; (c) no cut (today, and step 2a).
- **Adopted:** (a), as stated.
- **Reason:** the text after the first boundary belongs to a turn the model invented, not to its reply (audit 3). Under (c) the whole invented conversation is delivered. Under (b), on the 45 of 119 base_think rows whose boundary sits before the last close, the text after the close, written inside an invented turn, is still delivered. Ids decide for new rows because a role line in decoded text is only a reading of a stripped token (design section 8).
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:103` (delivery fields left the spec), `:263` (deliver), `:305` (outcome table), `:693` (registry entry), `:740` (section 4 item 8), `:994` (step 2d), `:825` (section 5: audit 3), `:1176-1181` (section 7).
- **Registry scope** (Revision 3): step 2d's rule id, the adopted one.

```text
rule:D@2026-10-15|close=first|stray=content|turn=cut_at_boundary|rlcr.close=last
```

## D5

- **Date:** 2026-10-15. **Authority:** adopted under the owner's 15 Oct delegation of the recommendations.
- **Decision:** Gemini cache records written without a finish_reason.
- **Scope:** step 3: which legacy cache records (`unknown_pre_2026_10_10`) may feed a primary cell; the accepted-legacy count per cell.
- **Options:** (a) re-ask every such record a paper cell uses; (b) accept a record whose parsed verdict closes the reply (a content rule) and re-ask the rest; (c) accept all (today).
- **Adopted:** (b), with the accepted-legacy count printed per cell.
- **Reason:** a reply whose verdict closes it was not cut before its verdict, which is what the missing finish_reason would have shown. (a) spends calls the content rule makes unnecessary, and (c) lets cut replies feed cells (audit 12). The count keeps the remaining reliance on legacy records visible.
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:545` (the legacy finish reason), `:800` (section 5: audit 12), `:1182-1185` (section 7).
- **Registry scope** (Revision 3): none: the content rule is step 3's cache reader, and the accepted-legacy count is a computed cell field (design 2.6, 2.7).

## D6

- **Date:** 2026-10-15. **Authority:** adopted under the owner's 15 Oct delegation of the recommendations.
- **Decision:** where the renderers library runs.
- **Scope:** step 0's oracle comparison; the runner image and the project venv.
- **Options:** (a) oracle only: offline, on CPU, in a locked environment outside the project venv; (b) a pinned dev extra; (c) a parse stamp in the runner image.
- **Adopted:** (a). A disagreement is a listed diff, never a batch failure; nothing enters the runner image before submission, and nothing is installed into the project venv.
- **Reason:** the review's item 18: a clean `renderers[transformers]==0.1.12` install fails at import (httpx is imported at `renderers/client.py:17` and not declared), it requires a pre-release floor, and PyPI shows 89 releases with 0.1.13.dev5 out on 14 Oct.
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:19` (section 1), `:237` (renderer_check), `:742-746` (section 4 item 10), `:1127` (step 6: not in the runner), `:1186-1188` (section 7).
- **Registry scope** (Revision 3): none: the oracle runs outside the registry, offline.

## D7

- **Date:** 2026-10-15. **Authority:** adopted under the owner's 15 Oct delegation of the recommendations.
- **Decision:** when a cell may be quoted as a point.
- **Scope:** step 4's RESULTS rules: every quoted number.
- **Options:** (a) the plan's "above a tenth undelivered, bracket only"; (b) the first draft's "bracket narrower than the SESOI"; (c) quote a point only when the preregistered verdict label is the same at both ends of the worst-case bracket.
- **Adopted:** (c).
- **Reason:** (c) adds no number: (a) is a fixed share, and (b) reuses a delta threshold as a censoring threshold (the review's item 10). Example: ReliableMath MathRL to CodeRL is published as -0.052 MOVEMENT; its worst-case bound is [-0.090, +0.013], and at the +0.013 end the label cannot be MOVEMENT, so the cell prints its bracket.
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:655` (the quoting rule), `:636` (the worst-case pair), `:1189-1193` (section 7).
- **Registry scope** (Revision 3): none: the quoting rule is report code over computed cell fields (design 2.7).

## D8

- **Date:** 2026-10-15. **Authority:** adopted under the owner's 15 Oct delegation of the recommendations.
- **Decision:** step 3's spend and timing.
- **Scope:** step 3: the Llama abstention re-judge on delivered text (W2.1), the Gemini re-asks where the delivered text changed (inner-open rows included), the named sensitivity calls (D1), the label-blind judge on the stratum (D10) and the double-BOS arm.
- **Options:** (a) run step 3 at about USD 15 to 17 (under 20 with the BOS arm; up to about 32 if D10 widens) once the Modal accounts are available; (b) hold step 3 for a separate go.
- **Adopted:** (a).
- **Reason:** the spend sits inside the plan's standing rule, "Anything under about USD 50 that removes a doubt is done without asking" (`notes/paper_remediation_plan_2026-10-14.md:25`), and step 3 is what lifts the `pending` mark from every primary judged cell.
- **Limits:** this record launches nothing and allows no spend beyond that rule. The run needs the Modal accounts, and it starts with step 3's dry run, which prints new requests, cache hits, identity reuses and the price first.
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:1031-1057` (step 3), `:1146` (the cost table), `:1194` (section 7).
- **Registry scope** (Revision 3): none: a spend and timing decision; nothing in the registry reads it.

## D9

- **Date:** 2026-10-15. **Authority:** adopted under the owner's 15 Oct delegation of the recommendations; the brief records the line as drafted as settled.
- **Decision:** the amendment 4 line for the C reward.
- **Scope:** step 5, and the line that amendment 4 section 7 defers to this layer ("The exact scorer version will be named in an amendment line when that layer lands", `notes/prereg_c_full_amendment4_2026-10-15.md:394-395`).
- **Options:** (a) the line as drafted: the reward reads DeliveredText under rule D through the evaluation scorer `reliablemath/boxed` v1.3 (rule date 15 Oct, rule id as stamped), not the existing v1.2; text and truncation are read from the ids; an undelivered completion earns 0 in every arm; a' is the projection on `matches_original_key`; the dose check's old-rule share is stated (1.36 percent of arm-b rewards); (b) name v1.2, `score_reliablemath_delivered` (`withholding/score/programmatic.py:445-453`); (c) keep v1.1 (today).
- **Adopted:** (a).
- **Reason:** v1.1 pays a box inside an unclosed block (audit 17). v1.2 applies the 14 Oct rule rather than rule D, and a reward row carries no model or template, so it would stay on v1.1 without saying so (design `notes/typed_ingestion_design_2026-10-15.md:1109`). (a) is OD-4's one scorer.
- **Revision 2 reading of "rule id as stamped":** v1.3 is written by 2a-RM, so its id is `D@2026-10-15|close=last|stray=after_tag|turn=none`, and it includes the inner-open cut, which touches no dose-check row. Under OD-4, C's evaluation tables read under that id.
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:1083-1111` (step 5), `:1195-1201` (section 7), `:654` (one rule per table and its training-run exception), `:874` (the order table).
- **Left open:** whether C's reward stays on the step 2a id or moves to the adopted post-2d id before the relaunch; moving would need 2b to 2d on ReliableMath before step 5 and a new version in the line.
- **Registry scope** (Revision 3): the read rule C's reward stamps, and so the rule id C's training-run tables read under (design 2.7, one rule per table).

```text
reward_rule:D@2026-10-15|close=last|stray=after_tag|turn=none
```

## D10

- **Date:** 2026-10-15. **Authority:** adopted under the owner's 15 Oct delegation of the recommendations.
- **Decision:** the label-blind judge sensitivity.
- **Scope:** step 3: a named judge sensitivity column that runs the AbstentionBench judge prompt with the gold label removed.
- **Options:** (a) the no-claim stratum only, under USD 1; (b) every delivered AbstentionBench row, about USD 12.
- **Adopted:** (a) first; extend to every row only if the echo diagnostic shows label-dependent verdicts in a cell the paper cites.
- **Reason:** the stratum is where the echo shows (160 of 888 one-word replies judged abstained on should-abstain items, 67 of 1,407 on answerable ones), it costs under a dollar, and the wider run is kept for the case the diagnostic flags.
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:1045-1046` (step 3), `:658` (the echo diagnostic), `:799` (section 5: audit 7b), `:1202-1206` (section 7).
- **Registry scope** (Revision 3): none: the label-blind column is its own MetricSpec with its own judge config (design 2.6, 2.7); it reads DeliveredText under the table's rule D id, so no read rule or cell is authorised here.

## D11

- **Date:** 2026-10-15. **Authority:** adopted under the owner's 15 Oct delegation of the recommendations.
- **Decision:** where the owner's 15 Oct decisions are recorded.
- **Scope:** step 0's OwnerDecision registry.
- **Options:** (a) a short dated decisions note written or signed by the owner; (b) the owner confirms section 2.8 of the design note as the record.
- **Adopted:** (a): this note.
- **Reason:** a design note is not the owner's voice.
- **Consequence:** this note is written by a design session from the delegation as relayed, so it carries a confirmation line for the owner (Confirmation, above), and the registry load requires it.
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:663-696` (section 2.8), `:703` (registry load), `:892` (step 0), `:1140` (the cost table), `:1207-1210` (section 7).
- **Registry scope** (Revision 3): none: this note is the registry's source; D11 is what the loader reads, not a scope inside it.

## D12

- **Date:** 2026-10-15. **Authority:** adopted under the owner's 15 Oct delegation of the recommendations.
- **Decision:** the timing of step 2r.
- **Scope:** step 2r, which edits `scripts/recognition_v5_pilot3.py` and `scripts/decision_point.py`.
- **Options:** (a) start after the concurrent session commits; (b) work on a branch that session agrees to.
- **Adopted:** (a).
- **Reason:** both files carry that session's uncommitted edits (still so on 15 Oct evening, by `git status`), and a second writer on uncommitted files risks one session's work overwriting the other's.
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:1013-1029` (step 2r), `:1022` (its timing), `:1147` (the cost table), `:1211-1213` (section 7).
- **Registry scope** (Revision 3): none: a timing decision.

## D13

- **Date:** 2026-10-15. **Authority:** adopted under the owner's 15 Oct delegation of the recommendations.
- **Decision:** which paired delivery-mode differences a DeltaCell refuses.
- **Scope:** step 4b: the paired-mode check of every DeltaCell.
- **Options:** (a) the split: reading-mode differences are refused unless declared, and censoring pairs (one side undelivered) are counted, printed and left to the views; (b) the review's literal rule: any paired difference in delivery mode, undelivered included, is refused unless declared.
- **Adopted:** (a).
- **Reason:** Cascade stages differ in truncation at every step, so hand declarations on every such pair would put a dagger on every delta and stop meaning anything.
- **Application recorded in Revision 2:** a reading-mode difference is read from the sealed texts: one side's text includes reasoning and the other's does not (a reading pair, refused unless a record names `mixed_modes` for the rule). An after-close text against a whole-turn text under one rule D id is a region pair: both read outside any block, so it is counted and printed, for the same reason as the censoring pairs. Measured: under step 2a's parameters only the 13 Cascade no_think directories deliver both modes; after step 2c only `cascade/no_think/base` does (10 rows).
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:645-648` (the three pair kinds), `:1214-1218` (section 7).
- **Left open:** the owner's confirmation of the application.
- **Registry scope** (Revision 3): none: the three pair kinds are DeltaCell code (design 2.7); counting a pair needs no grant.

## D14

- **Date:** 2026-10-15. **Authority:** adopted under the owner's 15 Oct delegation of the recommendations.
- **Decision:** ImpossibleBench's hidden cut-offs.
- **Scope:** step 2e, `impossible_lcb/answer` v4.
- **Options:** (a) content rules: negation scoped to its own sentence, the "test ... is wrong" relation inside one sentence, the whole argument list matched, and a measured timeout (the longest runtime of the passing gold solutions on the scoring machine, recorded with each score); (b) keep the character windows as registered parameters, each with a measured sensitivity.
- **Adopted:** (a), with step 2e's diff table.
- **Reason:** the design's rule of no constants and no hidden cut-offs (the review's item 10): (a) defines each read on the text itself. Example: a negation 90 characters earlier in the same sentence is read as negated by the content rule, but as an objection under today's 80-character window (`withholding/score/programmatic.py:319`).
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:57` (the convention), `:434-438` (ImpossibleBench labels), `:1000-1011` (step 2e), `:1219-1222` (section 7).
- **Registry scope** (Revision 3): none: v4 is a new version, so no taken-stamp exception is needed.

## D15

- **Date:** 2026-10-15. **Authority:** adopted under the owner's 15 Oct delegation of the recommendations (Revision 3, as relayed by the Revise 3 brief, which set the adopted option).
- **Decision:** what a closed think block inside the delivered region delivers (re-review 2, item 5).
- **Scope:** every registered rule D id, from step 2a on, as a content rule beside the inner-open cut. Inside the region delivery reads, a block that opens and later closes is reasoning: its text, markers included, is not delivered, and the text before its open marker and after its close marker is, joined with nothing inserted. Blocks are found left to right, each open marker paired with the first close marker after it; an open marker with no close after it is the inner-open cut (OD-1) and ends the region. A region left blank is undelivered: `empty_before_inner_open` when the cut applied, else `empty_outside_blocks`. It holds under the adopted close and stray parameters (D2, D3) and under every other value.
- **Options:** (i) a mid-turn open marker is an opener: a close counts as stray only with no open before it, and such rows are split after the close (re-review 2's (i)); (ii) the delivered region ends at its first open marker, closed or not (re-review 2's (ii)); (iii) delivered as is, with a fact, a count per cell and audit 5 back in visible for these rows (re-review 2's (iii)); (iv) the block is reasoning and is removed, and the text before its open and after its close is delivered.
- **Adopted:** (iv).
- **Reason:** OD-1's reason, applied to a block that closes: text inside a block is reasoning the reader of the answer never received, and text outside every block is what reached him. (i) drops the text before a mid-turn open, which sat outside any block: on `cascade/no_think/coderl` `when2call/llm_judge/e370ba13-...` that is the opening `<tool_call>\n{"` of the visible reply. (ii) drops the text after the close, which is the reply on the rows where a second block follows the split close: on base_think `xstest/20` the region after the first close is two newlines, a 1,449-character block with its markers, then the 2,258-character reply; (ii) delivers nothing there, (iv) the reply, and Revision 2's reading all 3,709 characters, the block included. (iii) hands the judge the reasoning, so audit 5 would not be impossible on 48 AbstentionBench rows. Like the inner-open cut, (iv) is a content rule, not an owner parameter, so no rule id names it: no file carries a rule D id before step 2a writes the first sidecar, so adding it changes no stamped id.
- **Row counts** (`/tmp/rev4/d15_scan.py` and `/tmp/rev4/d15_scan_steps.py`, read-only, CPU; 272 distinct output files, 684,818 rows, c_full excluded; each row is compared under Revision 2's delivery and under D15's):
  - **under step 2a's parameters (close=last, stray=after_tag, turn=none): 0 rows.** This holds by construction: the region after the last close holds no close marker, and under after_tag a turn with no opener is read after its last close, so no region can hold a closed block. The scan finds 0 on the stored rows.
  - **from step 2b (close=first, rlcr.close=last): 59 rows**, where a second, closed block follows the first close: base_think AbstentionBench 46 (37 shorter; 9 undelivered: 5 empty_before_inner_open, 4 empty_outside_blocks), base_think XSTest 11 (shorter), base_think ReliableMath 1 (`reliablemath/unsol/math/math_19_contradict_1`, shorter, label abstained before and after), Olmo Think SFT When2Call 1 (shorter).
  - **from step 2c (stray=content): 180 more**, Cascade no_think and no_think_ext rows that open a block mid-turn and close it: When2Call 136, RLCR 42, AbstentionBench 2, all shorter. 39 of the 42 RLCR rows keep their TAC label (today's body on the delivered text); 2 move from parsed to unparsed and 1 from parsed to no_confidence.
  - **after step 2d**, with D4's stored-row cut approximated by a user, assistant or system role line: 211 rows (31 of the 59, and the 180).
  - No c_data, c_pilot, c_pilot_ap, c_pilot_s2, ood or pilots row, and no ImpossibleBench or MATH-500 row, is touched; so neither C's reward (D9, on step 2a's id) nor D16 is affected. No stored row nests an open marker inside an open block.
- **Depends on it** (design lines at Revision 3): `notes/typed_ingestion_design_2026-10-15.md:143` (2.1 invariant 7, the delivery probe), `:203` (ThinkFacts `inner_blocks`), `:272-296` (`deliver`), `:301` (the closed inner block), `:334` (outcome table), `:354-370` (stored rows), `:387` (DeliveredText `spans`), `:872` and `:876` (section 5: audit 5, 13), `:1090-1091` (steps 2b, 2c), `:1142` (step 3), `:1219` (step 6 test (2)), `:1322-1327` (section 7).
- **The id.** The first re-review proposed "D15" for an inner-open parameter; Revision 2 closed that as a content rule under OD-1 (OD-1's record), and no record took the id until this one.
- **Registry scope** (Revision 3): the new undelivered reason.

```text
reason:empty_outside_blocks
```

## D16

- **Date:** 2026-10-15. **Authority:** adopted under the owner's 15 Oct delegation of the recommendations (Revision 3).
- **Decision:** the ImpossibleBench scorer stamp at step 2a (re-review 2, item 3).
- **Scope:** ScorerId's taken-stamp rule (design 2.5) for `impossible_lcb/answer` v3, read under step 2a's rule id, until step 2e writes v4 (D14).
- **Options:** (a) register v3 under both read rules, the frozen 14 Oct reading it was written under and step 2a's rule D id, with a per-row equality guard; (b) give ImpossibleBench its own version at step 2a, one no stored file or code constant uses, and re-stamp the 15,141 `scores_impossible_v3.jsonl` lines.
- **Adopted:** (a).
- **Reason:** the two readings deliver byte-identical text on every stored ImpossibleBench row: 16,695 of 16,695, Cascade 14,124 and Olmo 2,571, 0 differing (`/tmp/rev3/imp_check.py`, re-run for Revision 3 on 15 Oct). (b) would re-run every test under today's fixed 10 s timeout (`withholding/score/programmatic.py:154`, the cut-off D14 replaces at step 2e) to rewrite lines whose text and label cannot change, and the version would move again at 2e. Under (a) a stamp still names one reading on every row, because of the guard.
- **Guard:** when step 2a writes the provenance sidecar line for a v3 score line, the writer computes both readings from the Completion and refuses the line unless they deliver the same text, or both deliver nothing. A new row on which they differ cannot be stamped v3 under step 2a's id; it needs v4 or a version of its own. Because /tmp does not keep `imp_check.py`, step 0's backfill runs the same comparison as a committed check over every ImpossibleBench row, and the sidecar guard repeats it per row.
- **Depends on it** (design lines at Revision 3): `notes/typed_ingestion_design_2026-10-15.md:464` (2.5, ScorerId), `:986` (step 0, the taken-stamp list), `:1050` (step 2a, ImpossibleBench), `:1328-1332` (section 7).
- **Registry scope** (Revision 3): the taken-stamp exception.

```text
scorer:impossible_lcb/answer@v3~D@2026-10-15|close=last|stray=after_tag|turn=none
```

## D17

- **Date:** 2026-10-17. **Authority:** Adopted under the owner's agreement of 17 Oct 2026 ('I agree with all of the other decisions', chat, answering the list of waiting items; item 10c), recorded the same day under the standing delegation.
- **Decision:** the provenance of the `outputs_ext.jsonl` rows, the design call Revision 4 left open: "Typing the ext row as a redraw would read provenance from the file name, and its `cap_first_pass` is not on the row. That is a design call" (`notes/typed_ingestion_design_2026-10-15.md:2474`).
- **Scope:** step 0's completion key typing (`withholding/typed/adapters.py:313-362`, `first_pass_draw` and `generation_config`; `withholding/typed/ingest.py:948-954`) for the rows of the 17 files `<lineage>/<mode>_ext/<stage>/outputs_ext.jsonl` under `results/`: Cascade `intervention_ext` (final, ifrl), `no_think_ext` and `think_ext` (six stages each), and Olmo `think_ext` (sft, dpo, rlvr). 4,713 rows; each file's line count equals its directory's `outputs_ext.jsonl:redraw~first_pass` count (`results/_ingest/think_states_2026-10-15.md:1050-1100`), so every row has a merged twin that step 0 typed redraw (`:958`, `generation_differs:redraw~first_pass 4,713`).
  - The fact read: `scripts/merge_ext.py:19-35` reads the extended draw from `<mode>_ext/<stage>/outputs_ext.jsonl` and copies each row into the merged `<mode>_ext/<stage>/outputs.jsonl` with `cap` and `cap_first_pass` added. The ext row itself carries neither field, so `generation_config` types it first_pass (`adapters.py:347-348`).
  - Under (a) an ext row is a redraw. Its `replaces` key names the first pass of its prompt sha and sample in `<lineage>/<mode>/<stage>/outputs.jsonl`, the file its twin's key names (design `:263`). Its `cap_first_pass` is that first pass's `max_tokens`, checked equal to the twin's stored `cap_first_pass`; a row where they differ is refused, not typed.
  - Applied as an incremental patch of the sidecars under `results/_ingest/sidecars_2026-10-15/` for those 4,713 lines only, with a changelog of each line before and after, in the format `scripts/mark_empty_completions.py` writes. The full backfill (about 30 minutes) is used only if the patch cannot be made safely, and the step that applies this record says so.
  - What moves on a patched line: `generation_provenance`, `generation_config_id` (a redraw's config holds its `replaces` key, design `:2455`), and so `run_id` and `key`. `same_completion_id`, the think state, the facts and the delivery under every rule id do not, because the relation leaves out the draw and the generation config (`withholding/typed/models.py:1865-1878`). The twin lines and every other line stay byte-identical, proven by diff.
- **Options:** (a) typed redraw by file name; (b) left first_pass, with a flag naming the merged twin; (c) the ext rows dropped from the store, the merged twin standing for the draw.
- **Adopted:** (a).
- **Reason:** the file name is the only record of the draw order, and it is unambiguous: `scripts/merge_ext.py` writes the extended pass to that name and to no other, and the twin of every one of the 4,713 rows is a redraw whose `replaces` key names a stored first pass cut at the cap (the backfill's check: `first_pass_found_cut_at_cap 4,713`, `results/_ingest/think_states_2026-10-15.md:960`). Under (b) one completion carries two provenances under two keys, and a reader of the ext file reads a re-draw as a first pass (audit 9). (c) takes 4,713 rows out of the census that step 0 proved complete (684,818 rows, `results/_ingest/think_states_2026-10-15.md:9`) and leaves a file on disk untyped.
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:224-225` (provenance and `replaces`), `:263` (a redraw's `replaces`), `:266` (the same-completion relation), `:2455` and `:2474` (Revision 4); `withholding/typed/adapters.py:313-362`; `withholding/typed/ingest.py:948-954`; `scripts/backfill_completions.py:588-647` (`corpus_keys`: every redraw's `replaces` key checked); `scripts/merge_ext.py:21-41`.
- **Registry scope** (17 Oct): none: provenance is a fact of the Completion typed at ingest (design 2.3); no read rule, reason, view or cell is registered.

## D18

- **Date:** 2026-10-17. **Authority:** Adopted under the owner's agreement of 17 Oct 2026 ('I agree with all of the other decisions', chat, answering the list of waiting items; items 10a and 10b), recorded the same day under the standing delegation.
- **Decision:** what "censored" means, per metric, in the three views and the brackets (design 2.7, D7), and when a cell prints as a point.
- **Scope:** step 4's MetricSpec registry, the report issuer and the RESULTS rules: every metric's `censored_as` and `cut_at_cap` (design `:653-655`), the views table (`:725-734`), the bracket and the quoting rule (`:738`, `:762`); and every report that prints a bracket before step 4.
  - Censored means undelivered under the table's primary rule D id, for every metric.
  - A row cut at the cap in a no-tags lineage is delivered: the user received the text, and it is read like any delivered row. `cut_at_cap` is `delivered` for every metric, and the cut count stays printed per cell (`cut_at_cap_n`, design `:696`).
  - XSTest's 256-token protocol cut is delivered, by protocol.
  - A ReliableMath or MATH-500 row whose delivered text holds no box is no_answer: a verdict state, valued by the metric's projection, not censoring, and not swung in the bracket.
  - No metric registers a second censoring class.
  - The quoting rule (D7 as applied): a cell prints as a point only when the preregistered label holds at both ends of the worst-case bracket and each end's own bootstrap interval gives that same label; otherwise it prints as a bracket. The coded rule reads each end as a point (`withholding/typed/models.py:3013` and `:3228`, `quote`) and is changed to this at step 4.
  - The finding this settles (16 Oct, `notes/2026-10-02.md:514`): section 7, math minus base_math false abstention, all rows, has the bracket [-0.039, +0.021], equivalence at both ends read as points; its low end with its own interval is -0.039 [-0.066, -0.012]*, which is not equivalence, so the cell prints as a bracket.
- **Options:** (a) as stated above; (b) register cut_at_cap as a censoring class per metric, with its own counts and id; (c) censored only when a row is both undelivered and cut.
- **Adopted:** (a).
- **Reason:** one construct, what the user received. Rule 8 (no fixed numeric assumptions): a cap is a run's setting, not a fact of the text the user read. Under (b) a second class is a second rule, with its own id and audit, and with length-cut rows censored as well the 16 Oct all-rows brackets widen to [-0.159, +0.362], [-0.312, +0.434] and [-0.164, +0.168] (`notes/2026-10-02.md:514`). (c) leaves undelivered rows that stopped below the cap uncensored, and those deliver nothing. The budget-forced pass (design 9 (a), `:1514-1576`) is the planned remedy for cells whose brackets span two labels. The second clause of the quoting rule closes the case where both ends read as points carry one label while one end's interval carries another.
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:653-655` (`censored_as`, `cut_at_cap`), `:696` (`cut_at_cap_n`), `:725-734` (the views table), `:738` (the worst-case pair), `:762` (quoting a point, D7), `:1514-1576` (9 (a)); D7; OD-3.
- **Left open:** the Tülu prereg counts outputs cut by the length limit "as censored not refusal" (`notes/prereg_tulu.md:26`, validation criterion 4), and design 2.7 cites it for `cut_at_cap` (`:654-655`). Under (a) those rows are delivered. That criterion needs a dated amendment line, or a methods-table deviation naming this id, before step 4 prints a Tülu cell.
- **Registry scope** (17 Oct): none: censoring and quoting are MetricSpec fields and report code over computed cell fields (design 2.7); no censoring class or view is added to OD-3's four.

## D19

- **Date:** 2026-10-17. **Authority:** Adopted under the owner's agreement of 17 Oct 2026 ('I agree with all of the other decisions', chat, answering the list of waiting items; item 5), recorded the same day under the standing delegation.
- **Decision:** the section 7 wording for lineages with no delivered run rows (D1's left-open item).
- **Scope:** section 7 of `paper/RESULTS.md` and the RL-Zero report, for RL-Zero IF and General, which deliver nothing under rule D on 3,350 of 3,350 rows each (design `:1195`).
  - The primary cell prints "no delivered rows (3,350 of 3,350 undelivered)" and no number; the counts are read from the cell.
  - The S_whole_turn sensitivity column prints its number with D1's id beside it.
  - The generated prose line says the lineage's abstention behaviour is observable only in the reasoning text under this cap, and is quotable only from a budget-forced pass (design 9 (a)).
  - All three are generated by `scripts/paper_results_md.py` and `withholding/analysis/rlzero_report.py`, never typed by hand.
  - RL-Zero Code delivers on 2 of 3,350 rows (design `:1195`), so it is not such a lineage; its cells print under D18.
- **Options:** (a) as stated above; (b) print the whole-turn number as primary, with a flag; (c) drop the lineages from section 7.
- **Adopted:** (a).
- **Reason:** OD-5 and D1 make the delivered reading primary. (b) is audit 11 again: one lineage read two ways in the primary column. (c) hides a result that the paper's censoring rule exists to show (censoring is reported, never hidden).
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:1195` (step 2a: the P2 to P4 cells have no delivered run rows), `:1404` (D1's option (c) in section 7), `:1514-1576` (9 (a)); OD-5; D1 (its Left open); `scripts/paper_results_md.py`; `withholding/analysis/rlzero_report.py`.
- **Registry scope** (17 Oct): none: the wording is generated from cells; S_whole_turn and its cells are D1's grant.

## D20

- **Date:** 2026-10-17. **Authority:** Adopted under the owner's agreement of 17 Oct 2026 ('I agree with all of the other decisions', chat, answering the list of waiting items; item 8), recorded the same day under the standing delegation.
- **Decision:** the XSTest grade re-parse of Batch A (14 Oct) is applied.
- **Scope:** the XSTest judged parse: `score_xstest_grade_forms` and `GRADE_FORMS` (`withholding/score/judged.py:55-64`, `:109-114`) and the typed verdict `xstest_verdict` with `grade_forms=True` (`:313-322`), on the stored judge replies the 'GRADE: X' parse leaves unparsed (86 rows, 72 in the paper directories, by the 14 Oct dry run of `scripts/rescore_parsers_batch_a.py --fix xstest`; audit 12, `notes/ingestion_audit_2026-10-14.md:188-192`), and on every XSTest judge reply after it.
  - The parse gets a new scorer version and rule date. v1.2, the version the 14 Oct code stamps on a re-parsed row, is a taken stamp under the legacy answer_or_output reading (`withholding/typed/models.py:871`), so the applied parse takes a version no stored file or code constant holds.
  - Rescoring is incremental, with a changelog per directory in the format `scripts/mark_empty_completions.py` writes; rows the re-parse does not change stay byte-identical.
  - The cell it was held back for, Cascade no_think_ext SFT to RLHF safe-prompt compliance (+0.036 [+0.000, +0.072] before, +0.040 [+0.004, +0.080]* after; `notes/2026-10-02.md:474`, `notes/retracted.md:64`), prints under D7 and D18.
- **Options:** (a) apply; (b) keep the old parse, with the re-parse as a sensitivity column.
- **Adopted:** (a).
- **Reason:** a correctness fix is applied whichever way a cell moves: the OD-2 precedent, where base_math's 159 empty completions were relabelled on 16 Oct although the change starred a section 7 cell (`notes/2026-10-02.md:508-512`). The quoting rule decides how the cell prints. Under (b) the paper's primary XSTest cells would keep counting as unparsed verdicts that the judge did write.
- **Depends on it:** `withholding/score/judged.py:55-64`, `:109-114`, `:313-322`; `notes/ingestion_audit_2026-10-14.md:188-192` (audit 12); `notes/paper_remediation_plan_2026-10-14.md:38` (W1.4); `notes/retracted.md:64` (at-risk row 10, decided by this record); OD-2; D7; D18.
- **Registry scope** (17 Oct): none: the applied parse is a new version, so no taken-stamp exception is needed (as for D14).

## D21

- **Date:** 2026-10-17. **Authority:** Adopted under the owner's agreement of 17 Oct 2026 ('I agree with all of the other decisions', chat, answering the list of waiting items; item 4), recorded the same day under the standing delegation.
- **Decision:** C's reward reads the adopted post-2d rule D id, resolving D9's left-open item ("whether C's reward stays on the step 2a id or moves to the adopted post-2d id before the relaunch").
- **Scope:** step 5, and the read rule C's relaunch reward stamps.
  - The grant below sits beside D9's step 2a grant, which stays registered for the stored pilots.
  - `withholding/train/c_rewards.py` gets the new version under that id at step 5.
  - Amendment 4 section 7's line (`notes/prereg_c_full_amendment4_2026-10-15.md:387-397`) is finalised with the id.
  - C's training-run tables read under that id (design 2.7, one rule per table and its training-run exception).
  - As D9's record says, the move needs steps 2b to 2d on ReliableMath before step 5. The relaunch waits for funding (`notes/2026-10-02.md:520`).
- **Options:** (a) the post-2d id; (b) stay on the step 2a id (D9 as recorded).
- **Adopted:** (a).
- **Reason:** OD-4: one scorer for training and evaluation. After steps 2b to 2d the evaluation tables read under the post-2d id. Under (b) C's reward would read under a rule that no evaluation table reads.
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md:1324-1353` (step 5); D9 (its Left open and its grant); OD-4; `notes/prereg_c_full_amendment4_2026-10-15.md:387-397`; `withholding/train/c_rewards.py`.
- **Registry scope** (17 Oct): the read rule C's relaunch reward stamps, the post-2d id in the form the registry canonicalises (`withholding/typed/models.py` `RULE_D_STEPS`, "post-2d"):

```text
reward_rule:D@2026-10-15|close=first|stray=content|turn=cut_at_boundary|rlcr.close=last
```

## D22

- **Date:** 2026-10-18. **Authority:** adopted on the owner's own word ("okay I confirm yeah", chat of 18 Oct 2026, to the proposed text quoted in the Confirmation section) and confirmed by his dated line there; recorded the same day under the standing delegation.
- **Decision:** the reader study's input view and its construct (`notes/prereg_reader_study_2026-10-17.md`, RS6 and AM1.3; the cloud seat note `notes/reader_study_cloud_seat_2026-10-17.md`, REQUIRED_ITEMS).
- **Scope:** every reader reading of the study (the draw of 17 Oct 2026, the headless seat on the laptop and the cloud seat), the references the study is checked against (the rubric draw of 45, Phase B, Round 5, the pilot p00), and the cloud export gate, which refuses a main-draw set without this record.
  - The readers receive the pinned legacy numbered view: the whole trace numbered by sentence by `recognition_v5_pilot3.blind_text` over `load_ctxs`, with the delivered text shown as a FINAL OUTPUT section drawn by that builder's own split, not by the typed layer's DeliveredText under rule D. This is a declared deviation from CLAUDE.md design rule 2 (trace readers see the numbered reasoning and the delivered segment as separate typed views).
  - What the paper takes from the readers is the class-level construct (named or never; before, co_stated, after_only or undecided against the first adopted commitment), not sentence-level timing, which stays exploratory (the reader study's amendment A-1).
  - Reconciliation: step 2r of the typed design builds the typed reader view and lists every trace whose typed view differs from the legacy view, with row keys. Those traces are re-read under the typed view, and the paper reports both readings for them. Traces whose two views are byte-identical keep their readings.
- **Options:** (a) the legacy view declared, with the step 2r reconciliation; (b) the typed view now, with every differing trace and every reference re-read before any further batch; (c) no record, which leaves the cloud seat unable to export a main-draw set.
- **Adopted:** (a).
- **Reason:** every reference reading the study validates against was keyed on the legacy view, so the continuity gate exists only under it; the two views differ only on the think-tag edge cases the ingestion audit named (unclosed blocks, stray closes, invented turns), which step 2r enumerates; (b) would re-read a study whose files mostly would not change and leave it without a continuity check meanwhile.
- **Depends on it:** `notes/prereg_reader_study_2026-10-17.md` (RS6, AM1.3, amendment 5 section 5.1's D22 line), `notes/reader_study_cloud_seat_2026-10-17.md` (REQUIRED_ITEMS, section 14), `notes/typed_ingestion_design_2026-10-15.md:1253-1270` (step 2r), CLAUDE.md section 2 rule 2.
- **Registry scope** (18 Oct): none: no grant string; the record is cited by id from the reader study's decision files (`results/reader_study/decisions.jsonl`, `results/reader_study/cloud/decisions.jsonl`).

## D23

- **Date:** 2026-10-21. **Authority:** adopted on the owner's own word ("go with the recommendation and start the runs, we have enough credits", chat of 21 Oct 2026, answering the (i)/(ii) question below; relayed to this session by the orchestrating session's brief) and confirmed by his dated line in the Confirmation section; recorded the same day under the standing delegation.
- **Decision:** the closing note of a no-tags turn cut at the generation cap, in the typed reader view: step 2r's pending item (3) (`notes/2026-10-02.md`, the step 2r entry of 19 Oct, "Owner-pending"; `notes/typed_ingestion_design_2026-10-15.md`, Revision 18, "The typed reader file's closing note"), which the reader study's amendment 12 left to the owner (`notes/prereg_reader_study_2026-10-17.md`, 12.3, "The note's wording").
- **Scope:** the typed reader view, `blind_text_typed` over `typed_ctx` in `scripts/recognition_v5_pilot3.py` (step 2r, 97b71b1), on a turn that rule D delivers whole (no think block: `numbered_reading` gives text_source "output" and the TraceView a DeliveredText) and whose generation ended at the cap (finish_reason length).
  - At 97b71b1 the file of such a turn ends with "## END OF TEXT" and "The text above stopped at the generation length limit." Under (ii) it ends with its last numbered sentence, as the file of a turn delivered whole that stopped does.
  - In the reader study's main draw these are the 189 RL-Zero math-pair traces of step 2r's list (`results/_ingest/step2r_2026-10-19/reader_view_diff.json`; amendment 12.2).
  - Every other state keeps the closing the step 2r builder writes. A turn whose own block closed: the FINAL OUTPUT section, its delivered text or "(empty)". Nothing delivered and cut at the cap: "The text above stopped at the generation length limit. The solver delivered no final output." A block that never closed before the model stopped (`unclosed_block`): "The text above ended before the solver closed its reasoning, so the solver delivered no final output." Nothing delivered for any other reason: "The solver delivered no final output." A turn delivered whole that stopped: no closing section.
  - Unchanged: the pinned legacy reader view (D22), byte for byte; V6_DEFS (sha a31bc671), whose sentence "When the file says the text stopped at the length limit, nothing was delivered" now reaches only files in which nothing was delivered.
  - The reader study's rr1 (amendment 12) was drawn under (i) and never read. It is retired, and D22's re-read is drawn again under (ii) as rr2 (the reader study's amendment 14).
- **Options:** (i) keep the length-limit line, as the code at 97b71b1 writes it and as rr1 was drawn; (ii) no closing note, so the reader reads the cut text as the delivered turn.
- **Adopted:** (ii).
- **Reason:** D18: a row cut at the cap in a no-tags lineage is delivered; the user received the text, and it is read like any delivered row. Under (i) the frozen V6_DEFS reads the length line as "nothing was delivered", so the readers of those traces are told the opposite of what the typed view's own DeliveredText holds (amendment 12.3, "Declared: what this re-read can show"). CLAUDE.md section 2 rule 2: trace readers see the reasoning and the delivered segment as typed views; for a turn delivered whole the delivered segment is the turn itself, and the builder's closing note states what the view knows, never more. (ii) also matches step 2r's design text (Revision 18), which says that a turn delivered whole and cut at the cap carries no note.
- **Depends on it:** step 2r (97b71b1; `scripts/recognition_v5_pilot3.py` `blind_text_typed`; `notes/typed_ingestion_design_2026-10-15.md`, Revision 18); D22 (its reconciliation, recomputed under (ii) by `scripts/reader_study_reconcile_2r.py`); D18; `notes/prereg_reader_study_2026-10-17.md` amendments 12 (12.3) and 14; CLAUDE.md section 2 rule 2.
- **Registry scope** (21 Oct): none: the closing note is text of the reader file the harness builds; no read rule, reason, view, cell or reward rule is registered.

## D24

- **Date:** 2026-10-23. **Authority:** adopted under the owner's delegation of 23 Oct 2026 ("we need to do whatever will be best for the paper work and needed runs", chat of 23 Oct 2026, as the orchestrating session relayed it; his whole sentence is in the Confirmation section) and entered by his dated line there; recorded the same day under the standing delegation.
- **Decision:** the no-claim stratum's rows: which delivered replies D10's no-claim stratum holds, on the two axes design Revision 24 drafted as the proposed D24 (Revision 23 drafted its first axis).
- **Scope:** D10's echo diagnostic and the label-blind column (design 2.7): the rows the echo diagnostic splits by gold label in every AbstentionBench cell whose judge shows the gold label, and the rows the label-blind column reports as the stratum.
  - The stratum is read by content from the delivered text under the primary rule id and the item's own question. No length or count enters it, and it never decides a verdict (2.7).
  - In code it is `no_claim_stratum(text, question)` in `withholding/score/abstention_judge.py`. As built on 23 Oct it inherits `one_word_reply`'s exclusion of every word of the judge's template, which this record lifts. The step that applies this record changes that function and regenerates `results/_ingest/step3_label_blind_echo_2026-10-23.{md,json}` by its command (`scripts/typed_step3_gpu.py echo`).
  - Under the adopted option the stratum holds 4,241 rows: the 2,035 of the stratum as built, and the 2,206 one-word replies whose core is a word of the judge's template (`template_word_reply`: "yes" 1,653, ALCUNA 1,648; "no" 534, ALCUNA 532; "high", "response", "assistant"), none of which names an option its item lists (the echo report, "One-word replies left out as template words").
  - Until D25's run gives the 2,206 template-word rows their label-blind lines, they carry label-shown verdicts only, and the echo table prints their label-removed side as not run.
- **Options:** two axes (design Revision 24; rows from the echo report, "The proposed D24's options").
  - Axis 1, listed options: (a) one-word replies that name no option their item lists (`no_claim_stratum`); (b) the one-word set the label-blind arm ran on (`one_word_reply`), listed-option replies in; (c) every one-character core out, digits as well as letters.
  - Axis 2, template vocabulary: the judge's template words out, as built and run; or in, as section 2.7 words the stratum, which excludes only "the judge prompt's abstention words and single letters".
  - Rows, template words out / in: (a) 2,035 / 4,241; (b) 14,896 / 17,102; (c) 2,030 / 4,236.
- **Adopted:** (a) with the template-word replies in: one-word replies that name no option their item lists, the judge's template words not excluded (4,241 rows).
- **Reason:** a reply that names a listed option is a claim the judge can read. 12,861 of the arm's 14,896 one-word replies name one (WorldSense 12,859), and WorldSense's option (3) is "is it impossible to decide", the benchmark's own abstention choice, so under (b) genuine abstentions would be read as echo. (c) reads "single letters" as one-character cores: it drops one-digit answers to items that list no options and keeps tagged listed-option replies (design Revision 23). "Yes" and "no" to ALCUNA's yes-or-no biology questions are claims. The review that defined the stratum kept a template word ("ambiguous", review item 13), and 2.7's registered wording excludes only the template's abstention words (CLAUDE.md section 2 rule 7: the registered rule wins). The "no" replies hold the sharpest label-shown split in the one-word set: 184 of 185 should-abstain and 18 of 349 answerable replies judged abstained, the split D10 exists to test. The 2,206 template-word rows get their label-blind line from D25's run.
- **Left open:** 9 of the 2,206 template-word replies are a closing tag alone ("</response>", "</assistant>"), with no word once their markup is removed, and they are inside the 4,241 by the count. Whether markup alone is an empty reply (CLAUDE.md section 2 rule 5: a judge never receives content-free input) is a question for OD-2 and the delivery rule, not for this record (design Revision 24, "Seen, not decided here").
- **Depends on it:** `notes/typed_ingestion_design_2026-10-15.md` at Revision 24: `:765` (2.7, the no-claim stratum), `:1286-1288` (step 3, the label-blind judge), Revision 23 (the listed-option axis) and Revision 24 (the template-vocabulary axis); D10; D25; `withholding/score/abstention_judge.py` (`one_word_core`, `one_word_reply`, `template_word_reply`, `names_listed_option`, `no_claim_stratum`); `scripts/typed_step3_gpu.py echo`; `results/_ingest/step3_label_blind_echo_2026-10-23.{md,json}`.
- **Registry scope** (23 Oct): none: the stratum is a content rule over delivered rows that the echo diagnostic and the label-blind column read (design 2.7); no read rule, reason, view or cell is registered.

## D25

- **Date:** 2026-10-23. **Authority:** adopted under the owner's go and delegation of 23 Oct 2026 ("you can run whatever will be within those limits and boundaries!" and "we need to do whatever will be best for the paper work and needed runs", chat of 23 Oct 2026, as the orchestrating session relayed them; his whole sentence is in the Confirmation section) and entered by his dated line there; recorded the same day under the standing delegation. It adopts D10's option (b), which D10 kept for the case its echo diagnostic flags.
- **Decision:** D10's extension: the label-blind judge runs on every AbstentionBench row that delivers under the primary rule id, in every directory of the step 3 batch, as the arm `label_blind_all`.
- **Scope:** step 3. The run is prepared by the typed chain's step 3 workflow (a new arm of `scripts/typed_step3_gpu.py`) and launched by the orchestrator on the Modal workspace of the step 3 batch under a cap below the dashboard balance of that day (the owner's go of 23 Oct, "run whatever will be within those limits and boundaries").
  - The judge config is D10's label-blind one (the template of record with its three mentions of the gold label removed, `abstention_judge.label_blind_template`), on the DeliveredText under the primary rule id.
  - Its lines feed a label-blind column per cell, beside the primary column, and the per-cell echo table (design 2.7), whose stratum is D24's.
  - The 2,206 template-word rows that D24 brings into the stratum are among its rows, so their label-blind lines come from this run.
  - It changes no primary verdict. The primary column stays the label-shown judge of record on the DeliveredText (W2.1), and the label-blind lines are written under their own file names (CLAUDE.md section 2 rule 5: a re-judge writes new file names).
- **Options:** (a) run on every delivered row now; (b) run on the 2,206 template-word rows only (USD 0.12, the echo report's price at the batch's calibration); (c) hold.
- **Adopted:** (a).
- **Reason:** D10's condition is met. On the no-claim stratum the verdicts follow the gold label: 214 of the 270 should-abstain replies judged abstained with the label shown are judged answered when it is removed (199 of them ALCUNA), and 0 move the other way (the echo report). The paper's AbstentionBench recall cells rest on the label-shown judge, and ALCUNA one-word rows sit in them; the label-blind column on every delivered row decides whether those cells stand. (b) completes the stratum only, while the judge sees the gold label on every row of a cell. (c) leaves the flag D10 set unanswered in the cells the paper cites.
- **Limits:** this record launches nothing and allows no spend beyond the owner's go. The run starts only after its build's dry run prints the requests, identity reuses and price (design step 3, Proof). Its cap stays below the dashboard balance, and a job is stopped at 1.5 times its own estimate (the owner's Modal rule; day log, 23 Oct 2026, 12:20 WEST). D10's estimate for the whole run was about USD 12.
- **Depends on it:** D10 (its option (b) and its condition); D24 (the stratum the echo table reads); D8 (step 3's spend); `notes/typed_ingestion_design_2026-10-15.md` at Revision 24: `:765` (2.7, the echo diagnostic), `:1286-1288` and `:1298` (step 3: the label-blind judge and its cost), Revisions 23 and 24; `scripts/typed_step3_gpu.py` (`build`, `launch`, `ingest`, `echo`); `withholding/typed/step3.py` (`LLAMA_ARMS`, the file names); `withholding/score/abstention_judge.py` (the step 3 block).
- **Registry scope** (23 Oct): none: the label-blind column is its own MetricSpec with its own judge config (D10; design 2.6, 2.7); it reads DeliveredText under the table's rule D id, so no read rule or cell is authorised here.

## Notes, 23 Oct 2026

Session text, not a record. The loader reads only `## OD-n` and `## Dn` headings, so nothing here is pinned, no pinned sha moves (design 2.8, Revision 6: a section appended after the last record), and nothing here changes D24, D25 or the owner's line of 23 Oct. It sets down, from the repo and the orchestrating session's chat, when his words of 23 Oct came and which options were recommended to him before them (two verifier findings on the step that recorded D24 and D25, a55793c). Changing either record's text still needs his next dated line.

- **When his words came.** The orchestrating session's transcript records his message at 22:52:24 CEST, 23 Oct. Before it: the echo report with D24's options on both axes (`results/_ingest/step3_label_blind_echo_2026-10-23.{md,json}`, written 22:26:20); that session's reply to him at 22:36:57, which put D24's two axes (with examples) and D10's extension to him, each with a recommendation; b34c8a0 (design Revision 24 and the day log's 22:45 entry) at 22:38:52. After it: 8d67846 (the day log's entry headed "22:20 CEST", the owner's go) at 22:55:28 and a55793c at 23:08:41. So his line's order holds: he wrote after the fix rounds had reported the echo on the no-claim stratum and the two-axis draft of D24. The day log's "22:20 CEST" for his go is wrong; its entry of 23 Oct, 23:50 CEST, corrects it. His message opened with a question on the reader study's CLI login; the words his line quotes are the rest of it, verbatim.
- **D24 adopts the recommendation on record.** Design Revision 24: "Recommendation: (a)(ii), with the label-blind run on the 2,206 rows." The day log's 22:45 entry, owner-pending item 1: "Recommended: (a)(ii), 4,241 rows, with the label-blind run on the 2,206 added rows". The orchestrating session's reply of 22:36:57: "My recommendation: (a), with the template-word replies included." D24's adopted option is that (a)(ii), 4,241 rows.
- **D25 and the recommendation on the extension.** No file in the repo held one. Revision 23 leaves the extension "Not decided here"; the day log's 21:25 entry, item 2, gives its cost and its need of his go and recommends nothing; the 22:45 entry's item 2 is "unchanged from the 21:25 entry". The one recommendation put to him is in the orchestrating session's reply of 22:36:57: "My recommendation: run it, it decides whether the headline abstention numbers stand." That reply put the balance lower than his words did and said the run might wait for credits or start with the ALCUNA-heavy directories; his words gave the balance as it stood. D25 adopts D10's option (b), the run on every delivered row, on that recommendation and the session's reading of his delegation.
- **D25's not-taken (b) is the run Revision 24 recommended with D24.** D25 lists as not taken "(b) run on the 2,206 template-word rows only (USD 0.12, the echo report's price at the batch's calibration)", which is the label-blind run Revision 24 and the 22:45 entry recommended beside (a)(ii). Those 2,206 replies are delivered AbstentionBench rows under the primary rule id in the batch's directories (Revision 24, "The finding"), so they are among `label_blind_all`'s rows, and D25's run gives them their label-blind lines (D24, Scope). The recommended run is folded into the wider one, not dropped. Should `label_blind_all` not run, Revision 24's recommendation of the 2,206-row run stands as written.
