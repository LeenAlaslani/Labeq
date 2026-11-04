#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PY="${LABEQ_MLX_PYTHON:-$PWD/.mlxvenv/bin/python}"
if [ ! -x "$PY" ]; then PY="$PWD/.mlxvenv/bin/python"; fi
if [ ! -x "$PY" ]; then echo 'نفذي bash prepare_local.sh أولًا'; exit 1; fi
if [ ! -f mlx_adapter/adapters.safetensors ]; then echo 'نفذي bash prepare_local.sh أولًا'; exit 1; fi
if lsof -nP -iTCP:7862 -sTCP:LISTEN >/dev/null 2>&1; then
  echo 'المنفذ 7862 مستخدم. أوقفي الخادم المحلي القديم قبل التشغيل.'; exit 1
fi
echo 'تحميل Saudi LoRA على الماك. إذا نجح يظهر سطر تم تحميل جميع أوزان LoRA.'
exec "$PY" -m uvicorn local_mlx_server:app --host 127.0.0.1 --port 7862 --workers 1
