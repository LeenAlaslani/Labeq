# Saudi LoRA training and evaluation

## Approved inputs

Use the supplied `LABEQ_Approved_Training_Data.zip` (SHA-256 `9278a55a7edd6d5ce776a2f6affbd6c3c62864f732483acf5e3ef08e0921cb25`). The package contains conversational prompt/completion JSONL, a provenance CSV, and the Dataset Manifest. The [original Colab training notebook](../notebooks/LABEQ_Final_Training_Colab.ipynb) records the intended CUDA recipe. [Arabic QA criteria](QA_ACCEPTANCE_AR.md) define the review expectations.

| Split | Count | Use |
| --- | ---: | --- |
| Train | 958 | 178 approved revisions and 780 unchanged legacy synthetic examples |
| Validation | 114 | Track validation loss during optimization |
| Test | 114 | Held-out evaluation |
| One per test scenario | 38 | Primary paired comparison and blind review |

Two reviewed rows were held because the rewrites could change the intended meaning. The validator checks chat roles, counts, normalized situation overlaps across splits, exact membership of the gold and 38-case subsets, and agreement with the nine style labels in the supplied manifest. The pilot notebook deduplicated the earlier Compact Train file to 960 distinct responses. The held-out situations had zero exact normalized substring matches in the pilot source prompts. This check measures exact matches.

```bash
unzip LABEQ_Approved_Training_Data.zip -d training
python training/validate_data.py training/data
```

## Apple Silicon v2

The local recipe uses MLX-VLM 0.7.11 and the quantized `mlx-community/Qwen3.5-4B-MLX-4bit` snapshot `32f3e8ecf65426fc3306969496342d504bfa13f3`. It retains the original notebook's seed 3407, rank and alpha 16, seven target projection suffixes, max length 768, two epochs, effective batch of four, learning rate 5e-5, 5% warmup, and completion-only objective. MLX changes the base precision, optimizer implementation and batching. The assistant tokens plus end token contribute to loss. Inputs longer than 768 fail validation. Test rows are excluded from optimization and validation.

```bash
python -m pip install 'mlx-vlm[train]==0.7.11'
MODEL=mlx-community/Qwen3.5-4B-MLX-4bit
python training/train_mlx.py --data training/data --model "$MODEL" \
  --out training/runs/LABEQ_Saudi_LoRA_v2
```

The output directory is created once and contains run configuration, data manifest, intermediate adapters, final MLX weights, logs/metrics, and the validation loss. Redirect standard output to a separate log if needed. `--smoke` trains on eight rows for four iterations to verify GPU execution. Losses from that diagnostic are separate from the full run.

The [supplied CUDA notebook](../notebooks/LABEQ_Final_Training_Colab.ipynb) uses PyTorch, Unsloth, TRL, and PEFT on a compatible NVIDIA GPU. That workflow creates a PEFT checkpoint for the CUDA server. Verify its runtime dependency versions and GPU allocation before training. The Apple Silicon run exports an MLX adapter.

## Paired evaluation

Compare base Qwen, the previous pilot adapter, and v2 on the same held-out prompts with the same quantized base, chat template, thinking disabled, greedy decoding, and a limit of 160 generated tokens. The evaluator disables all adapters for base, and swaps adapter layers for pilot and v2. No reference reply enters inference.

```bash
python training/evaluate_mlx.py --data training/data --model "$MODEL" \
  --pilot /path/to/private-pilot --v2 training/runs/LABEQ_Saudi_LoRA_v2 \
  --out training/runs/eval-38
```

Use `--split 114` to evaluate the full test split. The evaluation saves raw outputs, objective flags, a summary, and a blinded review CSV with a separate reveal key. Use a fresh output directory for a changed adapter or model revision. Inspect language, unsupported detail, repeated-request wording, and instruction leakage flags as diagnostics. Naturalness, intent, social fit, goal completion, relationship, style consistency, factuality, usefulness, and sendability require blinded Saudi Arabic review. Report reviewer count and coverage before any claim of improvement. Keep the pilot configured for demonstrations until a replacement has a quality decision.

## Release evidence

The Metal diagnostic completed on Apple M5. The full run and aggregate paired results are tracked in the release report. The local app screenshots use the already trained pilot adapter. Data files, raw outputs, and weights remain private.
