"""单组份预测 Tab — Scientific Dashboard 布局 v3

布局结构(参考 ui-ux-pro-max-skill 设计原则):

  Bento Grid 布局:
    ┌─────────────────┬────────────────────────────┐
    │  Hero Card      │  Quick Actions Card         │
    │  (输入区)       │  (示例材料快捷选择)          │
    ├─────────────────┴────────────────────────────┤
    │  Results Dashboard (Bento Grid)              │
    │  ┌────────┬────────┬────────┬────────┐      │
    │  │Metric  │Metric  │Metric  │Metric  │      │
    │  │  Card  │  Card  │  Card  │  Card  │      │
    │  └────────┴────────┴────────┴────────┘      │
    │  ┌───────────────────┬────────────┐        │
    │  │   Main Chart      │  Side     │        │
    │  │   (van't Hoff)    │  Info     │        │
    │  └───────────────────┴────────────┘        │
    └────────────────────────────────────────────┘
"""

from __future__ import annotations
import html
from pathlib import Path
import gradio as gr

from .predictor import predict_full


# ============================================================
# 步骤模板:统一大步骤卡样式
# ============================================================
_STEP_TPL = """
<div class="pct-step pct-step-{idx}">
  <div class="pct-step-bar"></div>
  <div class="pct-step-head">
    <span class="pct-step-num">{idx}</span>
    <span class="pct-step-icon">{icon}</span>
    <span class="pct-step-title">{title}</span>
    <span class="pct-step-status">●  待执行</span>
  </div>
  <div class="pct-step-body">
    {body}
  </div>
</div>
"""


def _step(idx: int, icon: str, title: str, body: str = "") -> str:
    return _STEP_TPL.format(idx=idx, icon=icon, title=title, body=body)


