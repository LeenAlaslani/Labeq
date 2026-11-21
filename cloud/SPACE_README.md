---
title: LABEQ
emoji: 💜
colorFrom: purple
colorTo: pink
sdk: gradio
sdk_version: "6.32.0"
app_file: cloud/space_app.py
python_version: "3.12"
pinned: false
---

# LABEQ · لبِق

Saudi Arabic communication coaching with the V16 interface, original Maha artwork, Qwen3.5-4B with a Saudi pilot LoRA adapter, and the original Faisal decision adapter. Requests use Gradio's queue and Hugging Face ZeroGPU.

The Saudi LoRA v2 candidate completed two epochs locally. Its held-out review found intent and dialect failures, so the pilot remains the configured research baseline. A separate completed compositional experiment reached 5/16 strict local diagnostic passes under assistant assessment and was also not promoted. Replies require user review. Detailed methods, unsuccessful outputs and new application screenshots are recorded in the GitHub generalization report.

Faisal is Omer Nacar's Jev-inspired Arabic decision model under CC BY-NC 4.0. This Space is an attributed noncommercial research demonstration.

Configure the private adapter repository and its exact revision as LABEQ_ADAPTER_REPO and LABEQ_ADAPTER_REVISION. Store private model access in the HF_TOKEN Space secret. Maha speech additionally needs the original Munsit provider secrets and activation through LABEQ_VOICE_ENABLED.

Source and team credits are at https://github.com/LeenAlaslani/Labeq.
