# Saudi compositional generalization experiment

This experiment responds to omissions, invented justifications, and unnatural wording in multi-part communication requests. It is separate from the completed approved Saudi LoRA v2. The production adapter must not be changed solely because training loss falls or unit tests pass.

The supplied approved set contains 178 revised answers across 60 situations; its median answer length is nine words. The full 958-row set also has a nine-word median. This is a coverage concern for requests with several obligations, not proof of the cause of any individual failure.

`synthetic.json` contains 48 AI-authored, longer examples covering responsibility, partial agreement, permanent versus temporary limits, uncertainty, repair, and relationship preservation. These are **not human-approved**. The builder keeps all 178 approved completions verbatim, updates their input contract, and weights each synthetic example twice: 274 training records, 226 unique prompts. No user regression is a training example.

`dev.json` contains four development cases for selecting between the two epoch checkpoints. `holdout.json` is a separately frozen 16-case diagnostic: 12 situation families and four minimal contrasts. A contrast changes permission, duration, participation, or capacity while retaining the domain. These are intended to detect intent collapse. `regressions.json` contains the two already observed user cases and must never be counted as unseen generalization evidence.

The holdout hash is recorded before training. Evaluation uses the same prompt, base snapshot, greedy decoding, thinking disabled, and 256-token limit for every adapter. It records raw generated text with no register normalization. Human interpretation of natural language is still needed: substring checks, training loss, and the model's own review are insufficient measures of generalization. Any assistant review must be labeled as such, with the independent-human-review limitation explicit.

The experimental adapter starts from the frozen MLX 4-bit Qwen3.5-4B base, not the previous adapters. It adds `linear_attn.in_proj_qkv` and `linear_attn.out_proj` to the existing seven projection targets so the 24 linear-attention layers also receive attention adapters. This is an architectural coverage change, not an established cause of better quality. Several factors change together, so this experiment cannot attribute an improvement to one factor.

With the repository's installation instructions and a separate Apple Silicon MLX environment:

```bash
python training/generalization/build.py \
  --approved-data /path/to/approved/data \
  --out /path/to/fresh/experiment-data

python training/train_compositional.py \
  --data /path/to/fresh/experiment-data \
  --model /path/to/pinned/Qwen3.5-4B-MLX-4bit \
  --out /path/to/fresh/candidate

python training/generalization/evaluate.py \
  --model /path/to/pinned/Qwen3.5-4B-MLX-4bit \
  --pilot /path/to/pilot \
  --v2 /path/to/completed/v2 \
  --candidate /path/to/fresh/candidate \
  --cases training/generalization/holdout.json \
  --out /path/to/fresh/evaluation
```

Directories must be fresh. Optimizer state is not resumable in this script. Private weights, source approved data, and raw training artifacts remain outside Git. MLX validation does not establish equivalence to the public bfloat16 runtime; a production promotion needs separate runtime checks.

## بالعربية

هذه تجربة مستقلة لتحسين حفظ أكثر من طلب وقيد في الرسالة السعودية. الأمثلة الجديدة مولدة آليًا وليست مراجعات بشرية معتمدة، ولم ندخل موقفي المستخدم في التدريب. المقارنة تفصل بين أربع حالات تطوير، و١٦ حالة اختبار محفوظة قبل التدريب، وموقفي المستخدم المعروفين سابقًا.

نقارن النص الخام من نفس النموذج الأساسي وبنفس إعدادات التوليد، بدون تبديل الكلمات بعد التوليد. انخفاض خسارة التدريب أو نجاح الاختبارات البرمجية لا يثبت التعميم. لا نغيّر النموذج المنشور قبل وجود دليل جودة كافٍ والتحقق من بيئة التشغيل الفعلية، ولا ندعي أن مراجعة النموذج لنفسه بديل عن التقييم البشري المستقل.
