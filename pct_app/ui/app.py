"""组装整个 Gradio Blocks: Hero + Tabs(single/batch) + Footer。"""

from __future__ import annotations
import gradio as gr

from .hero import HERO_HTML, FOOTER_HTML
from .single import build_single_tab
from .batch import build_batch_tab


def build_ui() -> gr.Blocks:
    """组装 Gradio Blocks,返回 demo 对象(由 run.py/launcher 调用 launch())。

    theme / css 按 Gradio 6.0 规范传给 launch() 而非 Blocks 构造函数。
    """
    with gr.Blocks(title="稀土储氢合金智能预测平台 · Demo") as demo:
        gr.HTML(HERO_HTML)

        with gr.Tabs():
            with gr.Tab("🎯 单组份预测"):
                build_single_tab()
            with gr.Tab("📊 批量预测"):
                build_batch_tab()

        gr.HTML(FOOTER_HTML)

    # 限制最大并发线程,减少 SSE 连接冲突导致的闪烁
    demo.max_threads = 1
    return demo
