# Saudi generalization: actual runtime qualification

These are separate research experiments, not a production quality claim. All development situations were already exposed. The assistant assessed strict sendability; independent Saudi Arabic human review is pending. No human reference answer entered the inference prompts.

## What was tested

The preserved pilot and completed approved v2 weights each generate with two fixed policies. Actual original Faisal scores communication styles. A pinned Qwen3.6-35B-A3B Q8 CPU model produces an automatic advisory facts/actions/constraints plan, selects among the four unedited generated candidates or rejects all, and reviews against source IDs. Traces preserve the exact candidates, automatic plan, coaching and review, including wrong judgments. The final writer's adapter and policy are frozen per attempt; an unsuccessful retry cannot relabel an earlier winner. No hand-written scenario response, paid resource or provider-key upload is involved.

## BF16 production runtime

Raw candidate selection over MLX-generated development texts passed 4/4. That result did **not** transfer to the full BF16 runtime: only **2/4** final replies met the same strict naturalness/meaning criteria. Actual request latencies were 96.7–105.1 seconds. The apology was formal and unnatural, while the report boundary used stiff translated phrasing. All four apology candidates needed repair; a selector cannot recover a good answer absent from its pool. Automatic selection and source-grounded review accepted the defective text.

[Exact results, identities, candidates and assessments](../training/qwen36_cpu/bf16_runtime_results.json) · [Frozen runtime protocol](../training/qwen36_cpu/runtime_protocol.json). The combined system remains distinct from an individual adapter; neither v2 training completion nor a valid review schema establishes generalization.

## Quantized-runtime compatibility follow-up

The official pinned llama.cpp converter exported each preserved PEFT adapter as F32 GGUF. The verifier compared **all 256 factors per adapter**, exact shapes and array values, with alpha/r scaling unchanged. No adapter factor was merged or quantized. Original tensors and hashes remain preserved. The public response base changes to Q4_K_M, so this is a separate inference configuration rather than a claim of numerical equivalence to MLX or BF16.

The private free Space loaded both real converted adapters, verified the public base checksum and retained actual original BF16 Faisal routing. The same full-pipeline development, UI and unopened-test gates apply. [Frozen configuration and conversion hashes](../training/qwen36_cpu/gguf_runtime_protocol.json) identify the exact inputs. The actual calls completed: **1/4** final replies passed the strict reply criterion, at 88.6–103.1 seconds. The list-restoration request was reduced to a review request despite complete pilot candidates being available; automated selection and review missed the omission. The apology remained formal, and coaching changed the friend into a brother. The report boundary retained meaning but remained unnatural. [Exact final replies, candidates, coaching and identities](../training/qwen36_cpu/gguf_runtime_results.json) document this failed gate. No new UI qualification or fresh test outputs were opened. The result does not isolate a quantization effect: the full V16 prompt/style/routing contract also differs from the earlier raw MLX study.

## Frontend intent correction

Selecting «ننهي الخلاف» previously sent «أحل سوء الفهم بهدوء» to the backend. That introduced a cause the user had not necessarily stated. The frontend now sends «ننهي الخلاف ونتفاهم بهدوء» on both initial generation and style rewrites. Chrome verifies the actual outgoing request. This general request correction changes no character design and inserts no scenario-specific reply.

## Decision

The public pilot remains an incumbent research baseline, not a validated high-quality Saudi model. No fresh S01–S16 outputs may be opened until a new complete runtime passes every development and known-user UI gate. The software checks, actual model loading, tensor conversion and successful HTTP requests are measured separately from meaning, register and grounded coaching. More validation-loss optimization or a larger selector alone has not solved those failures.

## بالعربية

اكتمل تدريب v2 وحُفظت أوزانه، لكن ذلك لا يثبت تحسّن التعميم. اختبار التطبيق الكامل على BF16 اجتاز ردّين من أربعة وفق تقييم المساعد. المراجع الآلي قبل صيغًا غير طبيعية، ولا يمكن لاختيار أفضل صيغة أن يصلح مجموعة كل صيغها معيبة. تجربة GGUF منفصلة وتحافظ على جميع عوامل LoRA الأصلية، لكن تغيير دقة المودل الأساسي قد يغيّر الردود. بقي المحوّل السابق في الديمو ولم تُفتح مخرجات الاختبار الجديد. كما أُصلح إرسال هدف إنهاء الخلاف دون تحويله إلى افتراض بوجود سوء فهم.
