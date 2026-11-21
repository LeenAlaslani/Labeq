# CPU inference with the original interface

`cloud/cpu_space_app.py` serves the same FastAPI frontend and Gradio queue as the GPU entry point. The default `/reply` callback runs the pinned Qwen3.5-4B base, selected Saudi adapter and original Faisal adapter on CPU in bfloat16. A separate `/reply_gpu` callback performs real inference on ZeroGPU when explicitly called. The frontend uses `/reply`. No dummy GPU function, replacement voice or example-response fallback is used.

Private QA observed 16 allocated CPU cores and a 104 GB memory limit on the existing free ZeroGPU Space. These are observed shared resources, not a promised free hosting entitlement. The backend uses eight PyTorch threads and keeps separate CPU and emulated CUDA model instances. It never requests a hardware upgrade or subscription. A CPU-only Space without a GPU function was rejected by the platform; the optional GPU callback here executes the actual LABEQ pipeline.

Two actual private CPU requests with the unchanged pilot completed in approximately 35 and 37 seconds and reported genuine Faisal routing. Both failed semantic acceptance. Their coaching was unavailable and their reviews were flagged. This establishes transport feasibility, not successful Saudi generalization or a public deployment of this entry point. Further measurements must identify the running source, weights and versions.

Configure an existing eligible Space with:

```text
LABEQ_MODEL_MODE=real
LABEQ_ADAPTER_REPO=your-account/your-private-compatible-adapter
LABEQ_ADAPTER_REVISION=full-model-repository-commit
LABEQ_ADAPTER_LABEL=your-accurate-adapter-label
LABEQ_VOICE_ENABLED=0
```

Use the Space's protected `HF_TOKEN` secret for private model access. Voice-provider credentials are separate and optional. No credential belongs in Git or these commands. For private QA, `LABEQ_LOCAL_ADAPTER_DIR=private-qa-adapter` selects locally packaged adapter files instead. `LABEQ_WRITER_POLICY=/app/path/to/policy.json` optionally selects the matching reviewed writer contract; this does not select or qualify an adapter.

Publish only committed source, after inspecting the result:

```bash
python cloud/publish_space.py --space your-account/LABEQ \
  --commit FULL_GIT_COMMIT --backend cpu

# Optional: weights may only be copied into your OWN PRIVATE QA Space.
python cloud/publish_space.py --space your-account/LABEQ-private-check \
  --commit FULL_GIT_COMMIT --backend cpu \
  --private-adapter /path/to/compatible/peft-adapter
```

The publisher requires existing free ZeroGPU hardware, checks requested hardware too, and rejects private-weight uploads to public Spaces. It copies an explicit source selection, excluding `.env`, provider keys and training directories. The deployment manifest records the source and file hashes; the running application's health endpoint reports its loaded source, adapter hash and library versions.

Evaluate explicitly selected, already approved development cases:

```bash
python cloud/evaluate_space.py --space your-account/LABEQ-private-check \
  --source FULL_GIT_COMMIT --cases /path/to/development.json \
  --out /path/to/fresh/results
```

This command waits for neither training nor deployment: it fails unless the exact deployed revision is running and its health source matches. Public callbacks use no authentication token. An owned private callback uses the securely stored Hub login. Results are incremental, include errors, and are not automatically graded as good Saudi Arabic. Do not open an unused holdout before its qualification gate.

CPU phases have cooperative time limits: 30 seconds for advisory planning, 45 for a draft, 40 for review, within a 135-second request budget. An actual EOS is required; a time stop cannot turn clipped text into a finished reply. Advisory failures remain unavailable/unverified. A valid-looking model review remains fallible. `LABEQ_RETURN_GENERATION_TRACE=1` adds only that request's decoded phase outputs for private diagnostics; leave it unset for ordinary use.

هذا مسار استدلال فعلي على المعالج، مع بقاء الواجهة وشخصية مها كما هما. نجاح الاتصال وسرعة الطلب لا يعنيان اجتياز جودة اللهجة أو حفظ المقصد. لا تُستبدل الأوزان المنشورة بسبب انخفاض خسارة التدريب أو موافقة المراجع الآلي وحده.
