# Preregistration: Tülu 3 8B stage validation on the AbstentionBench fast subset

Written 4 October 2026, before the four-sample run. A one-sample pilot of the same three stages was run earlier today (results/tulu/report.md) and is disclosed below; this document fixes the configuration and the success criteria for the run that counts.

## Purpose
Validate the pipeline (export, generation, published judge, metric, paired bootstrap) against numbers that already exist, before any checkpoint whose numbers do not exist (Nemotron-Cascade-8B) is run.

## Fixed configuration
- Prompt set: AbstentionBench fast subset as exported by inspect_evals 0.23.0 (100 items per dataset, 22 datasets incl. GPQA), 2104 items, 891 should-abstain. sha256 of results/tulu/prompts.jsonl at preregistration: 0c5d6914bef1dbb1e6017438cc965930ad7042a19b436b177269feeeb9a24ac5
- Checkpoints (Hugging Face commits from results/manifest.json): SFT f2a0b46b0cfda21003c6141b1ff837b7e165524d, DPO a7beb67e33ffd01cc87ac3b46cadc1000985b8db, RLVR 666943798adbde0b1aff34626007e26986a3c107. All three share chat template sha256 ac7498a36a719da630e99d48e6ebc4409de85a77556c2b6159eeb735bcbd11df.
- Generation: vLLM on one H100 per stage, float16, temperature 0.8, top_p 0.95, max_tokens 4000, no system prompt, tokenizer chat template, seed 13, four samples per item (n=4).
- Judge: meta-llama/Llama-3.1-8B-Instruct commit 0e9e39f249a16976918f6564b8830bc894c89659, float16, temperature 0, max_tokens 5, the paper's CoCoNot-style prompt verbatim, reference answers rendered as "[a; b]" or "[]" and the label as the Python bool, exactly as recipe/evaluation.py does. Verdict parsing: lowercase, strip " .,\n", exact yes or no, anything else unparsed and excluded (the paper's rule).
- Metric: per item, mean verdict over the four samples; recall = mean over should-abstain items; also precision and the abstention rate on answerable items, per dataset and pooled.
- Statistic: stage-to-stage delta of recall with a paired item bootstrap (10,000 resamples of items, 95 percent percentile interval), over the should-abstain items present in both stages. Reported alongside per-dataset tables. No correction across the two deltas (they are reported, not selected).

## Expectations, written before the run
- SFT to DPO: positive. Paper, mean over datasets: +0.078. Pilot (one sample): +0.036 [+0.007, +0.065].
- DPO to RLVR: small, sign uncertain. Paper: -0.013 (no error bars in the paper). Pilot: +0.021 [-0.005, +0.047]. The paper's clearest per-dataset drops are MuSiQue (0.185 to 0.119), SQuAD 2.0 (0.304 to 0.244) and MMLU Math (0.308 to 0.226); the pilot reproduced the direction on MuSiQue and MMLU Math and not on SQuAD 2.0.
- Precision rises at RLVR and the abstention rate on answerable items falls (paper and pilot agree).
- Absolute recall per dataset is expected to sit above the paper's full-set numbers on many datasets, as the Inspect port's own fast-subset run of Llama-3.1-8B-Instruct does; the comparator for levels is the port's README table where available, not the paper's column.

## What counts as a validated pipeline
1. The SFT to DPO interval excludes zero and is positive.
2. Judge precision per dataset is within 0.1 of the paper's for at least 15 of the 20 datasets the paper reports.
3. The Llama-3.1-8B-Instruct diagnostic run lands within 0.1 of the Inspect port's README value on at least 15 of its 22 datasets.
4. Unparsed judge verdicts under 1 percent; outputs cut off by the length limit under 1 percent (reported, counted as censored not refusal).
The DPO to RLVR delta is reported with its interval whatever it shows; it is not a validation criterion because the paper's own effect is within the noise of this sample size.

## Disclosed deviations from the paper
Fast subset instead of the default subsample (cost); four samples per item instead of one (variance); judge max_tokens 5 instead of 100 (verdicts were exactly Yes/No in the pilot: 2,023 of 2,024); vLLM 0.10+ instead of 0.6.4; seeded sampling.
- **Amendment 1, 23 October 2026 (D18).** Criterion 4's "counted as censored not refusal" for outputs cut off by the length limit (line 26) is replaced by D18 (`notes/typed_layer_decisions_2026-10-15.md`, adopted 17 Oct 2026 under the owner's agreement of that day, "I agree with all of the other decisions"): censored means undelivered under the table's primary rule D id, so a row cut at the length limit in this lineage (no think block) is delivered and read like any delivered row, its cut count printed per cell (`cut_at_cap_n`); the reading with length-cut samples dropped stays beside it as a finished-only sensitivity. Criterion 4's share (under 1 percent) is reported as before. A deviation by design for the methods table and the fidelity ledger (W7.4).
