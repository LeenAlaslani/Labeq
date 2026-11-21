# Separate Qwen3.6 CPU diagnostic

This tests an unadapted, eight-bit Qwen3.6-35B-A3B writer on existing free CPU resources after the long-form 4B LoRA experiment failed its development gate. It is not a Saudi LoRA, does not overwrite its completed training, and is not configured in the public application. The [frozen protocol](protocol.json) identifies the model, tokenizer, quantization, sampler, policies, gates and still-unused fresh test.

The official [model card](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/tree/345d467b117d1fd5eda9b879a5988de9ae5f47a7) supplies the non-thinking sampling settings. The [quantizer's pinned repository](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF/tree/a483e9e6cbd595906af30beda3187c2663a1118c) supplies the public Q8 file and checksum. All GGUF bytes are verified before loading. `n_gpu_layers=0` keeps writing on CPU. The separately registered GPU route executes genuine original Faisal scoring; the evaluated full pipeline explicitly uses the actual CPU Faisal adapter and does not invoke that GPU function.

Only four previously exposed development cases may be generated initially, under the two frozen policies. The clean policy uses no reference answers; the few-shot policy contains three already published AI-authored examples, never UI results. No provider secret or trained private model file belongs in this diagnostic package. Do not call a valid review schema or a successful download a quality result.

The [actual recommended-sampling results](recommended_results.json) completed: clean policy 1/4 and few-shot policy 2/4 strict passes under assistant assessment. Reply compute was 7.8–15.6 seconds after loading; a large cold download is separate. Neither policy qualified, so no fresh test output was generated and the public pilot was preserved. A [separate frozen greedy follow-up](greedy_protocol.json) tests the identical weights with temperature/presence penalty zero; it is not a result until actually run. The Space card uses documented build-time preloading and the runtime uses its default Hub cache, avoiding a redundant custom-cache download after each deployment.


The automatic-plan candidate system selected sendable MLX-generated messages on 4/4 exposed development cases, but its actual BF16 production runtime failed the same strict gate: **2/4**, with formal or unnatural personal messages and false acceptance by automatic review. [Exact replies, candidates and identity](bf16_runtime_results.json) remain recorded. The fresh S01–S16 output set remains unopened. No public adapter was replaced.

A separate [GGUF runtime protocol](gguf_runtime_protocol.json) freezes a public Q4_K_M response base and the **unchanged** pilot/v2 LoRA factors. These are converted with official llama.cpp revision `0c1e57098bba43ac29e6e3b677cdceebdd22334f` (the submodule used by the pinned Python wheel):

```bash
python convert_lora_to_gguf.py --base /path/to/pinned-qwen-config --outtype f32 --outfile /private/qa/pilot.gguf /private/pilot-peft
PYTHONPATH=/path/to/llama.cpp/gguf-py python training/qwen36_cpu/verify_gguf_adapter.py /private/pilot-peft /private/qa/pilot.gguf --out /private/qa/pilot-verification.json
# Repeat for v2.gguf and v2-verification.json using the preserved v2 PEFT directory.
```

The verifier requires all 256 factors in each file to be exactly equal to their original F32 PEFT arrays, identical alpha/r scaling and no missing or extra tensors. This establishes conversion fidelity, **not** equivalent base quantization, successful generalization or deployment qualification. Private `cloud/ensemble_space_app.py` supports `LABEQ_WRITER_RUNTIME=gguf` and `LABEQ_GGUF_ADAPTER_DIR` as an explicit experiment; normal public CPU inference remains unchanged.

الاختبار الفعلي على بيئة BF16 لم يجتز شرط اللهجة الطبيعية: نجح ردّان من أربعة وفق تقييم المساعد، مع قبول آلي خاطئ لصيغ تحتاج تعديل. لذلك بقي المودل العام كما هو ولم تُفتح مخرجات الاختبار الجديد. تجربة GGUF منفصلة، وتحافظ على عوامل LoRA الأصلية دون إعادة تدريب؛ مطابقة الأوزان لا تعني نجاح جودة الردود.
