"""结构生成 + 加氢(CIF 输出)。

完全 delegate 给 vendor.pct_toolkit_wrapper,hydrogenate_via_voidsize 内部会:
  - 用 Wyckoff CSV + 几何过滤确定 H 占据
  - 写 CIF 到 assets/

加氢主入口已搬迁到 pct_app.ui.predictor.hydrogenated_cif_for_download,
本模块只保留原始结构(skeleton)的 CIF 输出。
"""

from __future__ import annotations
from ..config.paths import ASSETS_DIR


def structure_to_cif_for_download(formula: str):
    """根据化学式构造候选结构 → 写 CIF 文件到 assets/,返回路径。

    失败时返回 None,避免 Gradio File 组件收到空字符串时尝试打开父目录。
    """
    from vendor.pct_toolkit_wrapper import full_pipeline as _fp
    try:
        r = _fp(formula, V0=293.0)
    except Exception:
        return None
    out = ASSETS_DIR / f"{formula.replace('/', '_').replace(' ', '')}.cif"
    try:
        out.write_text(r["cif"])
    except Exception:
        return None
    return str(out)
