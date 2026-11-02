"""withholding: measure five "withholding" behaviors across public post-training checkpoints.

Layout (read in this order):
  data/      one loader per benchmark; each returns a list of Item(id, prompt, meta)
  run/       generation: send prompts to a model, store raw outputs as frozen JSONL
  score/     scorers: turn raw outputs into per-item 0/1 or probability scores
  analysis/  stage-to-stage deltas with paired item bootstrap; plots

Every number in the write-up must be recomputable from files in results/ with one command.
"""
