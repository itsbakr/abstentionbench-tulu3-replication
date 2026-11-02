# AbstentionBench on Tülu 3 8B: the code and scores behind my reproduction report

Ahmed Bakr, 2 November 2026

## What this is

This folder holds what my reproduction report (submitted separately) rests on. The report asks whether my pipeline gives back AbstentionBench's Tülu 3 8B result across the three
training stages (SFT, DPO, RLVR) on the benchmark's fast subset, graded by the paper's own judge, Llama 3.1 8B
Instruct. It then judges the same 25,248 answers again with the answer-key line removed from the judge prompt, and
compares the judge with my own hand labels.

It is a curated copy of my private research repository at commit `1f167c2`
(`1f167c248e93b9047701507f9b328df2f5e50946`, 1 Nov 2026). Every code file here is a byte-for-byte copy of that commit,
with no edits and no header added, except `scripts/mean_over_21_datasets.py`, written for this folder. `MANIFEST.json` gives each file's sha256, its source path and how it got here
(verbatim, filtered, or written for this folder). It does not list itself.

## What is in here

- `scripts/export_abstentionbench.py`: writes the fast-subset prompts through the Inspect port (`inspect_evals`).
- `scripts/run_tulu_n4.sh`: the preregistered run. Three stages generate in parallel on Modal (one H100 each, four
  answers per question), then the judge runs on each stage, then the report.
- `withholding/run/modal_vllm.py`: the Modal and vLLM runner used for both the models and the judge.
- `withholding/score/abstention_judge.py`: the judge prompt builder and verdict parser, including the
  label-line-removed template (`LABEL_BLIND_CUTS`, `label_blind_template`, and the `step3_*` functions that build its
  requests). `withholding/score/record_file.py` is the writer that refuses to overwrite a file built from other content.
- `withholding/typed/`: the typed layer the runner and the judge builder import (models, adapters, ingest, legacy,
  registry, dispatch, and the two pin files the registry checks). `notes/typed_layer_decisions_2026-10-15.md` is here
  only because the registry reads it at import and checks it against `owner_decisions.pins.json`. It is a redacted
  copy: my verbatim chat lines, Modal workspace names and balances are withheld, and the pins file was recomputed for
  the copy (see What is left out).
- `withholding/analysis/abstention_report.py` and `withholding/analysis/bootstrap.py`: the per-dataset tables and the
  paired item bootstrap (10,000 resamples, seed 13, 95 percent percentile interval).
- `withholding/score/human_check.py`: draws the hand-check sample and scores the judge against my labels.
- `scripts/mean_over_21_datasets.py`: prints the 21-dataset means of both judge columns and the paper's, written for this
  folder.
- `third_party/abstentionbench/`: seven files from the authors' repository, unedited, with a `NOTICE` (upstream
  facebookresearch/AbstentionBench at commit e291841) and the upstream licence, CC BY-NC 4.0, vendored as `LICENSE`.
