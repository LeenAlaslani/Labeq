---
title: LABEQ private CPU quality check
emoji: 💜
colorFrom: purple
colorTo: pink
sdk: gradio
sdk_version: "6.32.0"
app_file: app.py
python_version: "3.12"
pinned: false
preload_from_hub:
  - unsloth/Qwen3.6-35B-A3B-GGUF Qwen3.6-35B-A3B-Q8_0.gguf a483e9e6cbd595906af30beda3187c2663a1118c
---

Private noncommercial LABEQ development diagnostic. CPU inference uses pinned unadapted Qwen3.6-35B-A3B Q8_0, not the Saudi response adapter. Original Faisal by Omer Nacar is attributed under CC BY-NC 4.0. The separately registered real GPU routing API is optional; evaluated full pipelines use actual CPU Faisal scoring. Development output is not a quality certification. No voice-provider key is included.
