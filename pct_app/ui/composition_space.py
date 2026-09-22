"""稀土储氢合金 — 组份空间设计模块。

提供两个能力:

  1. ``build_periodic_table_ui(...)``
     ── 渲染元素周期表，点击元素 → 更新 hidden Textbox → 触发显示更新。
        稀土元素(Sc/Y + 15 Lanthanides)粉红高亮。

  2. ``generate_compositions(selected_symbols, ...)``
     ── 把用户在周期表里点选出的元素展开成实际的化学式列表。
        强制要求至少含 1 个稀土元素(否则安全策略直接返回空)。
"""

from __future__ import annotations
from typing import List, Tuple


# ============================================================
# 稀土元素定义
# ============================================================
RARE_EARTH_ELEMENTS = {
    "Sc", "Y",                       # 通常被算作稀土类
    "La", "Ce", "Pr", "Nd", "Pm", "Sm",
    "Eu", "Gd", "Tb", "Dy", "Ho", "Er",
    "Tm", "Yb", "Lu",
}


# ============================================================
# 周期表数据(精简版:Hydrogen → Copernicium)
# ============================================================
# 格式: (atomic_number, symbol, period, group, chinese_name)
_PERIODIC_TABLE: List[Tuple[int, str, int, int, str]] = [
    # Period 1
    (1,  "H",  1,  1,  "氢"), (2,  "He", 1, 18, "氦"),
    # Period 2
    (3,  "Li", 2,  1,  "锂"), (4,  "Be", 2,  2,  "铍"),
    (5,  "B",  2, 13, "硼"),  (6,  "C",  2, 14, "碳"),
    (7,  "N",  2, 15, "氮"),  (8,  "O",  2, 16, "氧"),
    (9,  "F",  2, 17, "氟"),  (10, "Ne", 2, 18, "氖"),
    # Period 3
    (11, "Na", 3,  1, "钠"),  (12, "Mg", 3,  2, "镁"),
    (13, "Al", 3, 13, "铝"),  (14, "Si", 3, 14, "硅"),
    (15, "P",  3, 15, "磷"),  (16, "S",  3, 16, "硫"),
    (17, "Cl", 3, 17, "氯"),  (18, "Ar", 3, 18, "氩"),
    # Period 4
    (19, "K",  4,  1, "钾"),  (20, "Ca", 4,  2, "钙"),
    (21, "Sc", 4,  3, "钪"),  (22, "Ti", 4,  4, "钛"),
    (23, "V",  4,  5, "钒"),  (24, "Cr", 4,  6, "铬"),
    (25, "Mn", 4,  7, "锰"),  (26, "Fe", 4,  8, "铁"),
    (27, "Co", 4,  9, "钴"),  (28, "Ni", 4, 10, "镍"),
    (29, "Cu", 4, 11, "铜"),  (30, "Zn", 4, 12, "锌"),
    (31, "Ga", 4, 13, "镓"),  (32, "Ge", 4, 14, "锗"),
    (33, "As", 4, 15, "砷"),  (34, "Se", 4, 16, "硒"),
    (35, "Br", 4, 17, "溴"),  (36, "Kr", 4, 18, "氪"),
    # Period 5
    (37, "Rb", 5,  1, "铷"),  (38, "Sr", 5,  2, "锶"),
    (39, "Y",  5,  3, "钇"),  (40, "Zr", 5,  4, "锆"),
    (41, "Nb", 5,  5, "铌"),  (42, "Mo", 5,  6, "钼"),
    (43, "Tc", 5,  7, "锝"),  (44, "Ru", 5,  8, "钌"),
    (45, "Rh", 5,  9, "铑"),  (46, "Pd", 5, 10, "钯"),
    (47, "Ag", 5, 11, "银"),  (48, "Cd", 5, 12, "镉"),
    (49, "In", 5, 13, "铟"),  (50, "Sn", 5, 14, "锡"),
    (51, "Sb", 5, 15, "锑"),  (52, "Te", 5, 16, "碲"),
    (53, "I",  5, 17, "碘"),  (54, "Xe", 5, 18, "氙"),
    # Period 6
    (55, "Cs", 6,  1, "铯"),  (56, "Ba", 6,  2, "钡"),
    # La(57)-Lu(71) 占位用 La/Y 占位
    (72, "Hf", 6,  4, "铪"),  (73, "Ta", 6,  5, "钽"),
    (74, "W",  6,  6, "钨"),  (75, "Re", 6,  7, "铼"),
    (76, "Os", 6,  8, "锇"),  (77, "Ir", 6,  9, "铱"),
    (78, "Pt", 6, 10, "铂"),  (79, "Au", 6, 11, "金"),
    (80, "Hg", 6, 12, "汞"),  (81, "Tl", 6, 13, "铊"),
    (82, "Pb", 6, 14, "铅"),  (83, "Bi", 6, 15, "铋"),
    (84, "Po", 6, 16, "钋"),  (85, "At", 6, 17, "砹"),
    (86, "Rn", 6, 18, "氡"),
    # Period 7
    (87, "Fr", 7,  1, "钫"),  (88, "Ra", 7,  2, "镭"),
    # Ac-Lr 占位
    (104, "Rf", 7,  4, "𬬻"),  (105, "Db", 7,  5, "𬭊"),
    (106, "Sg", 7,  6, "𬭳"),  (107, "Bh", 7,  7, "𬭶"),
    (108, "Hs", 7,  8, "𬭸"),  (109, "Mt", 7,  9, "鿏"),
    (110, "Ds", 7, 10, "𫟼"),  (111, "Rg", 7, 11, "𬬭"),
    (112, "Cn", 7, 12, "鿔"),
]

