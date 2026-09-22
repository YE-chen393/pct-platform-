#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PCT Platform Demo — 启动脚本
============================

启动:
    PYTHONPATH="$PWD:$PYTHONPATH" python run.py
    PYTHONPATH="$PWD:$PYTHONPATH" python run.py --share
    PYTHONPATH="$PWD:$PYTHONPATH" python run.py --server-port 7861
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

# 让 pct_app/ 作为顶层包可被 import
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import gradio as gr

from pct_app.ui import build_ui
from pct_app.ui.css import CUSTOM_CSS


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PCT Platform Gradio Demo")
    p.add_argument("--server-name", default="0.0.0.0",
                   help="默认 0.0.0.0")
    p.add_argument("--server-port", default=7861, type=int,
                   help="默认端口 7861")
    p.add_argument("--share", action="store_true",
                   help="启用 Gradio 公网分享链接")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # 在启动前打印可访问的 URL（因为 launch() 会阻塞主线程）
    import socket, sys
    print()
    print("=" * 64, flush=True)
    print(f"🚀 PCT Platform 启动中 — 端口 {args.server_port}", flush=True)
    print("=" * 64, flush=True)
    print("📌 本机访问:", flush=True)
    print(f"   http://127.0.0.1:{args.server_port}", flush=True)
    print(f"   http://localhost:{args.server_port}", flush=True)
    try:
        hostname = socket.gethostname()
        try:
            primary_ip = socket.gethostbyname(hostname)
            print(f"   主机名 {hostname}: http://{primary_ip}:{args.server_port}", flush=True)
        except Exception:
            pass
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            lan_ip = s.getsockname()[0]
            print(f"   本机 LAN IP: http://{lan_ip}:{args.server_port}", flush=True)
        finally:
            s.close()
        try:
            import psutil as _ps
            addrs = _ps.net_if_addrs()
            print(flush=True)
            print("   所有网卡接口:", flush=True)
            for iface, addr_list in addrs.items():
                for a in addr_list:
                    if a.family == socket.AF_INET and not a.address.startswith("127."):
                        print(f"     - {iface}: http://{a.address}:{args.server_port}", flush=True)
        except ImportError:
            pass
    except Exception as e:
        print(f"   (检测 IP 失败: {e})", flush=True)
    print("=" * 64, flush=True)
    print(flush=True)

    demo = build_ui()
    demo.launch(
        server_name="0.0.0.0",  # 绑定所有网卡(局域网/远程均可访问)
        server_port=args.server_port,
        show_error=False,
        share=args.share,
        theme=gr.themes.Soft(),
        css=CUSTOM_CSS,
        inbrowser=True,  # 有显示器时自动打开浏览器
    )


if __name__ == "__main__":
    main()
