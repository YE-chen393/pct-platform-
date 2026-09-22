"""UI 层:build_ui / CSS / Hero / 单 Tab / 批量 Tab

目标导入路径:
    from pct_app.ui import build_ui

run.py 使用:
    from pct_app.ui import build_ui
    demo = build_ui()
    demo.launch(...)
"""

from .css import CUSTOM_CSS
from .hero import HERO_HTML, FOOTER_HTML
from .single import build_single_tab
from .batch import build_batch_tab

# 延迟导入避免循环:app.py → single.py → predictor.py → core.*
# build_ui 放在这里而非 __init__ 末尾,可让 from pct_app.ui import build_ui 成立
def build_ui():
    """组装整个 Gradio Blocks。实际实现在 .app.build_ui。"""
    from .app import build_ui as _build_ui
    return _build_ui()

__all__ = [
    "CUSTOM_CSS",
    "HERO_HTML", "FOOTER_HTML",
    "build_single_tab", "build_batch_tab",
    "build_ui",
]
