# AbstentionBench report (SFT, DPO, RLVR)

Recall = share of should-abstain items the judge marked as abstention (mean over samples per item).
Paper = the same number from AbstentionBench's results file for the matching Tülu 3 8B stage (scenarios pooled by mean).

| dataset | n should-abstain | SFT ours / paper | DPO ours / paper | RLVR ours / paper |
|---|---|---|---|---|
| alcuna | 47 | 0.750 / 0.414 | 0.777 / 0.524 | 0.819 / 0.492 |
| bbq | 51 | 0.784 / 0.448 | 0.843 / 0.659 | 0.838 / 0.621 |
| big_bench_disambiguate | 33 | 0.220 / 0.040 | 0.280 / 0.160 | 0.447 / 0.200 |
| big_bench_known_unknowns | 23 | 0.946 / 0.913 | 1.000 / 0.957 | 1.000 / 0.957 |
| coconot | 76 | 0.951 / 0.852 | 0.918 / 0.877 | 0.924 / 0.873 |
| falseqa | 57 | 0.522 / 0.432 | 0.553 / 0.413 | 0.539 / 0.399 |
| freshqa | 21 | 0.750 / 0.532 | 0.857 / 0.851 | 0.869 / 0.872 |
| gpqa | 40 | 0.456 / 0.325 | 0.425 / 0.175 | 0.356 / 0.225 |
| gsm8k | 45 | 0.789 / 0.687 | 0.822 / 0.754 | 0.833 / 0.745 |
| kuq | 47 | 0.553 / 0.538 | 0.681 / 0.647 | 0.676 / 0.634 |
| mediq | 46 | 0.016 / 0.015 | 0.098 / 0.028 | 0.125 / 0.029 |
| mmlu_history | 39 | 0.186 / 0.051 | 0.250 / 0.154 | 0.244 / 0.154 |
| mmlu_math | 47 | 0.282 / 0.278 | 0.319 / 0.308 | 0.330 / 0.226 |
| moralchoice | 45 | 0.467 / 0.257 | 0.456 / 0.278 | 0.428 / 0.263 |
| musique | 41 | 0.122 / 0.025 | 0.226 / 0.185 | 0.201 / 0.119 |
| qaqa | 54 | 0.528 / 0.361 | 0.565 / 0.481 | 0.574 / 0.425 |
| qasper | 7 | 0.857 / 0.747 | 0.929 / 0.949 | 0.893 / 0.962 |
| self_aware | 28 | 0.607 / - | 0.768 / - | 0.732 / - |
| situated_qa | 15 | 0.983 / 0.736 | 1.000 / 0.791 | 1.000 / 0.767 |
| squad2 | 54 | 0.241 / 0.161 | 0.505 / 0.304 | 0.412 / 0.244 |
| umwp | 53 | 0.307 / 0.289 | 0.283 / 0.318 | 0.283 / 0.316 |
| worldsense | 22 | 0.750 / 0.628 | 0.886 / 0.763 | 0.807 / 0.722 |
| **pooled (all should-abstain items)** | | 0.517 | 0.574 | 0.570 |
| **mean over datasets (paper's headline)** | | 0.548 / 0.416 | 0.611 / 0.504 | 0.606 / 0.488 |

## Stage-to-stage deltas (paired item bootstrap over should-abstain items, 10,000 resamples)

| from -> to | n items | delta | 95% interval |
|---|---|---|---|
| SFT -> DPO | 891 | +0.056 | [+0.040, +0.073] |
| DPO -> RLVR | 891 | -0.004 | [-0.018, +0.010] |

## Precision and abstention rate (all items)

| stage | abstention rate on answerable items (false abstentions) | precision |
|---|---|---|
| SFT | 0.182 | 0.676 |
| DPO | 0.174 | 0.708 |
| RLVR | 0.155 | 0.730 |

## Three views (typed cells, step 4)

Typed cells (design 2.7, step 4): every cell reads rule D `D@2026-10-15|close=first|stray=content|turn=cut_at_boundary|rlcr.close=last` (label post-2d, rule date 2026-10-15), issued by withholding.typed.report from the score records joined to the sealed texts. Views (OD-3, D18): all rows = an undelivered row counted as not the behaviour, an unparsed judge verdict excluded and counted (the preregs' reading); delivered only = undelivered and unparsed rows dropped (in a delta, from both sides of the pair); bracket = every undelivered and unparsed row valued as not the behaviour at one end and as the behaviour at the other. A row cut at the token cap that delivered text is delivered (D18) and counted. Budget-forced: not run (W4.2). Deltas: the all-rows delta with its interval (paired item bootstrap, 10,000 resamples, seed 13), the delivered-at-both delta (W8.5.2's finished-at-both under D18), and the worst-case bound (W8.5.2: b's low end minus a's high end, then b's high end minus a's low end) with each end's own interval. Quoted (D7 with D18): the point only when both ends of the bound, each read as a point and with its own interval, give the all-rows delta's preregistered label (with its direction where the prereg's test is directional); otherwise the bound, marked 'bracket only' (a cell labelled inconclusive or 'excludes 0, below SESOI' is always quoted as its bound, a bound of one value when no row is censored). 'pending' = a cell holding rows whose verdict is not on file for the text the rule delivers; it prints no number, with the rule label.

Prereg rule: notes/prereg_tulu.md registers no SESOI: its deltas are not_registered.

The benchmark's published judge prompt (third_party/abstentionbench, vendored byte for byte: notes/reviews/2026-10-14_abstentionbench_fidelity.md) shows the judge the gold label, and its reference list encodes the label too: it is the empty list exactly on the should-abstain items of 14 of the 22 datasets (alcuna, bbq, big_bench_disambiguate, big_bench_known_unknowns, freshqa, kuq, mediq, moralchoice, musique, qasper, self_aware, situated_qa, squad2, umwp). The second column, "label line removed" (D25's arm; D10, D24 and D25 call it label-blind), removes the label line only; neither column has been validated against human labels on reasoning-model outputs, so the levels are levels of this judge protocol.

| typed level (metric @ stage) | all rows | delivered only | bracket | undelivered | scorer (version, rule date) | rule |
|---|---|---|---|---|---|---|
| abstain recall @ SFT | 0.517 | 0.517 | [0.517, 0.517] | 0 of 3,564; cut at cap 11 (delivered, D18) | abstentionbench_judge/llama-3.1-8b-instruct/coconot-style v1.5 (3,564, 3,564 kept verdicts, design 2.6 identity; rule date 2026-10-15) | post-2d |
| abstain recall @ DPO | 0.574 | 0.574 | [0.574, 0.574] | 0 of 3,564; cut at cap 1 (delivered, D18) | abstentionbench_judge/llama-3.1-8b-instruct/coconot-style v1.5 (3,564, 3,564 kept verdicts, design 2.6 identity; rule date 2026-10-15) | post-2d |
| abstain recall @ RLVR | 0.570 | 0.570 | [0.570, 0.570] | 0 of 3,564; cut at cap 1 (delivered, D18) | abstentionbench_judge/llama-3.1-8b-instruct/coconot-style v1.5 (3,564, 3,564 kept verdicts, design 2.6 identity; rule date 2026-10-15) | post-2d |
| abstain recall, label line removed @ SFT | 0.431 | 0.431 | [0.431, 0.431] | 0 of 3,564; cut at cap 11 (delivered, D18) | abstentionbench_judge/llama-3.1-8b-instruct/coconot-style-label-blind v1 (3,564; rule date 2026-10-15) | post-2d |
| abstain recall, label line removed @ DPO | 0.457 | 0.457 | [0.457, 0.457] | 0 of 3,564; cut at cap 1 (delivered, D18) | abstentionbench_judge/llama-3.1-8b-instruct/coconot-style-label-blind v1 (3,564; rule date 2026-10-15) | post-2d |
| abstain recall, label line removed @ RLVR | 0.441 | 0.441 | [0.441, 0.441] | 0 of 3,564; cut at cap 1 (delivered, D18) | abstentionbench_judge/llama-3.1-8b-instruct/coconot-style-label-blind v1 (3,564; rule date 2026-10-15) | post-2d |
| false abstention @ SFT | 0.182 | 0.182 | [0.182, 0.182] | 0 of 4,852; cut at cap 4 (delivered, D18) | abstentionbench_judge/llama-3.1-8b-instruct/coconot-style v1.5 (4,852, 4,852 kept verdicts, design 2.6 identity; rule date 2026-10-15) | post-2d |
| false abstention @ DPO | 0.174 | 0.174 | [0.174, 0.174] | 0 of 4,852 | abstentionbench_judge/llama-3.1-8b-instruct/coconot-style v1.5 (4,852, 4,852 kept verdicts, design 2.6 identity; rule date 2026-10-15) | post-2d |
| false abstention @ RLVR | 0.155 | 0.155 | [0.155, 0.155] | 0 of 4,852 | abstentionbench_judge/llama-3.1-8b-instruct/coconot-style v1.5 (4,852, 4,852 kept verdicts, design 2.6 identity; rule date 2026-10-15) | post-2d |
| false abstention, label line removed @ SFT | 0.258 | 0.258 | [0.258, 0.258] | 0 of 4,852; cut at cap 4 (delivered, D18) | abstentionbench_judge/llama-3.1-8b-instruct/coconot-style-label-blind v1 (4,852; rule date 2026-10-15) | post-2d |
| false abstention, label line removed @ DPO | 0.257 | 0.257 | [0.257, 0.257] | 0 of 4,852 | abstentionbench_judge/llama-3.1-8b-instruct/coconot-style-label-blind v1 (4,852; rule date 2026-10-15) | post-2d |
| false abstention, label line removed @ RLVR | 0.245 | 0.245 | [0.245, 0.245] | 0 of 4,852 | abstentionbench_judge/llama-3.1-8b-instruct/coconot-style-label-blind v1 (4,852; rule date 2026-10-15) | post-2d |

| typed delta (metric) | transition | all rows [95% CI] | delivered at both [95% CI] | worst-case bound (ends with their intervals) | verdict | quoted (D7, D18) |
|---|---|---|---|---|---|---|
| abstain recall | SFT -> DPO | +0.056 [+0.040, +0.073]* (n=891) | +0.056 [+0.040, +0.073]* (n=891) | [+0.056, +0.056]; ends +0.056 [+0.040, +0.073] and +0.056 [+0.040, +0.073] | not_registered | +0.056 |
| abstain recall, label line removed | SFT -> DPO | +0.026 [+0.010, +0.042]* (n=891) | +0.026 [+0.010, +0.042]* (n=891) | [+0.026, +0.026]; ends +0.026 [+0.010, +0.042] and +0.026 [+0.010, +0.042] | not_registered (label line removed) | +0.026 |
| abstain recall | DPO -> RLVR | -0.004 [-0.018, +0.010] (n=891) | -0.004 [-0.018, +0.010] (n=891) | [-0.004, -0.004]; ends -0.004 [-0.018, +0.010] and -0.004 [-0.018, +0.010] | not_registered; judge-dependent (the owner's rule is pending) | -0.004 |
| abstain recall, label line removed | DPO -> RLVR | -0.015 [-0.028, -0.003]* (n=891) | -0.015 [-0.028, -0.003]* (n=891) | [-0.015, -0.015]; ends -0.015 [-0.028, -0.003] and -0.015 [-0.028, -0.003] | not_registered (label line removed); judge-dependent (the owner's rule is pending) | -0.015 |
| false abstention | SFT -> DPO | -0.008 [-0.020, +0.003] (n=1213) | -0.008 [-0.020, +0.003] (n=1213) | [-0.008, -0.008]; ends -0.008 [-0.020, +0.003] and -0.008 [-0.020, +0.003] | not_registered | -0.008 |
| false abstention, label line removed | SFT -> DPO | -0.001 [-0.013, +0.012] (n=1213) | -0.001 [-0.013, +0.012] (n=1213) | [-0.001, -0.001]; ends -0.001 [-0.013, +0.012] and -0.001 [-0.013, +0.012] | not_registered (label line removed) | -0.001 |
| false abstention | DPO -> RLVR | -0.019 [-0.027, -0.011]* (n=1213) | -0.019 [-0.027, -0.011]* (n=1213) | [-0.019, -0.019]; ends -0.019 [-0.027, -0.011] and -0.019 [-0.027, -0.011] | not_registered | -0.019 |
| false abstention, label line removed | DPO -> RLVR | -0.012 [-0.021, -0.002]* (n=1213) | -0.012 [-0.021, -0.002]* (n=1213) | [-0.012, -0.012]; ends -0.012 [-0.021, -0.002] and -0.012 [-0.021, -0.002] | not_registered (label line removed) | -0.012 |

Item-pooled: a row is one completion (four samples per item), and an item's value in a delta is the mean of its paired samples, as the table above computes it; the paper's headline averages per dataset (audit 19). A row cut at the length limit is delivered and counted (D18; notes/prereg_tulu.md, amendment 1, 23 Oct 2026).

The echo diagnostic and the "label line removed" column, delivered rows (D24, D25; design 2.7). The column is D25's arm label_blind_all (D10's judge config: the template of record with the gold label's line removed) on every delivered row; its three views and its deltas are the companion rows of the tables above, and here its delivered-only value stands beside the primary cell's, like for like. It changes no primary verdict. The echo diagnostic reads the no-claim stratum as abstention_judge.no_claim_stratum computes it (D24's adopted option: one-word delivered replies that name no option their item lists, the judge's template words not excluded): with the gold label shown, how many of its rows the judge of record called abstained; with its line removed, how many of the stratum rows judged so (label_blind_all's line, else D10's first arm's) were called abstained. A recall cell holds should-abstain items and a false-abstention cell answerable ones, so the two rows of a coordinate are the diagnostic's two gold labels. It never decides a verdict.

| typed echo and the label line removed column (metric @ coordinate) | label shown, delivered only | label line removed, delivered only (D25) | no-claim stratum rows (D24) | abstained, label shown | abstained, label line removed | not judged with the line removed |
|---|---|---|---|---|---|---|
| abstain recall @ SFT | 0.517 | 0.431 | 126 | 34 of 126 | 10 of 126 | 0 |
| abstain recall @ DPO | 0.574 | 0.457 | 36 | 13 of 36 | 2 of 36 | 0 |
| abstain recall @ RLVR | 0.570 | 0.441 | 68 | 30 of 68 | 8 of 68 | 0 |
| false abstention @ SFT | 0.182 | 0.258 | 236 | 1 of 236 | 13 of 236 | 0 |
| false abstention @ DPO | 0.174 | 0.257 | 71 | 1 of 71 | 3 of 71 | 0 |
| false abstention @ RLVR | 0.155 | 0.245 | 133 | 1 of 133 | 10 of 133 | 0 |

Scorer stamps: each row carries the stamp it is valid under for the read rule. A line written under it (steps 2a to 2d's rewrites, step 2e's ImpossibleBench v4, step 3's re-judged lines) carries its own; a kept line of an older stamp carries the post-2d version step 2d's provenance recorded for it (results/_ingest/sidecars_2026-10-15/<dir>/typed/provenance_rule_d_2d.<score file>.gz, status kept_same_text: the line's input is the post-2d text, and 2d's equivalence check found the post-2d scorer writes it). Kept and re-asked pairs, counted as one scorer in a cell and a delta: xstest v1.7 + v1.8 (D5); when2call v1.5 + v1.6 (D5); abstentionbench_judge v1.5 + v1.6 (design 2.6 identity). The kept stamp's verdicts were kept by step 3 because the prompt the judge read is the delivered request (design 2.6); the Gemini ones also pass D5's content rule (the verdict closes the reply). Each cell prints how many kept verdicts it holds. 'rule date' is the stamp's: the read rule's, or the date of the decision that set its parse (D20 for XSTest).