# 镧系(57-71)
_LANTHANIDES: List[Tuple[int, str, str]] = [
    (57,  "La", "镧"), (58,  "Ce", "铈"),
    (59,  "Pr", "镨"), (60,  "Nd", "钕"),
    (61,  "Pm", "钷"), (62,  "Sm", "钐"),
    (63,  "Eu", "铕"), (64,  "Gd", "钆"),
    (65,  "Tb", "铽"), (66,  "Dy", "镝"),
    (67,  "Ho", "钬"), (68,  "Er", "铒"),
    (69,  "Tm", "铥"), (70,  "Yb", "镱"),
    (71,  "Lu", "镥"),
]

# 锕系(89-103)
_ACTINIDES: List[Tuple[int, str, str]] = [
    (89,  "Ac", "锕"),  (90,  "Th", "钍"),
    (91,  "Pa", "镤"),  (92,  "U",  "铀"),
    (93,  "Np", "镎"),  (94,  "Pu", "钚"),
    (95,  "Am", "镅"),  (96,  "Cm", "锔"),
    (97,  "Bk", "锫"),  (98,  "Cf", "锎"),
    (99,  "Es", "锿"),  (100, "Fm", "镄"),
    (101, "Md", "钔"),  (102, "No", "锘"),
    (103, "Lr", "铹"),
]


# ============================================================
# 周期表 HTML 构建
# ============================================================
def _build_pt_html() -> str:
    """构建周期表 HTML(主表+镧系+锕系,整体紧凑布局)。"""
    # ---- 主周期表(1-7 周期)----
    main_cells = ""
    for _z, sym, period, group, _cn in _PERIODIC_TABLE:
        if sym == "La":
            # La 在主表中用占位符,镧系行另有 La 元素
            main_cells += (
                f'<div class="pt-cell pt-placeholder" '
                f'style="grid-column:{group};grid-row:{period};"></div>'
            )
        else:
            cls = "pt-cell pt-re" if sym in RARE_EARTH_ELEMENTS else "pt-cell"
            main_cells += (
                f'<div class="{cls}" id="pt-el-{sym}" '
                f'style="grid-column:{group};grid-row:{period};" '
                f'data-pt-el="{sym}">{sym}</div>'
            )

    # ---- 镧系行 ----
    lan_cells = ""
    lan_only = [(z, sym) for z, sym, _m in _LANTHANIDES]
    for idx, (_z, sym) in enumerate(lan_only):
        col = 3 + idx
        cls = "pt-cell pt-re"
        lan_cells += (
            f'<div class="{cls}" id="pt-el-{sym}" '
            f'style="grid-column:{col};grid-row:8;" '
            f'data-pt-el="{sym}">{sym}</div>'
        )

    # ---- 锕系行 ----
    act_cells = ""
    act_only = [(z, sym) for z, sym, _m in _ACTINIDES]
    for idx, (_z, sym) in enumerate(act_only):
        col = 3 + idx
        cls = "pt-cell"
        act_cells += (
            f'<div class="{cls}" id="pt-el-{sym}" '
            f'style="grid-column:{col};grid-row:9;" '
            f'data-pt-el="{sym}">{sym}</div>'
        )

    return (
        '<div class="pt-wrap">'
          '<div class="pt-periodic-main">'
            '<div class="pt-grid">' + main_cells + '</div>'
            '<div class="pt-separator">⬇ 镧系 La(57)–Lu(71) — 稀土★</div>'
            '<div class="pt-grid pt-rare-earth-grid">' + lan_cells + '</div>'
            '<div class="pt-separator">⬇ 锕系 Ac(89)–Lr(103)</div>'
            '<div class="pt-grid pt-rare-earth-grid">' + act_cells + '</div>'
          '</div>'
        '</div>'
    )


