#!/bin/zsh
# Preregistered run (notes/prereg_tulu.md): three Tülu 3 8B stages, four samples per item,
# paper settings; stages generate in parallel (one GPU each), then judge in parallel, then report.
set -euo pipefail
cd "$(dirname "$0")/.."
export HF_TOKEN=$(cat ~/.cache/huggingface/token)
MODAL=.venv/bin/modal; PY=.venv/bin/python
typeset -A MODELS
MODELS=(sft allenai/Llama-3.1-Tulu-3-8B-SFT dpo allenai/Llama-3.1-Tulu-3-8B-DPO rlvr allenai/Llama-3.1-Tulu-3-8B)
echo "=== $(date '+%H:%M:%S') generation, three stages in parallel"
for stage in sft dpo rlvr; do
  mkdir -p results/tulu_n4/$stage
  ( t0=$(date +%s); $MODAL run withholding/run/modal_vllm.py --model ${MODELS[$stage]} --prompts results/tulu/prompts.jsonl \
      --out results/tulu_n4/$stage/outputs.jsonl --temperature 0.8 --top-p 0.95 --max-tokens 4000 \
      --dtype float16 --max-model-len 20480 --gpu H100 --n 4 --batch 2500 > results/tulu_n4/$stage/gen.log 2>&1
    echo "exit $? after $(( $(date +%s) - t0 ))s" >> results/tulu_n4/$stage/gen.log ) &
done
wait
for stage in sft dpo rlvr; do echo "$stage generation: $(tail -1 results/tulu_n4/$stage/gen.log) | rows $(wc -l < results/tulu_n4/$stage/outputs.jsonl)"; done
echo "=== $(date '+%H:%M:%S') judging, three stages in parallel (float16 judge, paper rendering)"
for stage in sft dpo rlvr; do
  $PY -m withholding.score.abstention_judge build results/tulu_n4/$stage/outputs.jsonl results/tulu_n4/$stage/judge_prompts.jsonl paper
  ( t0=$(date +%s); $MODAL run withholding/run/modal_vllm.py --model meta-llama/Llama-3.1-8B-Instruct --prompts results/tulu_n4/$stage/judge_prompts.jsonl \
      --out results/tulu_n4/$stage/judge_outputs.jsonl --temperature 0 --max-tokens 5 --dtype float16 --max-model-len 20480 --gpu H100 --batch 4000 > results/tulu_n4/$stage/judge.log 2>&1
    echo "exit $? after $(( $(date +%s) - t0 ))s" >> results/tulu_n4/$stage/judge.log ) &
done
wait
for stage in sft dpo rlvr; do
  echo "$stage judging: $(tail -1 results/tulu_n4/$stage/judge.log)"
  $PY -m withholding.score.abstention_judge parse results/tulu_n4/$stage/judge_outputs.jsonl results/tulu_n4/$stage/scores.jsonl
done
echo "=== report"
$PY -m withholding.analysis.abstention_report --stage SFT=results/tulu_n4/sft/scores.jsonl --stage DPO=results/tulu_n4/dpo/scores.jsonl --stage RLVR=results/tulu_n4/rlvr/scores.jsonl --out results/tulu_n4/report.md
echo "=== done $(date '+%H:%M:%S')"
