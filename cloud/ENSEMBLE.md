# Private candidate-system qualification

This opt-in configuration is **not selected in the public app**. The raw development study used genuine, unedited 4B completions with an automatic meaning plan. A Qwen3.6 selector chose strict-pass candidates on 4/4 exposed cases; original Faisal chose 2/4 on this different task, so Faisal remains the communication-style router. [Evidence](../training/qwen36_cpu/selection_results.json) and the [runtime protocol](../training/qwen36_cpu/runtime_protocol.json) separate this result from an unseen evaluation or a production promotion.

The entry point is `cloud/ensemble_space_app.py`. It retains the original interface, artwork, FastAPI/Gradio queue, style controls and original inactive voice configuration. Actual original Faisal performs style routing. Two compatible, preserved Qwen3.5-4B Saudi adapters each generate with two fixed policies, independent of the scenario. Pinned CPU Qwen3.6 supplies an advisory meaning plan, chooses an actual candidate or rejects them all, and performs source-ID review. No case-specific answer or hand-written oracle enters inference. The complete system remains fallible; valid JSON does not prove meaning or naturalness.

The selected attempt freezes its actual adapter hash, policy hash and generator. A rejected later attempt cannot relabel the earlier winner. An actual EOS is required for CPU candidates, and teacher time/token stops are rejected too. The shared warm request budget is 135 seconds, with 22 seconds per candidate and bounded token limits. Model loading is separate. Private diagnostic failures return traces without claiming a generated reply; ordinary serving fails rather than substituting example text.

Private QA can package both compatible PEFT adapters into an **owned private** existing free Space:

```bash
python cloud/publish_space.py --space YOUR_ACCOUNT/private-check \
  --commit EXACT_TESTED_GIT_COMMIT --backend ensemble \
  --private-adapter /path/to/preserved/pilot \
  --private-v2 /path/to/completed/v2/peft
```

Set `LABEQ_LOCAL_ADAPTER_DIR=private-qa-adapter`, `LABEQ_V2_ADAPTER_DIR=private-qa-v2`, accurate adapter labels/revisions, and both expected weight SHA-256 values through `LABEQ_PILOT_SHA256` and `LABEQ_V2_SHA256`. Keep `LABEQ_VOICE_ENABLED=0`. `LABEQ_RETURN_GENERATION_TRACE=1` is for private diagnostics only. No provider key is needed or uploaded.

For a later qualified deployment, response weights must remain in authorized private model repositories. The primary adapter uses the existing `LABEQ_ADAPTER_REPO`/`LABEQ_ADAPTER_REVISION` configuration; the second uses `LABEQ_V2_ADAPTER_REPO`, `LABEQ_V2_ADAPTER_REVISION` and optional `LABEQ_V2_ADAPTER_SUBFOLDER`. Use accurate `LABEQ_ADAPTER_LABEL` and `LABEQ_V2_ADAPTER_LABEL` values for your own compatible adapters. The publisher rejects QA-weight uploads to a public Space and never requests hardware upgrades.

The public Q8 teacher has an immutable revision/checksum and no Saudi response adapter. Its [documented build-time preloading](https://huggingface.co/docs/hub/spaces-config-reference) uses the default Hub cache, followed by a complete SHA-256 check before loading. The observed private allocation had 16 CPU cores and a 104 GB memory limit; this is not a free-resource guarantee. The original Faisal noncommercial attribution and all upstream model/data terms still apply.

Before any public selection, the combined system must pass development in its explicitly selected production runtime, both known-user UI regressions, then the still-unused 16-case test and latency/contrast gates. Its evidence cannot be described as proof that an individual adapter alone generalized.


The actual BF16 production-runtime gate subsequently failed: 2/4 strict development replies, including a falsely accepted formal apology. [Exact results](../training/qwen36_cpu/bf16_runtime_results.json) preserve candidates and coaching as generated. No fresh test outputs were opened.

A separate [GGUF runtime comparison](../training/qwen36_cpu/gguf_runtime_protocol.json) retains every F32 LoRA factor exactly while changing the public response base to pinned Q4_K_M. It is not a new trained adapter or evidence of quality. Private QA additionally passes `--private-gguf /path/to/verified/conversions`, sets `LABEQ_WRITER_RUNTIME=gguf` and `LABEQ_GGUF_ADAPTER_DIR=private-qa-gguf`, and records both conversion manifests and the base checksum in health. Actual original Faisal still runs on BF16. The same development, UI and fresh-test gates apply to this explicitly separate runtime; passing a raw MLX study cannot substitute for them.

The actual GGUF comparison also failed (1/4 strict replies); see [the complete report](../evidence/GENERALIZATION_RUNTIME.md). Neither runtime is publicly selected.
