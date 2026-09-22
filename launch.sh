#!/usr/bin/env bash
# PCT Platform Demo 启动脚本
# ===========================================================
# 自动检测 Python 解释器;优先用项目自带 venv,其次系统 python3。
# 用法:
#   bash launch.sh                  # 默认端口 7861
#   bash launch.sh --share          # Gradio 公网分享链接
#   PCT_PORT=8080 bash launch.sh    # 自定义端口
# ===========================================================
set -e
cd "$(dirname "$0")"
PROJECT_DIR="$(pwd)"
export PYTHONPATH="$PROJECT_DIR:${PYTHONPATH:-}"

# ---------- Python 自动检测 ----------
detect_python() {
  # 1. 用户显式指定
  if [ -n "${PYTHON_BIN:-}" ] && [ -x "$PYTHON_BIN" ]; then
    echo "$PYTHON_BIN"; return 0
  fi
  # 2. 项目内 venv
  for cand in "$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/venv/bin/python" \
              "$PROJECT_DIR/env/bin/python"; do
    if [ -x "$cand" ]; then echo "$cand"; return 0; fi
  done
  # 3. conda 环境(名字常为 ml / pytorch / base)
  for env in ml pytorch base root; do
    cand="$HOME/anaconda3/envs/$env/bin/python"
    [ -x "$cand" ] && { echo "$cand"; return 0; }
  done
  # 4. 系统 python3
  if command -v python3 >/dev/null 2>&1; then
    echo "$(command -v python3)"; return 0
  fi
  return 1
}

PYTHON_BIN="$(detect_python || true)"
if [ -z "$PYTHON_BIN" ]; then
  echo "[launch.sh] ❌ 找不到 Python 解释器。请安装 Python 3.10+ 或设置 PYTHON_BIN 环境变量。" >&2
  exit 1
fi

echo "[launch.sh] 项目目录: $PROJECT_DIR"
echo "[launch.sh] Python:    $PYTHON_BIN"
echo "[launch.sh] PYTHONPATH=$PYTHONPATH"

# ---------- 检查关键依赖 ----------
if ! "$PYTHON_BIN" -c "import gradio, pymatgen, matminer, pandas, numpy" >/dev/null 2>&1; then
  echo "[launch.sh] ⚠️  关键依赖缺失,尝试自动安装..."
  "$PYTHON_BIN" -m pip install -r "$PROJECT_DIR/requirements.txt" || {
    echo "[launch.sh] ❌ 依赖安装失败,请手动: $PYTHON_BIN -m pip install -r requirements.txt" >&2
    exit 1
  }
fi

PORT="${PCT_PORT:-7861}"
exec "$PYTHON_BIN" run.py --server-name 0.0.0.0 --server-port "$PORT" "$@"
