#!/usr/bin/env bash
# PCT Platform 服务守护脚本
# 用法:
#   bash scripts/pct_service.sh start   # 启动并切到后台
#   bash scripts/pct_service.sh stop    # 停止
#   bash scripts/pct_service.sh status  # 查看状态
#   bash scripts/pct_service.sh logs    # 实时跟踪日志

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PORT="${PCT_PORT:-7861}"
# Python 解释器:优先用项目内 launch.sh 的 detect_python 逻辑,
# 或用户通过 PYTHON_BIN 显式覆盖,最后回退到系统 python3。
if [ -z "${PYTHON_BIN:-}" ]; then
  for cand in "$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/venv/bin/python" \
              "$HOME/anaconda3/envs/ml/bin/python" "$HOME/anaconda3/envs/pytorch/bin/python"; do
    [ -x "$cand" ] && PYTHON_BIN="$cand" && break
  done
fi
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3)}"

PID_FILE="/tmp/pct_app_${PORT}.pid"
LOG_FILE="/tmp/pct_app_${PORT}.log"

is_running() {
  [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

start() {
  if is_running; then
    echo "[pct] 已在运行,PID=$(cat "$PID_FILE"),端口=$PORT"
    echo "      日志:$LOG_FILE"
    return 0
  fi
  echo "[pct] 启动中...端口=$PORT,Python=$PYTHON_BIN"
  cd "$PROJECT_DIR"
  PYTHONPATH="$PROJECT_DIR:${PYTHONPATH:-}" \
    nohup "$PYTHON_BIN" run.py --server-port "$PORT" --server-name 0.0.0.0 \
    > "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  disown
  sleep 4
  if is_running; then
    echo "[pct] 已启动,PID=$(cat "$PID_FILE")"
    echo "      内网访问: http://$(hostname):$PORT"
    echo "      日志跟踪: tail -f $LOG_FILE"
  else
    echo "[pct] 启动失败,查看日志:"
    tail -20 "$LOG_FILE"
    return 1
  fi
}

stop() {
  if ! is_running; then
    echo "[pct] 未在运行"
    return 0
  fi
  PID=$(cat "$PID_FILE")
  echo "[pct] 停止 PID=$PID"
  kill "$PID" 2>/dev/null || true
  sleep 2
  kill -9 "$PID" 2>/dev/null || true
  rm -f "$PID_FILE"
  echo "[pct] 已停止"
}

status() {
  if is_running; then
    PID=$(cat "$PID_FILE")
    echo "[pct] 运行中 - PID=$PID - 端口=$PORT"
    echo "      URL: http://localhost:$PORT"
    echo "      日志:$LOG_FILE"
    curl -s -o /dev/null -w "      HTTP %{http_code} (本地探测)\n" http://127.0.0.1:$PORT/ || true
  else
    echo "[pct] 未运行"
  fi
}

logs() { tail -f "$LOG_FILE"; }

case "${1:-}" in
  start)  start;;
  stop)   stop;;
  status) status;;
  logs)   logs;;
  restart) stop; start;;
  *) echo "用法: $0 {start|stop|status|logs|restart}"; exit 1;;
esac
