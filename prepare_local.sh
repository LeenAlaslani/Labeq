#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# Reuse the already working Qwen MLX environment from the user's earlier test.
PY="${LABEQ_MLX_PYTHON:-$PWD/.mlxvenv/bin/python}"
if [ ! -x "$PY" ]; then
  echo 'لم أجد بيئة اختبار MLX السابقة. أنشئ بيئة مستقلة...'
  python3 -m venv .mlxvenv
  PY="$PWD/.mlxvenv/bin/python"
fi
if ! "$PY" -c 'import mlx_vlm, fastapi, uvicorn, dotenv, safetensors, numpy' >/dev/null 2>&1; then
  echo 'تثبيت المكتبات اللازمة للمودل المحلي (مرة واحدة)...'
  "$PY" -m pip install -U mlx-vlm fastapi uvicorn python-dotenv safetensors numpy
fi
"$PY" setup_local.py
ZIP_PATH="${LABEQ_LORA_ZIP:-$PWD/LABEQ_Saudi_LoRA_Backup.zip}"
"$PY" convert_peft_to_mlx.py --zip "$ZIP_PATH" --output "$PWD/mlx_adapter"
printf '\n✅ نسخة الماك جاهزة للفحص.\nشغلي في هذه النافذة: bash start_local_model.sh\nوفي Terminal آخر: bash run_mac.sh\n'
