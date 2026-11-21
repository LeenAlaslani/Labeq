# Compositional Saudi Arabic evaluation

November 21, 2026. **The generalization problem remains open.** The engineering fixes and completed training below are real; neither the new adapter nor a larger alternative writer passed the quality gate. The public research app retains the pilot adapter. No scenario-specific answer was inserted into the inference path.

## What changed

The audit found 178 approved completions across 60 situations with a median answer length of nine words. In the full 958-row set, 943 answers are shorter than 15 words. This raises a coverage concern for messages with several obligations, but does not prove the cause of a particular failure.

The new experiment preserves every approved completion verbatim and adds 48 explicitly AI-authored compositional examples, weighted twice: 274 records and 226 unique prompts. It covers partial agreement, responsibility without excuses, permanent versus temporary boundaries, uncertainty and relationship reassurance. These additions are not human-approved data. Neither known user scenario is a training example.

The adapter also covers the Qwen3.5 linear-attention input/output projections that were absent from the earlier target list. This and the data/prompt changes occur together; the experiment cannot isolate their causal effects.

Runtime changes remove generic topic instructions that could turn a privacy boundary into a daily-help refusal. Faisal controls tone; the original situation and goal control content. Grounded JSON review replaces keyword matching of reviewer prose. A valid grounded concern can trigger one rewrite regardless of its wording; invalid, truncated or unsupported reviews cannot certify success. Failed advisory generation is reported as unavailable. Each attempt retains its own raw draft and wording edits, even if two drafts normalize to identical text. Explicitly truncated provider outputs fail rather than becoming finished replies. These are control-flow protections, not proof that the models understand every constraint.

## Completed training

The approved Saudi LoRA v2 run remains preserved: two epochs, 479 optimizer updates and validation loss **1.8040**. This new compositional experiment is a separate artifact.

| New experimental run | Observed value |
| --- | --- |
| Hardware | Apple M5 Metal GPU, 16 GB |
| Base | Pinned Qwen3.5-4B MLX 4-bit |
| Epochs / optimizer updates | 2 / 137 |
| Sequences / target tokens processed | 548 / 14,390 |
| Rank / alpha / adapted modules | 16 / 16 / 176 |
| Elapsed time / peak memory | 1,678.62 seconds / 6.139 GB |
| Validation loss | 2.2166, token likelihood only |

Both epochs failed development qualification. Epoch one was selected for diagnostic evaluation by the predeclared earlier-checkpoint tie rule. Both 352-tensor PEFT conversions passed exact transpose round trips and sampled delta equivalence. [Training metrics and weight hashes](../training/generalization/training_result.json) and [all development outputs](../training/generalization/development_outputs.json) preserve the evidence. The new validation loss uses a different experiment and is not a directly comparable quality score for v2.

## Frozen test comparison

Sixteen AI-authored cases, twelve situation families and four minimal contrasts were frozen before training. The two known user regressions are separate. All four models use the same base snapshot, raw prompt, greedy decoding, thinking disabled and 256-token cap, without dialect substitutions. Assessment was recorded with shuffled candidate labels before the model key was opened.

A strict pass requires all three meaning requirements, no unsupported assertion, correct roles/gender, and Saudi text ready to send without factual or grammatical repair. Minor orthographic differences alone do not fail. This is an **assistant assessment**, not independent human validation or a population accuracy estimate.

| Raw local MLX comparison | All three meaning requirements met | Strict passes |
| --- | ---: | ---: |
| Qwen3.5-4B base | 7/16 | 0/16 |
| Previous Saudi pilot | 7/16 | 1/16 |
| Approved Saudi LoRA v2 | 4/16 | 3/16 |
| New compositional epoch one | 12/16 | 5/16 |

The experiment preserves more requested meaning but still produces awkward language, role errors, unsupported statements and copied instructions. All models have zero contrast pairs with **both** cases strictly sendable; this is not a separate semantic-only contrast accuracy score. The candidate misses the frozen 13/16 promotion threshold, and both known user regressions still fail. It was not promoted. [Blinded per-requirement judgments and raw replies](../training/generalization/holdout_assessment_blind.json), [unblinded totals and key](../training/generalization/holdout_result.json), and the [protocol](../training/generalization/protocol.json) make this judgment reviewable. This test set is now exposed and must not serve as unseen evidence for later tuning.

## Additional real diagnostics

