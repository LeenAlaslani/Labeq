# LABEQ — model integration notes

## Scope

The public repository includes **inference integration and research notebooks**, but no checkpoint files or benchmark results. Do not treat this repository as independent evidence of model performance.

## Components

| Stage | Intended model/component | Status in public repository |
|---|---|---|
| Context intake | Arabic message, relationship and intent | Implemented in UI |
| Style router | Faisal decision-making model | Code path described in research workflow; trained classification adapter **not included** |
| Local style fallback | Explicit goal-to-style rules | Implemented and clearly identified as fallback |
| Arabic reply generator | Qwen3.5-4B + Saudi PEFT LoRA | Inference integration and loading scripts; user-provided weights required |
| Saudi voice | Munsit Maha | Optional external API; keys and voice audio not bundled |

## Supplied adapter metadata (reviewed privately)

The adapter supplied during development was a PEFT `CAUSAL_LM` LoRA adapter over `unsloth/Qwen3.5-4B`, with **rank 16**, **alpha 16**, **dropout 0**, and 256 LoRA matrices. The public repository does **not** redistribute that adapter. Adapter compatibility with a quantized MLX base model must be verified on the target hardware.

## Evaluation and reproduction

- The project brief described five target communication-style labels: `polite`, `firm`, `diplomatic`, `apology`, and `clarify`.
- A separate integrated notebook discusses additional historical experiments and data. Its historical experiment descriptions are **not** a standalone, independently verified benchmark in this repository.
- No before/after accuracy, macro F1, confusion matrix, or final held-out prediction table is asserted here.
- The original dataset, verified evaluation artifacts, and trained Faisal classification adapter are not in this public export.
- To reproduce classification fine-tuning, first add the licensed dataset and training/evaluation code, isolate a held-out split, and report actual metrics.
- To reproduce generation, obtain the adapter via a permitted private transfer, select a compatible base-model version, then run the Colab notebook or the local MLX adapter workflow.

## Known reliability limitation

Some Apple Silicon/MLX-VLM versions raise thread-scoped stream exceptions when the model is loaded in one thread and generated in another. `local_mlx_server.py` includes async startup and request handling in the source to address the observed mismatch; this is a targeted source patch, **not proof** that every MLX-VLM version will run correctly. Verify inference with `verify_local_model.py` before any showcase.

## Disclaimer

Suggested replies are language assistance only. They are not guaranteed to be culturally appropriate, risk-free, or free from errors. Always review before sending.
