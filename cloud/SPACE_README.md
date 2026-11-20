---
title: LABEQ
emoji: 💜
colorFrom: purple
colorTo: pink
sdk: gradio
app_file: cloud/space_app.py
python_version: "3.12"
pinned: false
---

# LABEQ · لبِق

Saudi Arabic communication coaching with the V16 interface, original Maha artwork, Qwen3.5-4B with a Saudi pilot LoRA adapter, and the original Faisal decision adapter. Requests use Gradio's queue and Hugging Face ZeroGPU.

The Saudi LoRA v2 candidate completed two epochs locally. Its held-out review found intent and dialect failures, so the pilot remains the configured research baseline. Replies require user review.

Faisal is Omer Nacar's Jev-inspired Arabic decision model under CC BY-NC 4.0. This Space is an attributed noncommercial research demonstration.

Configure the private adapter repository and its exact revision as LABEQ_ADAPTER_REPO and LABEQ_ADAPTER_REVISION. Store private model access in the HF_TOKEN Space secret. Maha speech additionally needs the original Munsit provider secrets and authorized usage credits.

Source and team credits are at https://github.com/LeenAlaslani/Labeq.