# ============================================================
# UI 构建
# ============================================================

# 增强的周期表 CSS
_PERIODIC_TABLE_CSS = """
<style>
/* 周期表容器 */
.pt-wrap {
    background: linear-gradient(180deg, var(--pct-bg-card) 0%, var(--pct-bg-panel) 100%);
    border: 1px solid var(--pct-border);
    border-radius: var(--pct-radius-lg);
    padding: 20px;
    margin: 12px 0 16px 0;
    overflow-x: auto;
    box-shadow: var(--pct-shadow-md);
}

.pt-periodic-main {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.pt-grid {
    display: grid;
    grid-template-columns: repeat(18, minmax(44px, 1fr));
    grid-auto-rows: minmax(44px, auto);
    gap: 5px;
    margin-bottom: 4px;
}

.pt-rare-earth-grid {
    grid-template-columns: repeat(18, minmax(44px, 1fr)) !important;
    gap: 5px !important;
}

.pt-cell {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 4px 2px 3px 2px;
    background: var(--pct-bg-card);
    border: 1px solid var(--pct-border);
    border-radius: 6px;
    cursor: pointer;
    user-select: none;
    font-size: 11px;
    line-height: 1.15 !important;
    color: var(--pct-text-primary);
    transition: all var(--pct-transition-fast);
    box-shadow: var(--pct-shadow-sm);
    min-width: 0;
    font-weight: 600;
}

.pt-cell:hover {
    background: var(--pct-primary-alpha);
    border-color: var(--pct-primary-light);
    transform: translateY(-2px);
    box-shadow: var(--pct-shadow-md);
    z-index: 2;
}

.pt-re {
    background: linear-gradient(180deg, #fdf2f8 0%, #fbcfe8 100%);
    border-color: #f9a8d4 !important;
    color: #9d174d !important;
    font-weight: 700;
}

.pt-re:hover {
    background: linear-gradient(135deg, #fce7f3 0%, #fbcfe8 100%);
}

.pt-placeholder {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    cursor: default !important;
    pointer-events: none !important;
}

.pt-selected {
    background: linear-gradient(135deg, var(--pct-primary) 0%, var(--pct-primary-dark) 100%) !important;
    border-color: transparent !important;
    color: white !important;
    box-shadow: 0 6px 16px rgba(30, 64, 175, 0.45) !important;
    transform: translateY(-3px) scale(1.05) !important;
    z-index: 3 !important;
}

.pt-selected.pt-re {
    background: linear-gradient(135deg, #db2777 0%, #be185d 100%) !important;
    border-color: transparent !important;
    box-shadow: 0 6px 16px rgba(219, 39, 119, 0.45) !important;
}

.pt-separator {
    font-size: 12px;
    color: var(--pct-text-secondary);
    font-weight: 700;
    letter-spacing: 0.5px;
    margin: 10px 0 4px 0;
    padding: 8px 12px;
    background: var(--pct-bg-panel);
    border-radius: var(--pct-radius-sm);
    text-align: center;
}

/* 状态框 */
.pt-status-box {
    flex: 1 1 300px;
    padding: 14px 18px;
    background: var(--pct-primary-alpha);
    border: 1px solid var(--pct-border);
    border-radius: var(--pct-radius-md);
    font-size: 12px;
    color: var(--pct-text-primary);
    line-height: 1.6 !important;
}

.pt-status-label {
    font-size: 11px;
    color: var(--pct-primary);
    font-weight: 700;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
    text-transform: uppercase;
}

.pt-current-list {
    font-family: "JetBrains Mono", "SF Mono", Consolas, monospace;
    font-size: 13px !important;
    color: var(--pct-primary);
    font-weight: 700;
    word-break: break-all;
}

/* 控制区域 */
.pt-controls {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    margin: 16px 0;
    padding: 16px;
    background: var(--pct-bg-panel);
    border-radius: var(--pct-radius-md);
}

.pt-control-item {
    flex: 1 1 200px;
}

.pt-buttons {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin: 16px 0;
}

/* 预览区域 */
.pt-preview-wrap {
    margin-top: 16px;
}

/* 芯片样式 */
.pct-chip-re {
    background: linear-gradient(135deg, #fce7f3 0%, #fbcfe8 100%);
    color: #9d174d;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 700;
    margin-right: 4px;
}

.pct-chip-b {
    background: var(--pct-primary-alpha);
    color: var(--pct-primary);
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 700;
    margin-right: 4px;
}

/* 成功提示 */
.pct-batch-success {
    background: var(--pct-success-bg);
    border: 2px solid var(--pct-success);
    border-radius: var(--pct-radius-lg);
    padding: 24px;
    text-align: center;
}

.pct-success-icon {
    font-size: 48px;
    margin-bottom: 12px;
}

.pct-success-title {
    font-size: 18px;
    font-weight: 700;
    color: var(--pct-success);
    margin-bottom: 8px;
}

.pct-success-hint {
    font-size: 13px;
    color: var(--pct-text-secondary);
    line-height: 1.6;
}
</style>
"""

