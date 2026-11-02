"""Generate model outputs for a JSONL of prompts on a rented GPU with vLLM, via Modal.

Why Modal: the Mac has 24 GB RAM and 18 GB free disk, so 8B checkpoints (about 16 GB each in
bf16) cannot live locally. Modal gives a GPU per call, caches the weights in a persistent
volume (shared with earlier projects: "huggingface-cache"), and we pay only for minutes used.

Usage (from the project root, with the uv venv active):
    modal run withholding/run/modal_vllm.py \
        --model nvidia/Nemotron-Cascade-8B --revision main \
        --prompts results/pilot/prompts.jsonl --out results/pilot/outputs.jsonl \
        --thinking false --max-tokens 1024 --gpu H100 --dtype float16

Cascade stages (subfolders of one repo), prompted with the FINAL model's template so every stage
sees identical prompts, thinking off, both Qwen stop tokens:
    modal run withholding/run/modal_vllm.py --model nvidia/Nemotron-Cascade-8B-Intermediate-ckpts \
        --subfolder Nemotron-Cascade-8B-MathRL --chat-template-from nvidia/Nemotron-Cascade-8B \
        --thinking false --stop-token-ids 151645,151643 --temperature 0.6 --top-p 0.95 ...

Input JSONL rows:  {"id": "...", "messages": [{"role": "user", "content": "..."}], ...}
Output JSONL rows: the input row plus {"model", "revision", "thinking", "output", "finish_reason",
                   "prompt_tokens", "completion_tokens", "sampling": {...}}

Everything that affects the output (model, revision, thinking flag, sampling params, chat
template source) is written next to the output so the run can be reproduced from the file alone.

13 Oct 2026: every output row also carries "vllm_version" (vllm.__version__ inside the container). The image pins
"vllm>=0.10", so an account that builds the image later can hold a newer vLLM than one that built it earlier;
amendment 3 D11 asks for the version per checkpoint, and scripts/ood_readout.py and scripts/c_full_report.py read this
field (they print "not recorded" for older files). The image definition is unchanged, so no cached image is rebuilt.

14 Oct 2026: forced-think templates. Every output row also carries "think_forced": True when the rendered prompt of
that row ends with "<think>" (after trailing whitespace), i.e. the chat template itself opened the think block, as the
Olmo 3 Think template does ("<|im_start|>assistant\n<think>"); False otherwise (Cascade and Qwen3 end at
"assistant\n"; Qwen3 with thinking off closes the block inside the prompt). withholding/score/programmatic.py
delivered_answer reads it: a row whose template forced the block open and whose output never closes it delivered no
answer. Additive only: no existing field changes, and a failed render stamps None instead of stopping the run.

14 Oct 2026 (notes/ingestion_audit_2026-10-14.md, findings 22 and 23). Two additions; no existing field changes, so every
row is byte-identical to before apart from the appended field (tests/test_runner_rows.py checks it on a fake engine).
- "prompt_token_hash" on every output row: sha256 (16 hex) of the chat template text the prompt was rendered with (the
  --chat-template-from text, else the tokenizer's own), the chat_template_kwargs, and the token ids vLLM received for
  that prompt (RequestOutput.prompt_token_ids). prompt_render_hash is unchanged and still hashes the rendered text of the
  first five prompts of a batch only, so it moves with batch composition and cannot see one text tokenized two ways
  (finding 2: id 100268 is '<|extra_id_3|>' for Olmo-3 base and Think but '<think>' for the RL-Zero runs).
  prompt_token_hash is per prompt: two runs prompted alike carry equal hashes id by id, whatever the batching. None
  when it cannot be computed (the stamp never stops a run).
- Resume guard: main() skips ids already in --out (cheap resume), and the Llama judge's ids are "<id>#judge<sample>"
  whatever the judge prompt says, so a re-judge into an existing judge_outputs.jsonl would have kept every old verdict.
  main() now stops before any GPU call when an id of the prompts file is already in --out under a different prompt (the
  canonical JSON of its "messages") or with no stored prompt; write to a new --out instead. The same prompts resume as
  before, and ids in --out that the prompts file does not hold are not read.

23 Oct 2026 (typed design step 3, plan W8.1.2, notes/reviews/2026-10-14_abstentionbench_fidelity.md F2): the BOS arm.
`--bos-mode upstream_text` renders each prompt with the chat template as text and passes the text to `llm.generate`,
which tokenizes it with the tokenizer's special tokens, as the AbstentionBench authors' code does (vLLM 0.6.4
tokenizer_group encode): a template that opens with the BOS token then carries two BOS ids, the authors' judge
tokenization. The default, `chat`, is today's `llm.chat` path (the rendered template encoded without special tokens:
one BOS for the Llama judge) and its rows are byte-identical to before. A row of the upstream_text mode also carries
"bos_mode" and "prompt_bos_ids" (the BOS ids its prompt token ids open with, read from vLLM's prompt_token_ids).

25 Oct 2026 (typed design section 6 step 6, plan W7.2): the runner's ingestion. Before any GPU call, main() resolves the
run's key (model, revision, subfolder, template source, chat kwargs) to its TemplateSpec in the typed registry
(withholding/typed/registry.py) and stops when no entry matches. Every row generate() returns carries vLLM's
"stop_reason" (the stop token id or string that ended it, None for EOS or the cap), appended after
"prompt_token_hash". main() then appends, on CPU and before the row is written, the ingestion stamp of
withholding.typed.ingest.runner_stamp: "spec_id", "think_opened_by" ("template", "model" or None), "think_closed",
"think_close_count" (the close markers of the turn), "empty_output" and "invented_turn". A row whose stamp cannot be
made, or that lacks a field the runner writes (ingest.RUNNER_ROW_FIELDS), is still written as it came back, and is
listed with the reason in "quarantine.<out file name>" beside --out. The report readers type a row through its step 0
sidecar line or through these fields, and refuse a row with neither (withholding/typed/dispatch.py). The typed layer is
imported by main() only: the GPU image does not carry it, and generate() never reads it.

25 Oct 2026 (typed design step 6 fix round; section 9 (b)): every row generate() returns also carries, after
"stop_reason", the ids vLLM sampled ("completion_token_ids", CompletionOutput.token_ids as returned) and their hash
("completion_token_hash": sha256, 16 hex, of the ids' canonical JSON; the typed Completion's completion_token_hash, which
the C reward computes the same way). A continuation of a row written from then on can feed back the sampled ids instead
of re-encoding the text (design 9 (b), prefix_ids_source "sampled"). ingest.classify_stored_row refuses a row whose hash
is not its ids' hash or whose ids are not completion_tokens long. Both fields are in ingest.RUNNER_ROW_FIELDS, so a row
without them is quarantined like any other row that lacks a runner field.

Decoding: top_k is never passed, so every run samples with vLLM's SamplingParams default (top_k 0 = no top-k cut, in vLLM
0.10 and later; the image pins vllm>=0.10). generation_config="vllm" keeps a checkpoint's generation_config.json out
(Qwen3 ships top_k 20), and vLLM applies generation defaults only when no SamplingParams is passed. Every sampling
parameter not listed in the "sampling" field (top_k, min_p, penalties) is the vLLM default.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import modal

APP_NAME = "withholding-gen"
HF_CACHE = "/root/.cache/huggingface"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("vllm>=0.10", "huggingface_hub>=0.30", "hf_transfer>=0.1")
    .env({
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "VLLM_LOGGING_LEVEL": "WARNING",
        # The slim image has no nvcc. vLLM's flashinfer sampler JIT-compiles a kernel at
        # startup and fails without it, so use the torch sampler (same outputs, slightly slower).
        "VLLM_USE_FLASHINFER_SAMPLER": "0",
    })
)
app = modal.App(APP_NAME, image=image)
hf_cache = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
secrets = [modal.Secret.from_dict({"HF_TOKEN": os.environ["HF_TOKEN"]})] if os.environ.get("HF_TOKEN") else []


def _build_chat_kwargs(thinking: bool | None):
    """Qwen3-family templates accept enable_thinking in chat_template_kwargs. Models that do not
    know the flag ignore it. None means: do not pass anything (model default)."""
    return {} if thinking is None else {"enable_thinking": bool(thinking)}


THINK_OPEN = "<think>"


def think_forced_from_render(rendered: str) -> bool:
    """True when a rendered prompt (add_generation_prompt=True) ends with the think-open tag after whitespace: the
    template opened the think block, so the completion starts inside it (14 Oct 2026, forced-think templates)."""
    return rendered.rstrip().endswith(THINK_OPEN)


def _think_forced_per_row(tokenizer, messages: list, template: str | None, chat_kwargs: dict) -> list[bool | None]:
    """think_forced for every prompt, rendered exactly as llm.chat renders it. Never raises: a render that fails
    stamps None for that row, so the stamp cannot stop a generation run."""
    out = []
    for m in messages:
        try:
            out.append(think_forced_from_render(tokenizer.apply_chat_template(
                m, tokenize=False, add_generation_prompt=True, chat_template=template, **chat_kwargs)))
        except Exception:  # noqa: BLE001 (any render failure stamps None; the stamp must never stop a run)
            out.append(None)
    return out


def effective_chat_template(tokenizer, template: str | None):
    """The chat template text a prompt is rendered with: `template` (the --chat-template-from text) when given, else the
    tokenizer's own (transformers' get_chat_template, else its chat_template attribute, else None)."""
    if template is not None:
        return template
    try:
        return tokenizer.get_chat_template()
    except Exception:  # noqa: BLE001 (a tokenizer without the method or a template falls back to the attribute)
        return getattr(tokenizer, "chat_template", None)


def prompt_token_hash(template_text, chat_kwargs: dict, token_ids) -> str:
    """sha256 (16 hex) of the template text, the chat kwargs and one prompt's token ids (14 Oct 2026, finding 22)."""
    payload = json.dumps({"chat_template": template_text, "chat_template_kwargs": chat_kwargs,
                          "prompt_token_ids": [int(t) for t in token_ids]}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def completion_token_hash(token_ids) -> str:
    """sha256 (16 hex) of one completion's token ids as canonical JSON (no whitespace): the typed Completion's
    completion_token_hash (25 Oct 2026, step 6 fix round; withholding.typed.adapters.completion_token_hash is the typed
    layer's copy, because the GPU image does not carry the typed layer)."""
    return hashlib.sha256(json.dumps([int(t) for t in token_ids], separators=(",", ":")).encode()).hexdigest()[:16]


def _prompt_token_hashes(tokenizer, template: str | None, chat_kwargs: dict, outs) -> list[str | None]:
    """prompt_token_hash for every vLLM RequestOutput. Never raises: a failure stamps None for that row."""
    text = effective_chat_template(tokenizer, template)
    hashes = []
    for o in outs:
        try:
            hashes.append(prompt_token_hash(text, chat_kwargs, o.prompt_token_ids))
        except Exception:  # noqa: BLE001 (the stamp must never stop a run)
            hashes.append(None)
    return hashes


def messages_hash(messages) -> str:
    """sha256 (16 hex) of a prompt's messages as canonical JSON (sorted keys): what the resume guard compares."""
    return hashlib.sha256(json.dumps(messages, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def resume_conflicts(out_path, rows: list[dict]) -> list[str]:
    """Ids of `rows` that `out_path` already holds under another prompt: a stored row whose "messages" match none of the
    prompts `rows` gives that id, or that stores no messages. main() refuses to resume on any (14 Oct 2026, finding
    23). Ids in `out_path` that `rows` does not hold are skipped."""
    want: dict[str, set[str]] = {}
    for r in rows:
        want.setdefault(r["id"], set()).add(messages_hash(r["messages"]))
    bad: dict[str, None] = {}  # insertion-ordered set: first conflict first
    with open(out_path) as f:
        for line in f:
            if not line.strip():
                continue
            o = json.loads(line)
            i = o.get("id")
            if i in want and ("messages" not in o or messages_hash(o["messages"]) not in want[i]):
                bad[i] = None
    return list(bad)


def _resolve_model_path(model: str, revision: str, subfolder: str | None) -> str:
    """vLLM cannot load a subfolder of a Hub repo (the Nemotron-Cascade intermediate stages are
    five subfolders of one repo), so download the subfolder into the cache and return its path."""
    if not subfolder:
        return model
    from huggingface_hub import snapshot_download
    root = snapshot_download(model, revision=revision, allow_patterns=[f"{subfolder}/*"])
    return f"{root}/{subfolder}"


def _load_chat_template(repo: str | None, revision: str = "main") -> str | None:
    """Chat template text taken from another repo's tokenizer_config.json, so every stage of a
    lineage is prompted identically (the Cascade SFT folder ships the wrong template)."""
    if not repo:
        return None
    import json as _json

    from huggingface_hub import hf_hub_download
    try:  # newer repos (Olmo 3) ship the template as a separate file, which takes precedence
        with open(hf_hub_download(repo, "chat_template.jinja", revision=revision)) as fh:
            return fh.read()
    except Exception:  # noqa: BLE001 (no chat_template.jinja in the repo: the template is in tokenizer_config.json)
        with open(hf_hub_download(repo, "tokenizer_config.json", revision=revision)) as fh:
            return _json.load(fh)["chat_template"]


@app.function(gpu="H100", timeout=6 * 60 * 60, volumes={HF_CACHE: hf_cache}, secrets=secrets)
def generate(model: str, revision: str, rows: list[dict], thinking: bool | None,
             max_tokens: int, temperature: float, top_p: float, seed: int,
             max_model_len: int, dtype: str = "bfloat16", n: int = 1,
             subfolder: str | None = None, chat_template_from: str | None = None,
             stop_token_ids: list[int] | None = None, ephemeral_cache: bool = False,
             bos_mode: str = "chat") -> list[dict]:
    import os as _os
    if ephemeral_cache:
        # Trajectory runs touch dozens of 16 GB checkpoints once each; keep them on the container's
        # own disk instead of filling the shared volume (which still serves the judge model).
        _os.environ["HF_HUB_CACHE"] = "/tmp/hfcache"; _os.makedirs("/tmp/hfcache", exist_ok=True)
    import vllm
    from vllm import LLM, SamplingParams

    # generation_config="vllm" ignores the checkpoint's generation_config.json, so a checkpoint
    # cannot silently cap max_new_tokens (the Nemotron-Cascade SFT folder sets 2048).
    model_path = _resolve_model_path(model, revision, subfolder)
    template = _load_chat_template(chat_template_from)
    llm = LLM(model=model_path, revision=None if subfolder else revision, dtype=dtype,
              max_model_len=max_model_len, gpu_memory_utilization=0.90, seed=seed,
              generation_config="vllm", download_dir="/tmp/hfcache" if ephemeral_cache else None)
    sampling = SamplingParams(max_tokens=max_tokens, temperature=temperature, top_p=top_p, seed=seed, n=n,
                              stop_token_ids=stop_token_ids or None)
    chat_kwargs = _build_chat_kwargs(thinking)
    messages = [r["messages"] for r in rows]
    if bos_mode == "chat":
        outs = llm.chat(messages, sampling, chat_template=template, chat_template_kwargs=chat_kwargs,
                        use_tqdm=True)
    elif bos_mode == "upstream_text":   # 23 Oct 2026 (W8.1.2): the authors' text path, the template's BOS and the encoder's
        texts = [llm.get_tokenizer().apply_chat_template(m, tokenize=False, add_generation_prompt=True,
                                                         chat_template=template, **chat_kwargs) for m in messages]
        outs = llm.generate(texts, sampling, use_tqdm=True)
    else:
        raise ValueError(f"unknown bos_mode {bos_mode!r} (chat or upstream_text)")
    import hashlib
    rendered = [llm.get_tokenizer().apply_chat_template(m, tokenize=False, add_generation_prompt=True,
                                                        chat_template=template, **chat_kwargs)
                for m in messages[:5]]
    prompt_hash = hashlib.sha256("\n".join(rendered).encode()).hexdigest()[:16]
    forced = _think_forced_per_row(llm.get_tokenizer(), messages, template, chat_kwargs)  # 14 Oct 2026, additive
    token_hashes = _prompt_token_hashes(llm.get_tokenizer(), template, chat_kwargs, outs)  # 14 Oct 2026, additive
    hf_cache.commit()
    results = []
    for r, o, tf, th in zip(rows, outs, forced, token_hashes):
        for k, c in enumerate(o.outputs):  # one row per sample; "sample" indexes them
            reasoning, sep, answer = c.text.rpartition("</think>")
            results.append({
                **r, "sample": k,
                "model": model, "subfolder": subfolder, "revision": revision, "thinking": thinking,
                "dtype": dtype, "chat_template_from": chat_template_from,
                "prompt_render_hash": prompt_hash,  # same hash across stages = same prompting
                "vllm_version": vllm.__version__,  # D11 provenance: the image pins only vllm>=0.10
                "output": c.text, "finish_reason": c.finish_reason,
                "reasoning": reasoning if sep else None, "answer": answer if sep else c.text,
                "prompt_tokens": len(o.prompt_token_ids), "completion_tokens": len(c.token_ids),
                "sampling": {"max_tokens": max_tokens, "temperature": temperature, "top_p": top_p,
                             "seed": seed, "n": n, "chat_template_kwargs": chat_kwargs,
                             "stop_token_ids": stop_token_ids},
                "think_forced": tf,  # 14 Oct 2026: the template opened the think block (see the module docstring)
                "prompt_token_hash": th,  # 14 Oct 2026: template + kwargs + this prompt's token ids (module docstring)
            })
            if hasattr(c, "stop_reason"):   # 25 Oct 2026 (step 6): absent only where vLLM has no such field
                results[-1]["stop_reason"] = c.stop_reason
            ids = [int(t) for t in c.token_ids]   # 25 Oct 2026 (step 6 fix round, design 9 (b)): the sampled ids
            results[-1].update({"completion_token_ids": ids, "completion_token_hash": completion_token_hash(ids)})
            if bos_mode != "chat":   # 23 Oct 2026 (W8.1.2): the tokenization the row was judged under
                results[-1].update({"bos_mode": bos_mode, "prompt_bos_ids": _leading_bos(llm.get_tokenizer(), o)})
    return results


def _leading_bos(tokenizer, out) -> int | None:
    """How many BOS ids a prompt's token ids open with (None when the tokenizer names no BOS id)."""
    bos = getattr(tokenizer, "bos_token_id", None)
    if bos is None:
        return None
    n = 0
    for t in out.prompt_token_ids:
        if t != bos:
            break
        n += 1
    return n


def run_spec(model: str, revision: str, subfolder: str | None, chat_template_from: str | None,
             thinking: bool | None):
    """The registry TemplateSpec this run's rows will resolve to (design section 6 step 6: "The run refuses to start
    without a registry match"): the row key generate() writes (model, revision, subfolder, template source, chat
    kwargs) resolved by the typed registry, as every reader resolves the stored rows. SystemExit when no entry, or more
    than one, matches, or when the registry does not load."""
    from withholding.typed import ingest
    from withholding.typed import registry as R

    key = {"model": model, "revision": revision, "subfolder": subfolder, "chat_template_from": chat_template_from,
           "thinking": thinking, "sampling": {"chat_template_kwargs": _build_chat_kwargs(thinking)}}
    try:
        return R.load_registry().spec_for_row(key)
    except (ingest.IngestError, R.RegistryError) as e:
        raise SystemExit(f"no registry entry for this run, so it does not start (add one with its fixtures first, "
                         f"CLAUDE.md 'Adding a model family'): {e}") from e


def stamp_rows(rows: list[dict], spec) -> tuple[list[dict], list[dict]]:
    """(rows, quarantine): each row with the ingestion stamp of `spec` appended (withholding.typed.ingest.runner_stamp
    on its raw output), and one quarantine record per row whose stamp failed or that lacks a field the runner writes
    (ingest.missing_runner_fields): {"id", "sample", "reason"}. A quarantined row is kept, as it came back or with the
    fields it has, so no generated text is lost; a reader refuses it until a step 0 sidecar covers it. Never raises."""
    from withholding.typed import ingest

    out, quarantine = [], []
    for r in rows:
        reason = None
        try:
            r = {**r, **ingest.runner_stamp(r["output"], spec)}
            missing = ingest.missing_runner_fields(r)
            if missing:
                reason = f"lacks the runner's fields {list(missing)}"
        except Exception as e:  # noqa: BLE001 (the stamp must never stop a run or lose a generated row)
            reason = f"stamp failed: {type(e).__name__}: {e}"
        if reason is not None:
            quarantine.append({"id": r.get("id"), "sample": r.get("sample"), "reason": reason})
        out.append(r)
    return out, quarantine


def quarantine_path(out_path: Path) -> Path:
    """Where main() lists the quarantined rows of --out: "quarantine.<out file name>" beside it (not an outputs*.jsonl
    name, so no reader or backfill takes it for an output file)."""
    return out_path.with_name(f"quarantine.{out_path.name}")


@app.local_entrypoint()
def main(model: str, prompts: str, out: str, revision: str = "main", thinking: str = "none",
         max_tokens: int = 1024, temperature: float = 0.0, top_p: float = 1.0, seed: int = 13,
         max_model_len: int = 8192, gpu: str = "H100", batch: int = 2000, dtype: str = "bfloat16",
         n: int = 1, subfolder: str = "", chat_template_from: str = "", stop_token_ids: str = "",
         ephemeral_cache: bool = False, bos_mode: str = "chat"):
    """Read prompts, call the GPU function in batches, append outputs. Re-running skips ids
    that already have an output in `out` (cheap resume), and stops if any of them was stored under a different prompt.
    Stops before any GPU call when the typed registry has no entry for the run (run_spec); every row is stamped
    (stamp_rows) before it is appended, and a row that cannot be is appended as it is and listed in quarantine_path."""
    think = None if thinking == "none" else thinking.lower() in ("1", "true", "yes", "on")
    spec = run_spec(model, revision, subfolder or None, chat_template_from or None, think)
    with open(prompts) as fh:
        rows = [json.loads(l) for l in fh if l.strip()]
    out_path = Path(out); out_path.parent.mkdir(parents=True, exist_ok=True)
    done = set()  # ids that already have all n samples
    if out_path.exists():
        counts = {}
        with open(out_path) as fh:
            for l in fh:
                if l.strip():
                    i = json.loads(l)["id"]; counts[i] = counts.get(i, 0) + 1
        done = {i for i, c in counts.items() if c >= n}
        stale = resume_conflicts(out_path, rows)  # 14 Oct 2026 (finding 23): resume only under the same prompts
        if stale:
            raise SystemExit(f"{out}: {len(stale)} id(s) already stored under a different prompt (first: {stale[0]}); "
                             "resuming would keep their old outputs. Write to a new --out.")
    todo = [r for r in rows if r["id"] not in done]
    print(f"{len(rows)} prompts, {len(done)} already done, {len(todo)} to run on {gpu} (registry spec {spec.spec_id})")
    fn = generate.with_options(gpu=gpu) if gpu != "H100" else generate
    with out_path.open("a") as f:
        for i in range(0, len(todo), batch):
            chunk = todo[i:i + batch]
            stops = [int(x) for x in stop_token_ids.split(",") if x.strip()]
            extra = {} if bos_mode == "chat" else {"bos_mode": bos_mode}   # the default call is unchanged
            results = fn.remote(model, revision, chunk, think, max_tokens, temperature, top_p,
                                seed, max_model_len, dtype, n, subfolder or None,
                                chat_template_from or None, stops or None, ephemeral_cache, **extra)
            results, quarantine = stamp_rows(results, spec)   # 25 Oct 2026 (step 6): CPU, never raises
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            if quarantine:
                with quarantine_path(out_path).open("a") as q:
                    for x in quarantine:
                        q.write(json.dumps(x, ensure_ascii=False) + "\n")
                print(f"{len(quarantine)} rows quarantined (unstamped): {quarantine_path(out_path)}")
            print(f"wrote {len(results)} rows ({i + len(chunk)}/{len(todo)})")