- `notes/prereg_tulu.md`: the preregistration, committed before the main run, with its one amendment (23 Oct).
- `results/tulu_n4/`: `report.md` and `VALIDATION.md` as they stand in the private repository, and per stage
  (`sft`, `dpo`, `rlvr`) both judge columns: `scores.jsonl` (the paper's prompt, answer key shown) and
  `scores_abstain_label_blind_all_post-2d.jsonl` (the same judge, answer-key line removed). 8,416 lines each.
- `results/tulu/human_check/`: the hand-check key, my labels and the sheet I labelled from (GPQA rows removed, see
  below), and `score_59_labels.txt`, the score command's output on all 59 labels.
- `requirements.txt` (the no-GPU path) and `requirements-gpu.txt` (the GPU path).

I checked the module list with a fresh venv: every module in `withholding/` imports, and the four registry specs of the
run resolve (Tülu SFT, DPO, RLVR and the judge). No module is here that those imports do not load.

## Regenerate the tables without a GPU

From this folder, Python 3.12. I ran exactly these on 2 Nov 2026 (with `python3.12 -m venv`, and again with uv):

```
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
mkdir -p regenerated
.venv/bin/python -B -m withholding.analysis.abstention_report --no-typed \
  --stage SFT=results/tulu_n4/sft/scores.jsonl \
  --stage DPO=results/tulu_n4/dpo/scores.jsonl \
  --stage RLVR=results/tulu_n4/rlvr/scores.jsonl \
  --out regenerated/report_label_shown.md
.venv/bin/python -B -m withholding.analysis.abstention_report --no-typed \
  --stage SFT=results/tulu_n4/sft/scores_abstain_label_blind_all_post-2d.jsonl \
  --stage DPO=results/tulu_n4/dpo/scores_abstain_label_blind_all_post-2d.jsonl \
  --stage RLVR=results/tulu_n4/rlvr/scores_abstain_label_blind_all_post-2d.jsonl \
  --out regenerated/report_label_line_removed.md
.venv/bin/python -B -m withholding.score.human_check score results/tulu/human_check
.venv/bin/python -B scripts/mean_over_21_datasets.py
cmp <(sed -n 1,46p results/tulu_n4/report.md) regenerated/report_label_shown.md && echo identical
```

The last line needs bash or zsh. `--no-typed` leaves out the report's last section ("Three views"), which needs the model outputs and the private
repository's ingestion sidecars; neither is here (see below). `-B` keeps `__pycache__` out of the folder. The only
dependency is numpy.

## What the regeneration gave

- Answer key shown: `regenerated/report_label_shown.md` is byte-identical to lines 1 to 46 of
  `results/tulu_n4/report.md`. That is every per-dataset recall (22 datasets, ours and the paper's), the pooled recall
  0.517, 0.574, 0.570, the mean over datasets 0.548, 0.611, 0.606 (paper 0.416, 0.504, 0.488), the deltas
  +0.056 [+0.040, +0.073] and -0.004 [-0.018, +0.010], the false-abstention rates 0.182, 0.174, 0.155 and the
  precision 0.676, 0.708, 0.730.
- Answer-key line removed: the regenerated pooled recall 0.431, 0.457, 0.441 (line 30), false abstention 0.258, 0.257,
  0.245 (lines 44 to 46) and the deltas +0.026 [+0.010, +0.042] and -0.015 [-0.028, -0.003] (lines 37 and 38) equal
  the "label line removed" rows of `results/tulu_n4/report.md` (lines 61 to 63, 67 to 69, 74 and 76). The per-dataset
  rows and the 22-dataset mean (0.465, 0.494, 0.477) are not printed in `report.md`; they match the private
  repository's `paper/RESULTS.md` line 42.
- Not regenerated here: the rest of the "Three views" section of `report.md` (lines 48 onward): the delivered-only and
  bracket views, the undelivered and cut-at-cap counts, the false-abstention deltas (lines 77 to 80), the echo table and
  the scorer stamps. For this run no row is undelivered and none is unparsed, so every view equals the all-rows value
  that the regenerated tables print.
- `VALIDATION.md`: criterion 1 (line 17) and the RLVR delta, precision, false abstentions and per-dataset directions of
  line 22 are regenerated, and so is the level offset of line 24 (`report.md` line 31). Criterion 2 (lines 7 to 9, 11
  and 18) has no script in the repository; I re-derived it from the shipped scores and the paper's CSV and got 14, 19
  and 14 of 21, with every listed miss and both numbers of each miss as written. Criterion 4's "0 unparsed of 25,248"
  holds in the shipped score files (every line has a Yes or No verdict). Its length-cut shares need the model outputs;
  the cut-at-cap counts that `report.md` prints (SFT 11 + 4, DPO 1, RLVR 1, of 8,416 each) give the same 0.18, 0.01
  and 0.01 percent. Criterion 3 needs the Instruct pilot, which is not here.
- Hand check: `score_59_labels.txt` (run on the unfiltered files of commit 1f167c2) reads n=59, accuracy 0.729,
  precision 0.758, recall 0.758, kappa 0.450, AC1 0.465. On the shipped files, with the one GPQA label removed, the same
  command gives n=58, accuracy 0.724, precision 0.758, recall 0.758, kappa 0.438, AC1 0.459.

## Where each number in the report comes from

Line numbers are those of the report I submitted. "Regenerated" means a command above prints it.
"Re-derived" means I recomputed it from the shipped files while building this folder, but no shipped script prints it.
"Private" means it comes from a file of the private repository at commit 1f167c2 that is not in this folder.

| Line | Number | Comes from | Status |
|---|---|---|---|
| 7, 11 | paper +0.078 then -0.013 | Mean over the 31 result rows per stage in `third_party/abstentionbench/abstention_performance.csv`; written into `notes/prereg_tulu.md` lines 17 and 18 before the run; printed by the private `scripts/paper_results_md.py` into `paper/RESULTS.md` line 29 | Re-derived: +0.0783, -0.0129 |
| 7 | paper table 0.43, 0.53, 0.51 | The paper's Table 4 (arXiv 2506.09038v1), recorded in my private fidelity review | Private |
| 9, 19 | pilot +0.036 [+0.007, +0.065], +0.021 [-0.005, +0.047] | `notes/prereg_tulu.md` lines 17 and 18: the one-sample pilot before its 80 GPQA rows were added (851 should-abstain items). See the corrections below | Private (pilot files not here) |
| 11 | pass lines (0.1, 15 of 20, 15 of 22, 1 percent) | `notes/prereg_tulu.md` lines 23 to 26 | In this folder |
| 13 | 2,104 questions, 22 datasets, 891 unanswerable | `notes/prereg_tulu.md` line 9; the score files hold 2,104 item ids over 22 datasets, 891 of them should-abstain (`report.md` lines 8 to 29 and 37) | 22 and 891 regenerated; 2,104 re-derived (item ids) |
| 13 | four answers, temperature 0.8, top-p 0.95, 4,000 tokens, H100; judge at temperature 0 | `scripts/run_tulu_n4.sh` lines 13 to 15 and 23 to 24; `notes/prereg_tulu.md` lines 11 and 12 | In this folder |
| 13 | 10,000 redraws, middle 95 percent | `withholding/analysis/bootstrap.py` lines 12 to 34 | In this folder |
| 20 | Instruct 0.72 vs port 0.66 vs paper 0.65; 12 of 21 | Private `results/tulu/report_instruct.md` line 30 (0.722 / 0.651) and `notes/2026-10-02.md` line 45 (port 0.660, 12 of 21); `VALIDATION.md` line 19 | Private |
| 21 | 99.2 percent identical | Private `notes/2026-10-02.md` line 44: 2,008 of 2,024 pilot SFT verdicts, bf16 against float16 judge | Private |
| 22 | 11.5 minutes; 25,248 answers, all readable | `VALIDATION.md` lines 3 and 20; 3 x 8,416 score lines, none unparsed | Count re-derived; 11.5 minutes private (run logs) |
| 22 | 19 of 21 (DPO), 14 of 21 (SFT, RLVR) | `VALIDATION.md` lines 7 to 9 and 18. The CSV column it compares with is the model's abstention precision, not the judge's (see corrections) | Re-derived: 14, 19, 14 |
| 23 | 4.9 percent change with two start markers | Private `notes/2026-10-02.md` line 2261: 1,245 of 25,248 (the bos2 score files are not here) | Private |
| 26 | USD 0, about USD 6 credit, about 1.5 H100 hours, 33 minutes | 33 H100 minutes: `VALIDATION.md` line 3. The totals are mine; I found no file that sums them | Not re-derived |
| 32 | paper +0.088, -0.016 over the 21 shared datasets | Mean of the paper's per-dataset recall over the 21 datasets it reports at all three stages (the `report.md` rows less `self_aware`, line 25); private `scripts/paper_results_md.py` lines 511 to 541, `paper/RESULTS.md` line 28 | Regenerated by `scripts/mean_over_21_datasets.py`: +0.088, -0.016 |
| 32 | paper's table +0.10, -0.02 | Differences of Table 4's 0.43, 0.53, 0.51 | Private |
| 33 | mine +0.058, -0.003, same 21 datasets | Same mean on our side; private `paper/RESULTS.md` line 27 | Regenerated by `scripts/mean_over_21_datasets.py`: +0.058, -0.003 |
| 34 | +0.056 [+0.040, +0.073], -0.004 [-0.018, +0.010] | `results/tulu_n4/report.md` lines 37 and 38 | Regenerated |
| 36 | false refusals 0.174 to 0.155; MuSiQue and SQuAD 2.0 drop; MMLU Math flat | `report.md` lines 45 and 46; line 22 (0.226 to 0.201), line 27 (0.505 to 0.412), line 20 (0.319 to 0.330); the paper's three largest drops are named in `notes/prereg_tulu.md` line 18 | Regenerated |
| 38 | mine 0.55, 0.60, 0.60 against 0.42, 0.50, 0.49; "0.11 to 0.13 above" | 21-dataset means, private `paper/RESULTS.md` line 43 | Regenerated by `scripts/mean_over_21_datasets.py`: 0.546, 0.603, 0.600 and 0.416, 0.504, 0.488; the gaps are 0.130, 0.100, 0.112 (see corrections) |
| 40 | 59 of 160 labelled; 73 percent agreement; kappa 0.45; 27 percent disagreement | `results/tulu/human_check/score_59_labels.txt` line 1, printed by `withholding/score/human_check.py` line 89; the key had 160 rows | Regenerated on 58 labels here (0.724, 0.438) |
| 40 | the paper's 0.88 | `human_check.py` line 90: the paper's judge accuracy on 300 labels (its Table 1). It compares with my 73 percent, not with the kappa | In this folder |
| 44 | 0.46, 0.49, 0.47 with the line removed | 21-dataset means of the label-line-removed column; private `paper/RESULTS.md` line 43 | Regenerated by `scripts/mean_over_21_datasets.py`: 0.459, 0.486, 0.472 |
| 44 | +0.026 [+0.010, +0.042]; -0.015 [-0.028, -0.003] | `report.md` lines 74 and 76 | Regenerated |
| 44 | 14 of 22 datasets where an empty reference list gives the key away | `report.md` line 54, printed by the typed section from the prompt rows | Not regenerable here (needs the prompts) |
| 44 | 274,184 answers, 11 percent changed, 98 percent toward the key | Private `notes/2026-10-02.md` line 2648: 30,402 of 274,184 delivered rows over every result directory the paper cites, 29,821 toward the label. For the Tülu run alone the shipped files give 2,513 of 25,248 (10.0 percent), 2,457 of them (97.8 percent) toward the key | Private; Tülu part re-derived |
| 44 | a bare "no": 184 of 185 and 18 of 349 | Private `results/_ingest/step3_label_blind_echo_2026-10-23.json`, `template_word.by_word.no`: 534 one-word "No" replies over 150 result directories, 532 from ALCUNA and 2 from SQuAD 2.0 | Private |
| 46 | the figure | The 21-dataset means above (paper; key shown; key line removed). No plotting script exists in either repository | Values re-derived |
| 52 | 6 disagreements, 5 sided with the no-key judge | The 59 labels joined to the pilot's label-line-removed verdicts (private `results/tulu/<run>/scores_abstain_label_blind_all_post-2d.jsonl`) | Re-derived from private files: 6 and 5 |
| 56 | 1,081 answers, 572 in the first wave | Private `results/abstentionbench/human_draw/draw.md` line 47 | Private |
| 56 | 30,402 plus 10,000; 70 and 90 percent | 30,402 as line 44; the 10,000 agreeing rows are in the private `notes/2026-10-02.md` line 3209; the 70 and 90 percent lines are the report's own plan | Plan |

The 21-dataset means are the plain mean of the per-dataset rows that have a paper value; `scripts/mean_over_21_datasets.py`
prints them for both judge columns and the paper. Done by hand from the
3-decimal rows of the regenerated tables they give the same numbers, except that the DPO to RLVR difference on our side
comes out at -0.0036 instead of -0.0035 (full precision -0.00346), so -0.004 rather than the report's -0.003.

## The GPU path on Modal

I did not rerun this for the export: a GPU launch needs my go and a stated cost. What I did check, on CPU: in a fresh
venv the four registry specs resolve after a clean tokenizer fetch (with the fix in step 2), and on the private
repository's stored outputs the shipped judge code rebuilds all 25,248 judge prompts byte for byte, parses the stored
judge replies into the same 25,248 verdicts as `scores.jsonl`, and rebuilds every stored label-line-removed prompt
(23,729 request rows) byte for byte. Every one of the 25,248 label-line-removed score lines names the request identity
and text hash that the shipped code gives its answer.

The code here is that of commit 1f167c2, newer than what ran on 4 Oct. The runner now refuses to start without a
registry entry for the model and writes more fields on each row. `build` and `parse` now read the delivered text under
the typed rule; the writers that produced the 4 Oct `scores.jsonl` are still in `abstention_judge.py` as `build-legacy`
and `parse-legacy`. On the stored outputs the new and old paths give the same prompts and verdicts (above).

1. Environment (Python 3.12; a Modal account; a Hugging Face token with access to meta-llama/Llama-3.1-8B-Instruct,
   saved by `hf auth login` in `~/.cache/huggingface/token`, which `run_tulu_n4.sh` reads):

   ```
   python3.12 -m venv .venv
   .venv/bin/pip install -r requirements-gpu.txt
   .venv/bin/modal setup
   ```

2. Tokenizer files for the typed registry, which checks every registered model's tokenizer at import (no weights).
   The pins were derived from a cache that did not hold two `special_tokens_map.json` files, so a clean fetch must drop
   them or the registry refuses to load:

   ```
   export WITHHOLDING_TOKENIZER_CACHE="$PWD/.tokenizer-cache"
   .venv/bin/python -B -m withholding.typed.registry fetch
   rm "$WITHHOLDING_TOKENIZER_CACHE"/models--allenai--Llama-3.1-Tulu-3-8B-SFT/snapshots/f2a0b46b0cfda21003c6141b1ff837b7e165524d/special_tokens_map.json
   rm "$WITHHOLDING_TOKENIZER_CACHE"/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/0e9e39f249a16976918f6564b8830bc894c89659/special_tokens_map.json
   .venv/bin/python -B -c "import withholding.typed.registry"
   ```

   Keep `WITHHOLDING_TOKENIZER_CACHE` exported in the shell that runs step 4.

3. Prompts (inspect_evals 0.23.0, the fast subset, seed 42 for the port's subsampling):

   ```
   .venv/bin/python -B scripts/export_abstentionbench.py --out results/tulu/prompts.jsonl
   ```

   The port shuffles GPQA's answer choices without a seed, so the 80 GPQA prompts and their ids will differ from the
   run's, and the file will not match the sha256 in `notes/prereg_tulu.md` line 9.

4. Move the shipped results aside (the writers never overwrite a file built from other content, and the runner resumes
   from any outputs it finds), then run the chain:

   ```
   mv results/tulu_n4 results/tulu_n4_shipped
   zsh scripts/run_tulu_n4.sh
   ```

   The script loads each model at revision `main`; the preregistration records the commits `main` pointed to on
   4 Oct (`notes/prereg_tulu.md` lines 10 and 12). Its last step calls the report without `--no-typed` and stops with an
   ImportError here, because the typed report modules are not in this folder. Run the report as in the no-GPU section,
   with the new `scores.jsonl` files.

5. The label-line-removed re-judge has no runnable driver here. In the private repository it ran as one batch over all
   147 result directories (`scripts/typed_step3_gpu.py`, 2,248 lines, tied to that repository's batch manifest and
   spend guard). The request it sends for each answer is `abstention_judge.build_abstention_request_step3` with the
   arm `label_blind_all`, style `paper`, max_tokens 5, temperature 0, float16, one start marker; each reply was
   typed with `abstention_reply_typed` and written by `step3_abstain_line`.

vLLM runs inside the Modal image that `modal_vllm.py` builds (`vllm>=0.10`, not pinned). The 4 Oct run did not record
its vLLM version; the 25 Oct re-judge rows record 0.31.0.

## What is left out, and why

- GPQA text. GPQA asks that its examples not be posted online. Every file here that carries question or answer text has
  its GPQA rows removed: `results/tulu/human_check/to_label.csv` (3 of 160 rows), and for consistency `key.jsonl`
  (3 of 160) and `labels.jsonl` (1 of 79 lines). The score files keep their GPQA rows (320 per stage), because a score
  line holds ids, the dataset name, the gold label, hashes and the judge's Yes or No, and no question or answer text;
  that is why the tables regenerate exactly.
- The model outputs, the prompts, and the judge prompt and reply files. They carry the question text (GPQA included).
  The GPU path regenerates them.
- From the decisions note, my verbatim chat lines, the Modal workspace names and the balances of the day. The
  registry only checks the note's section hashes, so the copy was re-pinned; nothing a reader of this code needs is
  changed. The hand-check sheet `to_label.csv` carries benchmark question text under the datasets' own licences
  (WorldSense CC-BY-NC 4.0, some unspecified), redistributed here for non-commercial research.
- The rest of the private repository. It holds other experiments, third-party text I have no licence to publish,
  Modal run logs and spend logs that name accounts, caches and reader-study data, and it is far larger than this.
  Of the code these numbers touch, I left out the typed report modules (the "Three views" section), the step 3 batch
  driver, and `scripts/paper_results_md.py`, which builds the paper's whole results file and computes the 21-dataset
  means; each needs files that are not here.
- Two verbatim files contain en or em dashes, and I left them as they are: line 42 of
  `third_party/abstentionbench/evaluation_judge_prompts.py` (inside the published judge prompt, which the judge must
  read byte for byte) and `results/tulu/human_check/to_label.csv` (seven, four en dashes and three em dashes, on six lines of question and answer text).

## Compute and cost

- Main run: 11.5 minutes wall clock with the stages in parallel, about 33 H100 minutes in all (`VALIDATION.md` line 3).
- The 4 Oct pilot measured about USD 0.25 per one-answer generation pass and USD 0.20 per judge pass on one H100
  (private `notes/2026-10-02.md` line 38).
- The report's totals for this work: USD 0 out of pocket, about USD 6 of Modal startup credit, about 1.5 H100 hours,
  plus a few hours of my labelling.
- Regenerating the tables here: under a minute on a laptop, no GPU, no network after the numpy install.

## Corrections found while building this

- Report lines 9 and 19: the pilot deltas +0.036 [+0.007, +0.065] and +0.021 [-0.005, +0.047] are from before the
  pilot's GPQA rows were added (851 should-abstain items). With them (891 items) the pilot gives +0.028 [+0.000, +0.056]
  and +0.021 [-0.004, +0.047] (private `results/_archive/2026-10-17/tulu/report.md` lines 37 and 38; I reran it with
  the shipped report code and got the same).
- Report line 38: the 21-dataset gaps are 0.130, 0.100 and 0.112, so "0.10 to 0.13 above", not "0.11 to 0.13".
- Report line 22 and `VALIDATION.md`: the paper's CSV `precision` column is the model's abstention precision, not a
  judge precision (my fidelity review, finding F10). The comparison is like for like (ours is the same quantity), but
  "judge precision" is the wrong name.
- Report line 44: 532 of the 534 bare "No" replies are ALCUNA's; 2 are SQuAD 2.0's.
