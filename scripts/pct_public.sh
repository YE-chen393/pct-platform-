#!/usr/bin/env bash
# PCT Platform 公网发布脚本
# 用法:
#   bash scripts/pct_public.sh start   # 启动服务 + 公网隧道,打印公网 URL
#   bash scripts/pct_public.sh stop    # 停止服务 + 隧道
#   bash scripts/pct_public.sh status  # 查看状态
#   bash scripts/pct_public.sh restart # 重启
#   bash scripts/pct_public.sh logs    # 跟踪服务日志
#   bash scripts/pct_public.sh url     # 打印当前公网 URL

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PORT="${PCT_PORT:-7861}"
CFDIR="${CFDIR:-/public/home/ak1/.local/bin}"
CLOUDFLARED="$CFDIR/cloudflared"
TUNNEL_LOG="/tmp/pcf_tunnel_${PORT}.log"
URL_FILE="/tmp/pcf_public_url_${PORT}.txt"

# ---------- helpers ----------
is_app_running() {
  curl -s -m 2 -o /dev/null -w "%{http_code}" "http://127.0.0.1:${PORT}/" | grep -q 200
}

is_tunnel_running() {
  pgrep -f "cloudflared tunnel --url http://127.0.0.1:${PORT}" >/dev/null 2>&1
}

extract_url() {
  if [ -f "$TUNNEL_LOG" ]; then
    grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$TUNNEL_LOG" | head -1
  fi
}

# ---------- commands ----------
cmd_start() {
  echo "============================================================"
  echo "  PCT Platform 公网发布"
  echo "============================================================"

  # 1. 确保 cloudflared 已安装
  if [ ! -x "$CLOUDFLARED" ]; then
    echo "[1/3] 下载 cloudflared ..."
    mkdir -p "$CFDIR"
    curl -sL -o "$CLOUDFLARED" \
      "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    chmod +x "$CLOUDFLARED"
    echo "      完成"
  else
    echo "[1/3] cloudflared 已就绪 ($($CLOUDFLARED --version 2>&1 | head -1))"
  fi

  # 2. 启动 / 重启 Gradio 应用
  echo "[2/3] 启动 Gradio 应用 (端口 $PORT) ..."
  if is_app_running; then
    echo "      已在运行"
  else
    bash "$SCRIPT_DIR/pct_service.sh" start
  fi

  # 3. 启动 Cloudflare 隧道
  echo "[3/3] 启动 Cloudflare Tunnel (公网 HTTPS) ..."
  if is_tunnel_running; then
    echo "      已在运行"
  else
    : > "$TUNNEL_LOG"
    nohup "$CLOUDFLARED" tunnel --url "http://127.0.0.1:${PORT}" \
      --no-autoupdate --logfile "$TUNNEL_LOG" --loglevel info \
    --protocol http2 \
      > /dev/null 2>&1 &
    disown
    # 等待 URL 出现(最多 30 秒)
    URL=""
    for i in $(seq 1 30); do
      sleep 1
      URL=$(extract_url)
      if [ -n "$URL" ]; then
        break
      fi
    done
  fi

  echo "============================================================"
  URL=$(extract_url)
  if [ -n "$URL" ]; then
    echo "  公网访问(任何人可访问):"
    echo "    $URL"
    echo ""
    echo "  内网访问:"
    echo "    http://$(hostname):${PORT}"
    echo "============================================================"
    echo "$URL" > "$URL_FILE"
  else
    echo "  公网隧道启动失败,查看日志:"
    echo "    tail -f $TUNNEL_LOG"
  fi
}

cmd_stop() {
  echo "[stop] 停止 Cloudflare Tunnel ..."
  pkill -f "cloudflared tunnel --url http://127.0.0.1:${PORT}" 2>/dev/null || true
  echo "[stop] 停止 Gradio 应用 ..."
  bash "$SCRIPT_DIR/pct_service.sh" stop
  rm -f "$URL_FILE"
  echo "[stop] 完成"
}

cmd_status() {
  echo "==== Gradio 应用 ===="
  bash "$SCRIPT_DIR/pct_service.sh" status 2>&1
  echo ""
  echo "==== Cloudflare Tunnel ===="
  if is_tunnel_running; then
    PID=$(pgrep -f "cloudflared tunnel --url http://127.0.0.1:${PORT}")
    URL=$(extract_url)
    echo "  运行中 - PID=$PID"
    [ -n "$URL" ] && echo "  公网 URL: $URL"
    echo "  日志:$TUNNEL_LOG"
  else
    echo "  未运行"
  fi
}

cmd_url() {
  URL=$(extract_url)
  if [ -n "$URL" ]; then
    echo "$URL"
  else
    echo "(无 — 先运行: bash scripts/pct_public.sh start)" >&2
    return 1
  fi
}

cmd_logs() { tail -f /tmp/pct_app_${PORT}.log; }

case "${1:-}" in
  start)   cmd_start;;
  stop)    cmd_stop;;
  status)  cmd_status;;
  restart) cmd_stop; sleep 1; cmd_start;;
  logs)    cmd_logs;;
  url)     cmd_url;;
  *) echo "用法: $0 {start|stop|status|restart|logs|url}"; exit 1;;
esac
