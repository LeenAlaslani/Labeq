# LABEQ model card

| Component | Role | Release evidence |
| --- | --- | --- |
| Qwen3.5-4B base | Context plan and draft review | Real text inference through MLX locally and Transformers in the ZeroGPU deployment |
| Pilot Saudi LoRA | Response generation | Preserved original adapter, verified local tensor loading, and public inference checks |
| Saudi LoRA v2 | Candidate response generator | See the [training report](training/README.md) for run status and held-out evidence |
| Faisal | Automatic communication-style routing | Original adapter ran locally and on public ZeroGPU. Six of seven public cases used Faisal; one used explicit fallback. A human routing benchmark remains open. |
| Rule router | Fallback after unavailable or insufficient Faisal decision | Returns `rule_fallback` and retains the original goal |
| GitHub Pages | Entry point to the public app | Redirects to ZeroGPU; preview.html retains written examples |

## Provenance and rights

[Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B) is Apache-2.0. [Faisal](https://huggingface.co/Omartificial-Intelligence-Space/ara-jev-Faisal) is Omer Nacar's Arabic-first, Jev-inspired Qwen3.5-4B decision model. The upstream project uses LoRA SFT with labeled decision tasks and CC BY-NC 4.0 weights. Experimental use on LABEQ adds five communication-style descriptions and an insufficient-information option. It preserves the published chat and next-token scoring contract. Attribution and noncommercial use apply to the original adapted weights.

The pilot uses rank 16, alpha 16, zero dropout, and 256 LoRA tensors. The MLX loader maps PEFT weight names and orientations, validates pairs and shapes, and swaps just the adapter layers on a shared base. The original Faisal adapter used in local verification was revision `38849bdac4b7850c19587f78f5fe16c38adefac1`. It uses rank 32, alpha 64, and 496 tensors. The shared-base run uses quantized MLX weights. Upstream model-card metrics do not measure this quantized configuration on LABEQ scenarios.

Use of Munsit, ElevenLabs, and Azure voice features requires provider terms and credentials. The release distributes source code, fixture-based examples, genuine public inference records, and browser screenshots. The approved data and trained adapters remain private while redistribution rights are unresolved.

## Limitations

Saudi Arabic register varies across speakers and regions. Short prompts can leave the relationship or goal underspecified. A draft can introduce stiff phrasing, an unsupported promise, or a shift in intent. Model-based review shares the generator's base and does not establish human agreement. Judge output against the situation before sending.

The [public release evidence](evidence/RELEASE.md) records the deployed sources, actual inference, browser checks, voice test status, quotas, and observed quality failures.
