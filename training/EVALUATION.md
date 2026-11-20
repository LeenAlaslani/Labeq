# Saudi LoRA v2 evaluation

Training completed on November 17, 2026. The final adapter contains 256 finite, nonzero tensors. Four intermediate checkpoints are preserved at iterations 200, 400, 600, and 800. The final checkpoint and metrics remain in the private run directory.

| Measurement | Observed result |
| --- | ---: |
| Training examples | 958 |
| Validation examples | 114 |
| Epochs | 2 |
| Minibatch iterations | 958 |
| Optimizer updates | 479 |
| Last logged training loss | 1.2804 |
| First-epoch validation loss | 1.8096 |
| Final validation loss | 1.8040 |
| Runtime recorded by trainer | 3,597.48 seconds |
| Peak memory reported by MLX | 5.675 GB |

The run used Apple M5 with 16 GB unified memory, MLX 0.32.4, MLX-VLM 0.7.11, a four-bit Qwen3.5-4B snapshot, rank/alpha 16, seed 3407, a 768-token limit, and completion-only loss. Test examples were excluded from optimization. The final adapter SHA-256 is 866ca93ca5ad48faf8e92c11acdfe973a9435946903f7fe66d19564ed97d0e6e.

## Comparison on the same 38 held-out scenarios

All three variants generated replies to the same saved prompts on the same quantized MLX base. Thinking was disabled, decoding was greedy, and each call allowed 160 new tokens. References were excluded from generation. The private run contains 114 actual replies and a blinded review sheet.

| Variant | Completed cases | Cases flagged by original heuristics | Mean generation time |
| --- | ---: | ---: | ---: |
| Qwen base | 38 | 1 | 1.02 s |
| Previous Saudi LoRA pilot | 38 | 0 | 0.75 s |
| Saudi LoRA v2 | 38 | 0 | 0.80 s |

These timings describe this local run. Each variant produced 38 distinct replies. No pair of models returned identical text on a case.

The automatic checks missed substantial semantic and dialect problems. A qualitative Codex review covered all 114 replies. [Case-by-case concerns](review_notes.json) identify what that review noticed. Independent human reviewers have not scored the blinded sheet.

| Case | Pilot output | v2 output | Assessment |
| --- | --- | --- | --- |
| Asking whether a presentation is in person | السلام عليكم، هل يمكن توضيح نوع العرض (حضوري أو عن بعد)؟ | السلام عليكم دكتورة، هل العرض حضوري ولا عن بعد؟ | v2 is more conversational and retains the question. |
| Requesting an extension because the assignment is unfinished | أرجو مراجعة إمكانية تمديد تسليم الواجب لأسباب شخصية. | السلام عليكم دكتور، أود طلب تمديد مهلة تسليم الواجب بسبب ظروف استثنائية. | Both invent an excuse. |
| Supporting a friend considering marriage | أفهم أنكِ في مرحلة تفكير، وأحب أن أسمع رأيك قبل ما تتخذ القرار. | أقدّر ثقتك فيي، وأتمنى تتفككين القرار بعد استشارة أهلك. | Pilot has agreement problems. v2 introduces unnatural wording and unsolicited advice. |
| Repeated calls after midnight | أعتذر عن الرد بعد أوقات متأخرة، وأفضل نتحدث في أوقات نهارية. | يا خوي إذا اتصلك بعد النوم ابلغني قبل ما تتصل | v2 fails to express a clear ongoing boundary. Pilot is too formal and indirect. |

The base also produced Egyptian markers, confused speakers, and unsupported commitments. The fine-tuned models reduced some verbosity, while both still changed intent or produced unnatural expressions. Personal conversations need further review for everyday Saudi wording, punctuation, and the exact social action requested. Professional replies can retain a formal register.

Several evaluation inputs contain conflicting generic labels. A coffee-invitation situation has an acceptance-or-apology goal, and a guard is labeled as a landlord. Those inputs remained identical across all variants. Their ambiguity limits interpretation and should be resolved before a future benchmark.

## Adapter decision

Keep the pilot as the incumbent research baseline. v2 is a successfully trained candidate, and the comparison shows useful improvements on some cases. Its remaining intent failures and unnatural Saudi phrasing do not justify a production promotion. The pilot also needs review and has not received a human quality certification.

V16 adds planning, style controls, heuristic checks, and model review around the selected adapter. The comparison above evaluates the adapters directly. Application tests are reported separately.

## Reproduction and artifacts

[Machine-readable results](results.json) include the base revision, adapter hash, counts, checkpoints, and measured losses. Run the [evaluator](evaluate_mlx.py) with the same data package, model snapshot, and privately supplied adapters. It saves outputs as they complete and creates a blinded review CSV. Review dialect, intent, relationship fit, unsupported details, usefulness, and sendability with Saudi Arabic reviewers before changing the model selection.