# ============================================================
# Bento Grid CSS
# ============================================================
BENTO_CSS = """
<style>
/* Bento Grid Layout */
.pct-bento-grid {
    display: grid;
    gap: 16px;
    margin: 16px 0;
}

.pct-bento-2col {
    grid-template-columns: 1fr 1fr;
}

.pct-bento-3col {
    grid-template-columns: 2fr 1fr;
}

.pct-bento-4col {
    grid-template-columns: repeat(4, 1fr);
}

.pct-bento-card {
    background: var(--pct-bg-card);
    border: 1px solid var(--pct-border);
    border-radius: var(--pct-radius-lg);
    padding: 20px;
    box-shadow: var(--pct-shadow-sm);
    transition: var(--pct-transition-normal);
}

.pct-bento-card:hover {
    box-shadow: var(--pct-shadow-md);
    transform: translateY(-2px);
}

.pct-bento-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--pct-border);
}

.pct-bento-card-title {
    font-size: 14px;
    font-weight: 700;
    color: var(--pct-text-primary);
    display: flex;
    align-items: center;
    gap: 8px;
}

.pct-bento-card-icon {
    width: 32px;
    height: 32px;
    background: var(--pct-primary-alpha);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
}

/* Metric Card */
.pct-metric-card {
    background: linear-gradient(135deg, var(--pct-bg-card) 0%, var(--pct-bg-panel) 100%);
    border: 1px solid var(--pct-border);
    border-radius: var(--pct-radius-lg);
    padding: 20px;
    text-align: center;
    transition: var(--pct-transition-normal);
    position: relative;
    overflow: hidden;
}

.pct-metric-card::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: var(--pct-primary);
}

.pct-metric-card:hover {
    transform: translateY(-3px);
    box-shadow: var(--pct-shadow-lg);
}

.pct-metric-card.success::before { background: var(--pct-success); }
.pct-metric-card.warning::before { background: var(--pct-warning); }
.pct-metric-card.danger::before { background: var(--pct-danger); }

.pct-metric-card-label {
    font-size: 11px;
    font-weight: 700;
    color: var(--pct-text-muted);
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
}

.pct-metric-card-value {
    font-size: 32px;
    font-weight: 800;
    color: var(--pct-text-primary);
    line-height: 1;
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.5px;
}

.pct-metric-card.success .pct-metric-card-value { color: var(--pct-success); }
.pct-metric-card.warning .pct-metric-card-value { color: var(--pct-warning); }
.pct-metric-card.danger .pct-metric-card-value { color: var(--pct-danger); }

.pct-metric-card-unit {
    font-size: 12px;
    color: var(--pct-text-muted);
    margin-top: 8px;
    font-weight: 500;
    letter-spacing: 0.3px;
}

/* 数值加载动效 */
.pct-metric-card-value.is-loading {
    background: linear-gradient(90deg, var(--pct-border-light) 0%, var(--pct-border) 50%, var(--pct-border-light) 100%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    color: transparent;
    border-radius: var(--pct-radius-sm);
}

@keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

/* Quick Actions */
.pct-quick-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
}

.pct-quick-btn {
    background: var(--pct-bg-card);
    border: 1px solid var(--pct-border);
    border-radius: 20px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 600;
    color: var(--pct-text-primary);
    cursor: pointer;
    transition: var(--pct-transition-fast);
}

.pct-quick-btn:hover {
    background: var(--pct-primary);
    color: white;
    border-color: var(--pct-primary);
    transform: translateY(-2px);
    box-shadow: var(--pct-shadow-md);
}

/* Input Card */
.pct-input-card {
    background: var(--pct-bg-card);
    border: 1px solid var(--pct-border);
    border-radius: var(--pct-radius-lg);
    padding: 24px;
    box-shadow: var(--pct-shadow-md);
}

.pct-input-card-title {
    font-size: 16px;
    font-weight: 700;
    color: var(--pct-text-primary);
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 10px;
}

.pct-input-card-title-icon {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, var(--pct-primary) 0%, var(--pct-secondary) 100%);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
}

/* Chart Container */
.pct-chart-container {
    background: var(--pct-bg-card);
    border: 1px solid var(--pct-border);
    border-radius: var(--pct-radius-lg);
    padding: 20px;
    box-shadow: var(--pct-shadow-sm);
}

.pct-chart-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
}

.pct-chart-title {
    font-size: 14px;
    font-weight: 700;
    color: var(--pct-text-primary);
}

/* Status Badge */
.pct-status-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}

.pct-status-badge.success {
    background: var(--pct-success-bg);
    color: var(--pct-success);
}

.pct-status-badge.warning {
    background: var(--pct-warning-bg);
    color: var(--pct-warning);
}

.pct-status-badge.danger {
    background: var(--pct-danger-bg);
    color: var(--pct-danger);
}

.pct-status-badge.info {
    background: var(--pct-primary-alpha);
    color: var(--pct-primary);
}

/* Loading State */
.pct-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 48px;
    background: var(--pct-bg-card);
    border: 1px solid var(--pct-border);
    border-radius: var(--pct-radius-lg);
}

.pct-loading-spinner {
    width: 40px;
    height: 40px;
    border: 3px solid var(--pct-border);
    border-top-color: var(--pct-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
    .pct-bento-2col,
    .pct-bento-3col {
        grid-template-columns: 1fr;
    }
    
    .pct-bento-4col {
        grid-template-columns: repeat(2, 1fr);
    }
}
</style>
"""