# 隐藏组件 CSS
_HIDDEN_CSS = """
<style>
#pt-hidden-selected textarea, #pt-hidden-selected input,
#pt-formulas-hidden textarea, #pt-formulas-hidden input { 
    display: none !important; 
}
</style>
"""


def build_periodic_table_ui(
    hidden_textbox,
    status_textbox,
    generate_btn,
    send_btn,
    max_n_slider,
    strict_re_checkbox,
    preview_html,
    formulas_hidden,
    batch_file_ref,
    batch_preview_ref,
) -> None:
    """渲染元素周期表，点击元素 → 更新 hidden Textbox → 触发显示更新。"""
    import gradio as gr

    # ---- CSS ----
    gr.HTML(_PERIODIC_TABLE_CSS)
    gr.HTML(_HIDDEN_CSS)

    # ---- 渲染隐藏组件 ----
    hidden_textbox.render()
    formulas_hidden.render()
    status_textbox.render()
    max_n_slider.render()
    strict_re_checkbox.render()
    generate_btn.render()
    send_btn.render()
    preview_html.render()

    # ---- V0 滑块 (在「送入批量预测」前) — 用户从此处也能调节 V0 ----
    gr.HTML(
        '<div class="send-v0-slider-wrap">'
        '<div class="send-v0-label">'
        '<span class="send-v0-icon">🌡️</span>'
        'V0 (送入批量预测时统一应用的基底参量, K)'
        '</div>'
    )
    
    send_v0_slider = gr.Slider(
        label="🌡️ V0 值",
        minimum=200.0, maximum=500.0, value=293.0, step=1.0,
        info="默认 293.0 K (= 20℃)。下方生成的候选化学式都会用这个 V0 送入批量预测",
        elem_classes="pct-input",
    )
    
    gr.HTML('</div>')

    # ---- 主周期表 HTML ----
    js_on_load = r"""
(function() {
    function init() {
        document.querySelectorAll('[data-pt-el]').forEach(function(el) {
            el.style.cursor = 'pointer';
            el.addEventListener('click', function() {
                var sym = el.getAttribute('data-pt-el');
                el.classList.toggle('pt-selected');
                var hiddenInput = document.querySelector('#pt-hidden-selected textarea, #pt-hidden-selected input');
                if (hiddenInput) {
                    var selected = [];
                    document.querySelectorAll('.pt-selected[data-pt-el]').forEach(function(sel) {
                        selected.push(sel.getAttribute('data-pt-el'));
                    });
                    hiddenInput.value = selected.join(', ');
                    hiddenInput.dispatchEvent(new Event('input', { bubbles: true }));
                    hiddenInput.dispatchEvent(new Event('change', { bubbles: true }));
                }
            });
        });
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        setTimeout(init, 500);
    }
})();
"""

    gr.HTML(
        value=_build_pt_html(),
        js_on_load=js_on_load,
    )

    # ---- "生成预览" 按钮 ----
    def _generate_preview(hidden_txt: str, max_n: float, strict: bool):
        syms = [s.strip() for s in (hidden_txt or "").split(",") if s.strip()]
        if not syms:
            return "", """
        <div class="pct-empty-state pct-empty-state-error">
            <div class="pct-empty-icon">⚠️</div>
            <div class="pct-empty-title">尚未点选元素</div>
            <div class="pct-empty-hint">
                请在周期表上点击元素(稀土元素粉红色 ★)
            </div>
        </div>"""

        try:
            formulas = generate_compositions(
                syms, max_n=int(max_n), strict_re=bool(strict)
            )
        except Exception as e:
            return "", f"""
        <div class="pct-empty-state pct-empty-state-error">
            <div class="pct-empty-icon">❌</div>
            <div class="pct-empty-title">生成失败</div>
            <div class="pct-empty-hint">{e}</div>
        </div>"""

        if not formulas:
            return "", """
        <div class="pct-empty-state pct-empty-state-error">
            <div class="pct-empty-icon">⚠️</div>
            <div class="pct-empty-title">没有生成任何化学式</div>
            <div class="pct-empty-hint">
                请至少点选 1 个稀土元素(A 位)
            </div>
        </div>"""

        re_list = sorted(set(syms) & RARE_EARTH_ELEMENTS)
        b_list  = sorted(set(syms) - RARE_EARTH_ELEMENTS)
        re_chips = " ".join(f"<span class='pct-chip-re'>★ {s}</span>" for s in re_list) or "<span style='color:#94a3b8;'>(无)</span>"
        b_chips  = " ".join(f"<span class='pct-chip-b'>{s}</span>" for s in b_list) or "<span style='color:#94a3b8;'>(无)</span>"

        rows_html = ""
        for i, fml in enumerate(formulas[:30]):
            rows_html += f"<tr><td>{i+1}</td><td>{fml}</td></tr>"

        head = f"""
        <div class="pct-preview">
          <div class="pct-preview-meta">
            <div class="pct-meta-item">
              <span class="pct-meta-label">生成组份数</span>
              <span class="pct-meta-value">{len(formulas)}</span>
            </div>
            <div class="pct-meta-item">
              <span class="pct-meta-label">稀土(A 位)</span>
              <span class="pct-meta-chips">{re_chips}</span>
            </div>
            <div class="pct-meta-item">
              <span class="pct-meta-label">B 位元素</span>
              <span class="pct-meta-chips">{b_chips}</span>
            </div>
          </div>
          <div class="pct-preview-table-wrap">
            <table class="pct-preview-table">
              <thead><tr><th style="width:60px;">#</th><th>化学式</th></tr></thead>
              <tbody>
                {rows_html}
              </tbody>
            </table>
          </div>
          <div class="pct-preview-foot">
            显示前 {min(30, len(formulas))} 条,
            基于 AB5/A2B7/AB3/AB2/RE-TM-M 模板)
          </div>
        </div>"""

        return "\n".join(formulas), head

    generate_btn.click(
        _generate_preview,
        inputs=[hidden_textbox, max_n_slider, strict_re_checkbox],
        outputs=[formulas_hidden, preview_html],
    )

    # ---- "送入批量预测" 按钮 ----
    def _send_to_batch(hidden_txt: str, V0: float, progress=gr.Progress()):
        """从 formulas_hidden 读取化学式列表,使用用户设定的 V0 生成 CSV"""
        formulas = [f.strip() for f in (hidden_txt or "").split("\n") if f.strip()]
        if not formulas:
            return None, """
        <div class="pct-empty-state pct-empty-state-error">
            <div class="pct-empty-icon">⚠️</div>
            <div class="pct-empty-title">没有可用的化学式</div>
            <div class="pct-empty-hint">请先生成组份预览</div>
        </div>"""

        progress(0.1, desc="📋 正在生成 CSV...")
        import tempfile
        V0_value = float(V0) if V0 is not None else 293.0
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("formula,V0,name\n")
            for formula in formulas:
                f.write(f"{formula},{V0_value:.1f},\n")
            csv_path = f.name

        progress(0.5, desc=f"✅ 已生成 {len(formulas)} 条候选化学式 (V0={V0_value:.1f})")

        preview = f"""
        <div class="pct-batch-success">
            <div class="pct-success-icon">✅</div>
            <div class="pct-success-title">已生成 {len(formulas)} 条候选化学式</div>
            <div class="pct-success-hint">
                已应用 <b>V0 = {V0_value:.1f} K</b><br>
                已在下方「上传 CSV」处自动填入文件，点击 Step 3 开始批量预测
            </div>
        </div>"""

        progress(1.0, desc="完成")
        return csv_path, preview

    send_btn.click(
        _send_to_batch,
        inputs=[formulas_hidden, send_v0_slider],
        outputs=[batch_file_ref, batch_preview_ref],
    )


