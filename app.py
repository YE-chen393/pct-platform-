# -*- coding: utf-8 -*-
"""
PCT Platform Demo — 顶层入口模块
=================================

这个模块是兼容性 shim,实际实现全部在 pct_app 包里。

保留的原因:
  1. 让 `python -m app` 仍然可用(直接 demo 启动)
  2. 让一些不通过 pct_app 包路径的旧调用点能 import predict_three / featurize
  3. trio/CLI 脚本如果不想设置 PYTHONPATH,也能直接 `python app.py`

推荐使用 `run.py` 启动 Gradio UI(支持正确的 sys.path 注入)。
"""

from __future__ import annotations
from pct_app.ui import build_ui
from pct_app.ui.predictor import predict_full, predict_three

__all__ = ["build_ui", "predict_full", "predict_three"]


if __name__ == "__main__":
    # 直接 `python app.py` 也能起 demo
    import sys
    from pathlib import Path
    _ROOT = Path(__file__).resolve().parent
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    import gradio as gr
    from pct_app.ui.css import CUSTOM_CSS
    demo = build_ui()
    demo.launch(server_name="0.0.0.0", server_port=7861, css=CUSTOM_CSS, inbrowser=True)