Pinned local Qwen3.5-9B, Qwen2.5-14B and ALLaM-7B-Instruct-preview writers were tested on development cases. Larger size alone did not resolve Saudi wording, role preservation or invented commitments. An automatic English brief sometimes inverted negation; an English-message stage sometimes returned Arabic despite its instructions. These pipelines were rejected, not deployed. Manually translated English oracle tests are labeled as such and are not automatic-pipeline evidence. [Raw development diagnostics](../training/generalization/additional_development.json) preserve unsuccessful outputs as well as useful ones.

One actual official Qwen3.5-4B base bfloat16 request also produced mixed-dialect and semantic defects. This shows that this observed failure can occur outside local 4-bit inference; it does not establish a universal cause or quantify quantization effects. [Saved request/result](../training/generalization/bf16_diagnostic.json).

## New application screenshots

These are new, unedited captures from the latest local application using actual Qwen generation, the pilot adapter and actual Faisal routing. They show the remaining failures and the visible review state. They are not public bfloat16 inference screenshots or approved example answers.

| Privacy boundary | Late-cancellation apology |
| --- | --- |
| ![Actual latest local privacy response requiring review](../screenshots/generalization-pilot-privacy.png) | ![Actual latest local apology response requiring review](../screenshots/generalization-pilot-apology.png) |

The [experimental privacy](../screenshots/generalization-experimental_epoch_1-privacy.png) and [experimental apology](../screenshots/generalization-experimental_epoch_1-apology.png) captures retain the unsuccessful pre-guard development replies. [Runtime records](../training/generalization/runtime_regressions.json) identify the model and assessment for each image. No screenshot text was replaced with a hand-written response.

## Reproduction and limits

Use the [experiment commands](../training/generalization/README.md), exact model/checkpoint hashes, and frozen cases to repeat the raw comparison. `tests/capture_scenarios.py` runs the actual interface against a configured model service and requires the declared real source plus Faisal; it does not mock model routes. Unit and browser fixture tests verify contracts, not Saudi dialect quality.

The final hosted inference recheck is subject to the account's free ZeroGPU quota. The diagnostic service rejected a 20-second callback because it requested 30 quota seconds with 24 remaining; a reduced 12-second diagnostic subsequently succeeded. No paid hardware or subscription was activated. The longer grounded-review pipeline reserves 60 or 90 seconds rather than assuming the old 20-second allowance is sufficient; final latency remains unmeasured until a full hosted request completes. The cloud loader pins the official base and tokenizer to revision `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`. Local MLX checks do not establish production bfloat16 equivalence.

Further work needs a fresh evaluation set, broader reviewed multi-obligation Saudi data, independent Saudi Arabic review, and a passing production-runtime evaluation before replacing the incumbent. The model's own reviewer remains fallible and cannot supply that independent evidence.

## بالعربية

**مشكلة التعميم ما زالت مفتوحة.** اكتمل تدريب المحوّل التجريبي الجديد فعليًا، وتحسن حفظ الطلبات في المقارنة المحلية، لكن ٥ ردود فقط من ١٦ اجتازت معيار الصلاحية للإرسال، مقابل رد واحد للمحوّل السابق و٣ لـ v2. الحد المحدد قبل الاختبار هو ١٣ من ١٦، وموقفا الخصوصية والاعتذار المعروفان ما زالا غير ناجحين. لذلك لم نستبدل النموذج المنشور، ولم نضع ردودًا مكتوبة يدويًا داخل مسار الاستدلال.

شمل الإصلاح فصل النبرة عن المقصد، وإزالة توجيهات عامة كانت تغيّر موضوع الحدود، وربط مراجعة المعنى باقتباسات من النص، وحفظ النص الأصلي لكل محاولة، ورفض النص المقطوع بدل عرضه كأنه مكتمل. نجاح هذه الحمايات برمجيًا لا يثبت طبيعية اللهجة أو صحة فهم النموذج.

الأمثلة الجديدة مولدة آليًا وموسومة بوضوح وليست بيانات معتمدة بشريًا. التقييم المنشور هو تقييمي كمساعد، مع إتاحة النصوص الخام والأحكام التفصيلية للمراجعة. الصور جديدة ومن التطبيق الفعلي محليًا، وتعرض الإخفاقات كما ظهرت. يلزم اختبار جديد لم يُستخدم في التطوير ومراجعة سعودية مستقلة واجتياز بيئة التشغيل العامة قبل اعتماد محوّل بديل. بقيت شخصية مها وتصميمها وتكامل صوتها النجدي الأصلي محفوظة، ومفتاح المزود محليًا.