# ============================================================
# 组份空间生成器
# ============================================================
_STOICHIOMETRY_TEMPLATES = [
    ("AB5",  [("A", 1.0),  ("B", 5.0)]),
    ("A2B7", [("A", 2.0),  ("B", 7.0)]),
    ("AB3",  [("A", 1.0),  ("B", 3.0)]),
    ("AB2",  [("A", 1.0),  ("B", 2.0)]),
    ("RE(TM)4.5(M)0.5", [("A", 1.0), ("B", 4.5), ("B_alt", 0.5)]),
    ("RE(TM)3(M)1",     [("A", 1.0), ("B", 3.0), ("B_alt", 1.0)]),
]
_A_SITE_RATIOS = [1.0, 0.5, 0.7]


def _split_mixed_symbol(elem1: str, elem2: str, ratio: float) -> str:
    """把两个元素按 ratio:ratio 反比混合。ratio=0.5 表示 elem1:elem2 = 0.5:0.5"""
    r1 = ratio
    r2 = 1.0 - ratio
    return f"{elem1}{r1:.2f}{elem2}{r2:.2f}"


def _format_subscript(value: float) -> str:
    if abs(value - round(value)) < 1e-6:
        return str(int(round(value)))
    return f"{value:.2f}"


def generate_compositions(
    selected_symbols: List[str],
    max_n: int = 200,
    strict_re: bool = True,
) -> List[str]:
    """根据用户在周期表里点选的元素生成组份列表。

    规则:
      - 如果 ``strict_re=True`` 且 selected_symbols ∩ RARE_EARTH_ELEMENTS 为空 → 返回 []
      - 选取 1 个 A 位 + 1~3 个 B 位元素,枚举化学计量模板
      - A 位可混 RE(0.5/0.7 比例);B 位也可混多个 TM 元素
      - 输出按字典序、去重,截断 max_n 条
    """
    syms = [s.strip() for s in (selected_symbols or []) if s.strip()]
    if not syms:
        return []

    re_syms = [s for s in syms if s in RARE_EARTH_ELEMENTS]
    b_syms  = [s for s in syms if s not in RARE_EARTH_ELEMENTS]

    if strict_re and not re_syms:
        return []
    if not b_syms:
        # 只有 RE,固定 B = Ni
        b_syms = ["Ni"]

    out: List[str] = []

    # ---- 单 A + 单 B ----
    for a in re_syms:
        for b in b_syms:
            for ratio in _A_SITE_RATIOS:
                if ratio == 1.0:
                    a_part = a
                else:
                    re_other = [r for r in re_syms if r != a]
                    if re_other:
                        a_part = _split_mixed_symbol(a, re_other[0], ratio)
                    else:
                        a_part = a
                for name, parts in _STOICHIOMETRY_TEMPLATES:
                    parts_str = ""
                    for tag, val in parts:
                        if tag == "A":
                            parts_str += a_part + _format_subscript(val)
                        else:
                            parts_str += b + _format_subscript(val)
                    formula = parts_str
                    if formula not in out:
                        out.append(formula)
                    if len(out) >= max_n:
                        return sorted(out)

    # ---- 单 A + 双 B(主 / 次) ----
    if len(b_syms) >= 2:
        for a in re_syms:
            for i, b_main in enumerate(b_syms):
                for b_alt in b_syms[i+1:]:
                    for name, parts in _STOICHIOMETRY_TEMPLATES:
                        parts_str = ""
                        for tag, val in parts:
                            if tag == "A":
                                parts_str += a + _format_subscript(val)
                            elif tag == "B":
                                parts_str += b_main + _format_subscript(val)
                            elif tag == "B_alt":
                                parts_str += b_alt + _format_subscript(val)
                        formula = parts_str
                        if formula not in out:
                            out.append(formula)
                        if len(out) >= max_n:
                            return sorted(out)

    return sorted(out)
