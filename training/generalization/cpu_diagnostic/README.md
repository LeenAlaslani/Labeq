---
title: LABEQ private CPU quality diagnostic
emoji: 🧪
colorFrom: purple
colorTo: pink
sdk: gradio
sdk_version: 6.32.0
python_version: 3.12
app_file: app.py
pinned: false
---

Private development diagnostic on the existing free Space. Qwen35B writing uses CPU only. The original Faisal adapter has a separate actual three-second GPU routing callback, required for automatic style selection in the intended hybrid application. Raw writer development checks do not call that endpoint. This is not the public LABEQ deployment. No paid resource or provider secret is configured. Faisal is Omer Nacar's Jev-inspired Qwen3.5-4B adapter, CC BY-NC 4.0; this diagnostic is noncommercial research.

The full `/pipeline` diagnostic runs actual Faisal on CPU and uses the same V16 plan/draft/review/one-repair control flow. The writer is the unadapted [Qwen3.5-35B-A3B](https://huggingface.co/Qwen/Qwen3.5-35B-A3B), using a pinned [Unsloth Q4_K_M GGUF](https://huggingface.co/unsloth/Qwen3.5-35B-A3B-GGUF), verified against its SHA-256. No Saudi response LoRA is claimed. The separate `/route` endpoint performs actual [Faisal](https://huggingface.co/Omartificial-Intelligence-Space/ara-jev-Faisal) GPU option scoring when called. `/check` records raw CPU writer output.

The tested allocation reports 16 CPU cores by cgroup quota and a 104,000,000,000-byte memory limit; these are resource limits, not measured peak usage. The GGUF is 22,016,023,168 bytes, and the router additionally loads the 4B base and adapter. This is not a 16 GB laptop recipe. The tested Linux CPU wheel is the maintainer's [0.3.36 release](https://github.com/abetlen/llama-cpp-python/releases/tag/v0.3.36), pinned by checksum in requirements.txt.

From the LABEQ repository, prepare an existing **private** Gradio Space on eligible free ZeroGPU hardware; consult [Hugging Face's account requirements](https://huggingface.co/docs/hub/en/spaces-zerogpu). This publisher neither creates paid resources nor changes hardware. Connect the CLI securely with `hf auth login --no-add-to-git-credential`; do not put the token in code or chat. Then:

```bash
python training/generalization/cpu_diagnostic/publish.py \
  --out /path/to/fresh/reviewable-package

python training/generalization/cpu_diagnostic/publish.py \
  --space YOUR_ACCOUNT/YOUR_PRIVATE_DIAGNOSTIC

python training/generalization/cpu_diagnostic/evaluate.py \
  --space YOUR_ACCOUNT/YOUR_PRIVATE_DIAGNOSTIC \
  --cases training/generalization/dev.json \
  --out /path/to/fresh/cpu-development --mode pipeline
```

The local client needs the repository's Hugging Face Hub and Gradio client dependencies. The model dependencies install inside the Space. Source packaging uses an explicit allowlist, never `.env`, local provider keys, adapters or model files. Its manifest identifies the working-tree file hashes and whether selected files differ from the Git base. Commit the intended source before a reproducible upload. The evaluator requires a private destination before sending necessary private-session authentication, records the actual Space revision, and stops if it changes mid-run. Each case, latency and failure is saved incrementally. It never opens another test file implicitly.

The source-ID review variant assigns exact original source units in code, constrains a verdict for every ID, and restores the original quotes without asking the model to reconstruct them. Language complaints must quote the actual candidate. These controls enforce provenance and mechanical coverage of source units; a unit can contain several requests, and model judgments can still be wrong. Development cases and the predeclared fresh-holdout gates are in the adjacent protocol files. Passing software contracts does not qualify a writer for the public application.

هذه بيئة بحث خاصة لاختبار الكاتب على CPU مع توجيه فيصل الفعلي. لا تستبدل واجهة لبِق أو شخصية مها، ولا تستخدم مفاتيح الصوت. تُحفظ الردود الفاشلة كما هي، ولا يعني نجاح التشغيل أو صحة JSON أن اللهجة أو المعنى اجتازا التقييم. لا يُعتمد الكاتب قبل اجتياز شروط الجودة المنشورة.
