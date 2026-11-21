# Separate long-form Saudi training experiment

This experiment follows the completed approved v2 and the unsuccessful compositional/CPU studies. It does not overwrite their weights or relabel AI-authored references as human approval.

The run completed two epochs and 249 optimizer updates in 3,357.13 seconds, processing 996 sequences and 39,354 target tokens. Final validation loss was 2.3218; this is token likelihood, not Saudi quality. [Real metrics and weight hashes](result.json), [all 20 raw paired development outputs](development_outputs.json), and [assistant judgments](development_assessment.json) record the unsuccessful result: base 0/4, pilot 2/4, approved v2 1/4, v3 epoch one 1/4 and epoch two 0/4. Neither candidate met the frozen 4/4 gate. Epoch one is diagnostic-only; no v3 was promoted and the fresh 16-case test remains unopened. Both 352-tensor PEFT conversions passed exact transposition and sampled delta checks.

Four additional [actual first-epoch CPU full-pipeline requests](cpu_epoch1_development.json) used the original Faisal adapter and pinned official 4B bfloat16 base. They took 63.6–72.4 seconds and retained grammar and role errors. Their prompts/precision/decoding differ from the raw local comparison, so the study does not isolate quantization effects. Independent human review remains pending.

The selected 80 AI-authored situations were curated by the assistant to remove unnecessary instruction narration, retain the requested speech acts and avoid unsupported gender assumptions. Their median reference length is 27 words, compared with nine in the approved set. They expand to four deterministic writing-style views per situation, with explicit repetitions: conversational/clear for every case and professional additionally for work, university and customers. The 178 approved completions remain verbatim. The resulting training set has 498 rows and 374 unique prompts. The held-out validation completions remain unchanged; their prompt contract migrates to the new policy.

The policy omits the stock-phrase list that earlier base outputs sometimes repeated. It supplies no in-context answer examples. Data, policy and learning rate change together, so a result cannot isolate one causal effect. These references have no independent human review. Exact protected-case overlap is checked, not guaranteed semantic separation.

```bash
python training/generalization_v3/build.py \
  --approved-data /path/to/approved/data \
  --out /path/to/fresh/v3-data

# In a separate pinned Apple Silicon MLX environment:
python training/train_compositional.py \
  --data /path/to/fresh/v3-data --model /path/to/pinned/MLX-base \
  --out /path/to/fresh/v3-candidate --learning-rate 5e-5
```

The [protocol](protocol.json) freezes two epochs, rank/alpha 16, the nine projection suffixes, seed 3407, completion-only loss, 768-token maximum and effective batch four. Checkpoints are not optimizer-resumable. The two epoch checkpoints are compared only on four development cases before the still-unused fresh 16-case test can be opened. Known user regressions are separate and do not count as unseen evidence. Promotion requires measured sendability, production-runtime and actual UI checks, not lower loss or valid JSON.

Use the same policy for every paired model:

```bash
python training/generalization/evaluate.py \
  --model /path/to/pinned/MLX-base --pilot /path/to/preserved/pilot \
  --v2 /path/to/preserved/v2 --candidate /path/to/selected/v3-checkpoint \
  --policy training/generalization_v3/policy.json \
  --cases training/generalization/cpu_candidate_holdout.json \
  --out /path/to/fresh/frozen-test-evaluation
```

Do not run the held-out command until development qualification is recorded. Raw clipped text is retained with its explicit finish reason; the serving path rejects it. Report the exact policy hash, adapter hashes, reviewer, coverage and failed cases. Private approved data and weights stay outside Git.

هذه تجربة مستقلة بثمانين موقفًا مؤلفًا آليًا ومراجعًا من المساعد، وليست بيانات معتمدة بشريًا. بقيت الصياغات المعتمدة الأصلية كما هي. الهدف هو تدريب ردود سعودية تحفظ أكثر من طلب وقيد، مع تعليمات تخلو من قائمة عبارات جاهزة. لا يعني اكتمال التدريب أو انخفاض الخسارة اجتياز التعميم؛ الاختبار المحجوز وموقفا المستخدم وبيئة التشغيل الفعلية هي شروط الاعتماد المعلنة.