def build_single_tab() -> None:
    """注册单组份预测 Tab: Scientific Dashboard 布局."""

    # 注入 Bento Grid CSS
    gr.HTML(BENTO_CSS)

    # ===== Step 1:输入区 — Bento Grid 布局 =====
    gr.HTML(_step(
        1, "📝", "输入材料信息",
        "<span style='color:#64748b;font-size:13px;'>"
        "填化学式与 V0 → 下方按钮触发预测</span>",
    ))

    # Bento Grid: 输入 + 快捷操作
    with gr.Row():
        with gr.Column(scale=1, min_width=340):
            with gr.Group(elem_classes="pct-input-card"):
                gr.HTML("""
                    <div class="pct-input-card-title">
                        <div class="pct-input-card-title-icon">⚗️</div>
                        材料参数
                    </div>
                """)
                inp_formula = gr.Textbox(
                    label="材料化学式",
                    placeholder="例如 La0.7Y0.3Ni4.5Mn0.5",
                    value="La0.7Y0.3Ni4.5Mn0.5",
                    info="稀土储氢合金(必须含稀土元素),如 La/Y/Ce-Mn-Ni 系",
                    elem_classes="pct-input",
                    scale=1,
                )
                inp_V0 = gr.Slider(
                    label="V0  (模型训练时的基底参量)",
                    minimum=0, maximum=500, value=293.0, step=1,
                    info="稀土系填 ~293,其它填 ~290 试",
                    elem_classes="pct-input",
                )

                # 触发按钮
                btn = gr.Button(
                    "🚀 开始预测", variant="primary",
                    elem_classes="predict-btn", size="lg",
                )

        with gr.Column(scale=1, min_width=280):
            with gr.Group(elem_classes="pct-bento-card"):
                gr.HTML("""
                    <div class="pct-bento-card-header">
                        <div class="pct-bento-card-title">
                            <div class="pct-bento-card-icon">📚</div>
                            示例材料
                        </div>
                    </div>
                    <div class="pct-quick-actions">
                """)

                # 示例芯片 - 使用 grid 布局
                examples_data = [
                    ("La0.7Y0.3Ni4.5Mn0.5", "La0.7Y0.3Ni4.5Mn0.5", 293.0, "AB5"),
                    ("LaNi5", "LaNi5", 293.0, "AB5"),
                    ("La0.5Ce0.5Ni5", "La0.5Ce0.5Ni5", 293.0, "AB5"),
                    ("YNi5", "YNi5", 293.0, "AB5"),
                    ("La2Ni7", "La2Ni7", 293.0, "A2B7"),
                    ("LaNi3Mn1", "LaNi3Mn1", 293.0, "AB4"),
                ]

                for name, formula_, V0_, type_ in examples_data:
                    b = gr.Button(
                        f"{name} [{type_}]", 
                        size="sm", 
                        elem_classes="pct-quick-btn"
                    )
                    b.click(
                        fn=lambda f=formula_, v=V0_: (f, v),
                        inputs=[],
                        outputs=[inp_formula, inp_V0],
                    )

                gr.HTML("</div>")

    # ===== Step 2:结果区 — Bento Grid Dashboard =====
    gr.HTML(_step(
        2, "📊", "预测结果 — Scientific Dashboard",
        "<span style='color:#64748b;font-size:13px;'>"
        "执行预测后,数据将以 Bento Grid 布局展示</span>",
    ))

    # 指标卡片行
    gr.HTML("""
        <div class="pct-bento-grid pct-bento-4col" id="single-metrics">
    """)

    with gr.Group():
        out_metric_v5 = gr.HTML(
            value="""
            <div class="pct-metric-card">
                <div class="pct-metric-card-label">V5 (van't Hoff 斜率)</div>
                <div class="pct-metric-card-value">—</div>
                <div class="pct-metric-card-unit">kK</div>
            </div>
            """,
            elem_classes="pct-bento-col",
        )

        out_metric_v6 = gr.HTML(
            value="""
            <div class="pct-metric-card success">
                <div class="pct-metric-card-label">V6 (van't Hoff 截距)</div>
                <div class="pct-metric-card-value">—</div>
                <div class="pct-metric-card-unit">—</div>
            </div>
            """,
            elem_classes="pct-bento-col",
        )

        out_metric_cap = gr.HTML(
            value="""
            <div class="pct-metric-card warning">
                <div class="pct-metric-card-label">容量</div>
                <div class="pct-metric-card-value">—</div>
                <div class="pct-metric-card-unit">wt%</div>
            </div>
            """,
            elem_classes="pct-bento-col",
        )

        out_metric_p = gr.HTML(
            value="""
            <div class="pct-metric-card success">
                <div class="pct-metric-card-label">平台压 P₂₅℃</div>
                <div class="pct-metric-card-value">—</div>
                <div class="pct-metric-card-unit">MPa</div>
            </div>
            """,
            elem_classes="pct-bento-col",
        )

    gr.HTML("</div>")

    # 图表行 - 2列布局
    gr.HTML("""
        <div class="pct-bento-grid pct-bento-2col" id="single-charts">
    """)

    with gr.Group(elem_classes="pct-bento-card"):
        gr.HTML("""
            <div class="pct-chart-header">
                <div class="pct-chart-title">📈 van't Hoff Plot</div>
            </div>
        """)
        out_vh = gr.Image(label="van't Hoff 曲线",
                          elem_classes="pct-plot")

    with gr.Group(elem_classes="pct-bento-card"):
        gr.HTML("""
            <div class="pct-chart-header">
                <div class="pct-chart-title">🌡️ P-T 曲线</div>
            </div>
        """)
        out_pt = gr.Image(label="P-T 曲线", elem_classes="pct-plot")

    gr.HTML("</div>")

    # 第二行图表
    gr.HTML("""
        <div class="pct-bento-grid pct-bento-2col" id="single-charts-2">
    """)

    with gr.Group(elem_classes="pct-bento-card"):
        gr.HTML("""
            <div class="pct-chart-header">
                <div class="pct-chart-title">📊 PCT 等温曲线</div>
            </div>
        """)
        out_pct = gr.Image(label="PCT 等温线族", elem_classes="pct-plot")

    with gr.Group(elem_classes="pct-bento-card"):
        gr.HTML("""
            <div class="pct-chart-header">
                <div class="pct-chart-title">🔬 结构信息</div>
            </div>
        """)
        out_struct = gr.Markdown(label="结构信息")
        out_cif = gr.File(label="下载 CIF", interactive=False)

    gr.HTML("</div>")

    # 第三行 - 氢化物 + JSON
    gr.HTML("""
        <div class="pct-bento-grid pct-bento-2col" id="single-charts-3">
    """)

    with gr.Group(elem_classes="pct-bento-card"):
        gr.HTML("""
            <div class="pct-chart-header">
                <div class="pct-chart-title">💧 加氢后的氢化物</div>
            </div>
        """)
        # gr.State 作为 hidden 存储：output=存值，input=取当前值
        hidden_formula  = gr.State(value="")
        hidden_capacity = gr.State(value=None)
        hidden_history  = gr.State(value=[])
        inp_HM = gr.Slider(
            label="加氢比 H/M (0~3)",
            minimum=0.0, maximum=3.0, value=1.0, step=0.05,
            info="调整滑块实时生成不同 H/M 比的氢化物结构,并加入历史列表。"
                 "推荐值由预测容量 wt% 反推得到。",
            elem_classes="pct-input",
        )
        out_hyd = gr.HTML(
            value="<div style='color:#94a3b8;font-size:13px;'>💧 点击「🚀 开始预测」后将根据预测容量推荐加氢结构</div>",
            label="氢化物信息 & H/M / wt%",
        )
        out_hyd_cif = gr.File(label="下载当前 CIF", interactive=False)
        out_hyd_history = gr.HTML(
            value="<div style='color:#94a3b8;font-size:13px;'>📚 生成的氢化物历史将显示在此</div>",
            label="已生成结构列表",
        )
        btn_clear_hist = gr.Button(
            "🗑️  清空历史", size="sm", elem_classes="pct-quick-btn",
        )
        btn_dl_hist = gr.Button(
            "⬇️  下载全部历史 CIF (zip)",
            size="sm", elem_classes="pct-quick-btn",
        )
        out_hyd_zip = gr.File(
            label="氢化物 zip 包",
            interactive=False, visible=False,
        )

    with gr.Group(elem_classes="pct-bento-card"):
        gr.HTML("""
            <div class="pct-chart-header">
                <div class="pct-chart-title">📋 稳定性 & JSON</div>
            </div>
        """)
        out_phon = gr.Markdown(label="PhononBench 稳定性")
        out_json = gr.Markdown(label="JSON 输出")

    gr.HTML("</div>")

    # ===== 事件绑定 =====
    def _make_history_zip(history: list, formula: str) -> str | None:
        """把历史列表中所有 CIF 打包成 zip 返回路径。"""
        from zipfile import ZipFile
        import tempfile
        cifs = [(Path(e["cif_path"]), e.get("H_to_M", 0))
                for e in (history or [])
                if e.get("cif_path") and Path(e["cif_path"]).exists()]
        if not cifs:
            return None
        tmp = tempfile.NamedTemporaryFile(
            prefix=f"{formula.replace('/', '_')}_hydrogenation_",
            suffix=".zip", delete=False, dir="/tmp",
        )
        tmp.close()
        with ZipFile(tmp.name, "w") as zf:
            for path, hm in cifs:
                arcname = f"H_M_{hm:.2f}_{path.name}"
                zf.write(path, arcname)
        return tmp.name

    def _format_history(history: list, formula: str) -> str:
        """把 history 列表渲染成 HTML。"""
        if not history:
            return ("<div style='color:#94a3b8;font-size:13px;'>"
                    "📚 尚未生成结构 — 拖动滑块生成 H/M 比后会自动加入此处</div>")
        items = []
        for i, e in enumerate(history, 1):
            hm     = e.get("H_to_M", 0.0)
            nh     = e.get("n_H", "?")
            wt     = e.get("wt_pct", 0.0)
            proto  = e.get("prototype", "?")
            sg     = e.get("spacegroup", "?")
            cif    = e.get("cif_path", "")
            ts     = e.get("ts", "")
            badge  = "✅ 推荐" if e.get("is_recommended") else ""
            cif_name = Path(cif).name if cif else "—"
            file_exists = bool(cif and Path(cif).exists())
            if file_exists:
                size_kb = Path(cif).stat().st_size / 1024.0
                file_info = (
                    f'<span style="font-size:11px;color:#10b981;">'
                    f'✓ {size_kb:.1f} KB</span>'
                )
            else:
                file_info = (
                    f'<span style="font-size:11px;color:#ef4444;">'
                    f'⚠️ 文件不存在</span>'
                )
            items.append(
                f'<div class="pct-history-item" style="'
                f'padding:6px 10px;margin:4px 0;border-left:3px solid #0ea5e9;'
                f'background:#f8fafc;border-radius:4px;font-size:13px;">'
                f'<b>#{i}  H/M = {hm:.2f}</b>  '
                f'<span style="color:#64748b;">| n_H={nh} | wt%={wt:.2f}% | '
                f'{html.escape(str(proto))} ({html.escape(str(sg))}) | '
                f'{ts}</span> {badge}'
                f'<div style="font-size:11px;color:#94a3b8;margin-top:2px;">'
                f'📂 <code>{html.escape(cif_name)}</code> {file_info}'
                f'</div>'
                f'</div>'
            )
        n = len(history)
        return (
            f'<div class="pct-history-list">'
            f'<div style="font-weight:600;margin-bottom:6px;">'
            f'📚 已生成 {n} 个氢化物结构</div>'
            f'<div style="font-size:11px;color:#64748b;margin-bottom:6px;">'
            f'💡 点击下方新增的「⬇️ 下载全部历史 CIF (zip)」按钮可一次性下载所有结构;'
            f'当前显示的结构用下方「下载当前 CIF」组件下载。'
            f'</div>'
            + "\n".join(items) +
            f'</div>'
        )

    def _on_hm_change(formula: str, H_to_M: float, cap: float | None,
                       history: list):
        """滑块 change → 重新生成加氢结构,并加入历史列表。
        Returns: (hyd_html, hyd_cif, history_state, history_html)
        """
        from .predictor import hydrogenation_section
        if not formula:
            empty_html = ("<div style='color:#94a3b8;font-size:13px;'>"
                          "💧 先点击「🚀 开始预测」加载材料数据</div>")
            return empty_html, "", history or [], _format_history(history or [], formula)

        hyd_html, hyd_cif = hydrogenation_section(
            formula, fill_fraction=1.0, predicted_capacity=cap, H_to_M=H_to_M,
        )

        # 解析 hyd_html 中的 n_H 与 wt%(从 info 取更可靠,这里二次调用拿 info)
        from .predictor import hydrogenated_cif_for_download
        _, hyd_info = hydrogenated_cif_for_download(formula,
                                                     fill_fraction=1.0,
                                                     H_to_M=H_to_M)
        # 重要:防止重复,若同 H/M 已存在则不再添加
        new_hist = list(history or [])
        # 用 H_to_M 保留 3 位小数比较
        existing_keys = {round(float(e.get("H_to_M", -1)), 3) for e in new_hist}
        key = round(float(H_to_M), 3)
        if key not in existing_keys:
            from datetime import datetime
            is_rec = False
            if cap and cap > 0:
                from .predictor import recommended_H_to_M
                rec = recommended_H_to_M(formula, cap)
                is_rec = abs(H_to_M - rec) < 0.05
            new_hist.append({
                "H_to_M":        float(H_to_M),
                "n_H":           hyd_info.get("n_H", "?"),
                "wt_pct":        float(hyd_info.get("wt_pct", 0.0)),
                "prototype":     hyd_info.get("prototype", "?"),
                "spacegroup":    hyd_info.get("spacegroup", "?"),
                "cif_path":      hyd_cif,
                "ts":            datetime.now().strftime("%H:%M:%S"),
                "is_recommended": is_rec,
            })
        return hyd_html, hyd_cif, new_hist, _format_history(new_hist, formula)

    def _on_clear_history():
        return [], _format_history([], "")

    def _predict(formula: str, V0: float, progress=gr.Progress()):
        """ML 预测 + 把滑块跳到推荐 H/M + 把 formula/capacity/history 存入 state。"""
        import time
        from .predictor import predict_full
        progress(0.05, desc="⚙️  生成 Magpie 特征 ...")
        time.sleep(0.05)
        try:
            progress(0.30, desc="🧠  SVR (V5) ... 推理中 ...")
            time.sleep(0.05)
            progress(0.55, desc="🌳  LightGBM (V6) ... 推理中 ...")
            time.sleep(0.05)
            progress(0.80, desc="🌲  RandomForest ... 容量预测 ...")
            time.sleep(0.05)
            progress(0.95, desc="📈  绘制 van't Hoff / P-T / PCT ...")
            result = predict_full(formula, V0=V0)
            progress(1.0, desc="✅  完成")
            return result  # 17 个: 14 显示 + 3 hidden
        except Exception as e:
            progress(1.0, desc=f"❌ 失败:{e}")
            raise

    btn.click(
        _predict,
        inputs=[inp_formula, inp_V0],
        outputs=[
            out_metric_v5, out_metric_v6, out_metric_cap, out_metric_p,
            out_vh,       out_pt,        out_pct,
            out_struct,   out_cif,
            out_hyd,      out_hyd_cif,
            out_phon,     out_json,
            inp_HM,            # 13 — H/M slider 跳到推荐值
            hidden_formula,    # 14
            hidden_capacity,   # 15
            hidden_history,    # 16
        ],
    )

    # 滑块 change → 实时生成新结构并加入历史
    inp_HM.change(
        _on_hm_change,
        inputs=[hidden_formula, inp_HM, hidden_capacity, hidden_history],
        outputs=[out_hyd, out_hyd_cif, hidden_history, out_hyd_history],
    )

    # 清空历史
    btn_clear_hist.click(
        _on_clear_history,
        inputs=[],
        outputs=[hidden_history, out_hyd_history],
    )

    # 下载全部历史为 zip
    def _on_download_history(formula: str, history: list):
        zip_path = _make_history_zip(history, formula)
        if zip_path:
            return gr.update(value=zip_path, visible=True)
        return gr.update(value=None, visible=False)

    btn_dl_hist.click(
        _on_download_history,
        inputs=[hidden_formula, hidden_history],
        outputs=[out_hyd_zip],
    )
