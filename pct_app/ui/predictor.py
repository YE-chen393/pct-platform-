"""UI 层后端:predict_full / predict_three — Gradio 主回调与模型推理。"""

from __future__ import annotations
import html
import time
import numpy as np
from pathlib import Path

import gradio as gr
from pymatgen.core import Composition

from ..core.featurize import featurize
from ..core.io import MODEL_REGISTRY
from ..core.plots import plot_vant_hoff, plot_p_vs_T, plot_pct_isotherms
from ..core.structures import structure_to_cif_for_download
from ..core.phonon import phonon_check_stub
from ..config.paths import ASSETS_DIR


# ============================================================
# 核心推理:三个模型 + 平台压
# ============================================================

def predict_three(formula: str, V0: float = 293.0) -> dict:
    """预测 V5、V6、Capacity 并计算 25℃ 平台压。"""
    magpie_df, comp = featurize(formula)
    out = {
        "formula":   formula,
        "reduced":   comp.reduced_formula,
        "fraction":  comp.fractional_composition.as_dict(),
        "V5": None, "V6": None, "Capacity": None,
        "P_298K": None, "warnings": [],
    }

    for name, (m, scX, scY, feats) in MODEL_REGISTRY.items():
        vals, miss = [], []
        for f in feats:
            if f == "V0":
                vals.append(V0)
            elif f in magpie_df.columns:
                vals.append(magpie_df[f].values[0])
            else:
                miss.append(f)
                vals.append(np.nan)
        if miss:
            out["warnings"].append(f"{name} 缺失特征 {len(miss)} 项:{miss[:3]}…")

        X = np.array(vals, dtype=float).reshape(1, -1)
        try:
            if scX is not None:
                pred_scaled = m.predict(scX.transform(X))
                pred = scY.inverse_transform(pred_scaled.reshape(-1, 1)).ravel()[0]
            else:
                pred = m.predict(X)[0]
            out[name] = float(pred)
        except Exception as e:
            out[name] = None
            out["warnings"].append(f"{name} 预测失败: {e}")

    # 25℃ 平台压
    if out["V5"] is not None and out["V6"] is not None:
        T_ref = 298.15
        lnP = (out["V5"] * 1000.0) / T_ref + out["V6"]
        out["P_298K"] = float(np.exp(lnP))
    return out


# ============================================================
# 加氢 CIF
# ============================================================

def hydrogenated_cif_for_download(formula: str, fill_fraction: float = 1.0,
                                  H_to_M: float | None = None):
    """
    构造加氢后的氢化物结构 → 写 CIF + 返回路径与统计。
    使用 vendor/pct_toolkit_wrapper 的 Wyckoff CSV + 几何过滤确定 H 占据。

    Args:
        H_to_M: 直接指定 H/M 比 (0~3), 优先于 fill_fraction。
        fill_fraction: 0~1 填充比例(备选)。
    """
    from vendor.pct_toolkit_wrapper import (
        hydrogenate_via_voidsize,
        structure_to_cif as _cif,
    )
    try:
        hyd, info = hydrogenate_via_voidsize(formula,
                                              fill_fraction=fill_fraction,
                                              H_to_M=H_to_M)
        cif = _cif(hyd)
        # 文件名用 H/M 标记以避免重复
        ratio_label = (f"H{H_to_M:.2f}".replace(".", "_")
                       if H_to_M is not None else
                       f"F{fill_fraction:.2f}".replace(".", "_"))
        tag = f"{formula.replace('/', '_').replace(' ', '')}_{ratio_label}"
        out = ASSETS_DIR / f"{tag}.cif"
        out.write_text(cif)
        return str(out), info
    except Exception as e:
        return None, {"error": str(e), "H_added": 0}


# ============================================================
# 根据预测容量计算推荐的 H/M 比
# ============================================================

def recommended_H_to_M(formula: str, capacity_wt_pct: float) -> float:
    """根据 ML 预测的储氢容量 (wt%) 计算推荐的 H/M 比。

    公式: wt% = M_H / (M_total) × 100%
         n_H = wt% × M_integer / (100 × M_H - wt% × M_H)
         H/M = n_H / N_metal_per_fu

    返回值钳制到 [0.05, 3.0] 范围。
    """
    from pymatgen.core import Composition
    M_H = 1.008
    comp = Composition(formula)
    int_formula, _ = comp.get_integer_formula_and_factor()
    int_comp = Composition(int_formula)
    mw = float(int_comp.weight)
    N_metal = float(sum(amt for el, amt in int_comp.items() if str(el) != "H"))

    # 防止除零
    if capacity_wt_pct <= 0 or capacity_wt_pct >= 100:
        return 0.05
    # n_H per formula unit
    n_H = capacity_wt_pct * mw / (100.0 * M_H - capacity_wt_pct * M_H)
    H_to_M = n_H / N_metal
    return max(0.05, min(3.0, H_to_M))


def recommended_fill_fraction(formula: str, capacity_wt_pct: float) -> float:
    """根据 ML 预测的储氢容量 (wt%) 计算推荐的加氢填充比例。

    对于 AB5 型合金,理论最大 H/M≈1.0 → ~1.38 wt%;
    对于 AB2  Laves,理论最大 H/M≈1.0  → ~2.07 wt%;
    对于 MgH2,理论最大 H/M≈2.0  → ~7.66 wt%。
    这里用 H_to_M 基准来算 fill_fraction = recommended_H_to_M / H_to_M_max。
    """
    H_to_M = recommended_H_to_M(formula, capacity_wt_pct)
    # 按材料类型取理论最大 H/M
    import re
    formula_clean = re.sub(r'[\d.]+', '', formula).strip()
    if 'Mg' in formula_clean and 'Ni' not in formula_clean:
        H_M_max = 2.0
    elif 'Al' in formula_clean or 'B' in formula_clean:
        H_M_max = 3.0
    elif 'Ti' in formula_clean and 'Fe' in formula_clean:
        H_M_max = 1.0
    else:
        H_M_max = 1.0   # AB5 默认
    return max(0.2, min(1.0, H_to_M / H_M_max))


def hydrogenation_section(formula: str, fill_fraction: float = 1.0,
                          predicted_capacity: float | None = None,
                          H_to_M: float | None = None,
                          history: list | None = None) -> tuple:
    """生成加氢结构 section HTML + CIF 路径,并标注推荐值来源。

    Args:
        H_to_M: 当前滑块的 H/M 比值 (0~3)。
        history: 历史生成的结构列表 [(H_to_M, n_H, wt_pct, cif_path), ...]

    返回 (HTML 字符串, CIF 路径)。
    """
    import html

    hyd_cif_path, hyd_info = hydrogenated_cif_for_download(
        formula, fill_fraction=fill_fraction, H_to_M=H_to_M,
    )

    # 计算推荐值标注
    rec_label = ""
    if predicted_capacity and predicted_capacity > 0:
        rec_H_to_M = recommended_H_to_M(formula, predicted_capacity)
        if H_to_M is not None:
            is_recommended = abs(H_to_M - rec_H_to_M) < 0.05
            badge_text = "推荐" if is_recommended else f"建议 H/M ≈ {rec_H_to_M:.2f}"
        else:
            is_recommended = False
            badge_text = f"建议 H/M ≈ {rec_H_to_M:.2f}"
        rec_label = (
            f'<span style="color:#64748b;font-size:12px;margin-left:10px;">'
            f'{"✅" if is_recommended else "ℹ️"} {badge_text} | 预测容量 {predicted_capacity:.2f} wt%</span>'
        )

    # 核心信息行
    proto    = html.escape(hyd_info.get('prototype', '?'))
    spacegrp = html.escape(hyd_info.get('spacegroup', '?'))
    n_metal  = hyd_info.get('n_metal', '?')
    n_H      = hyd_info.get('n_H', '?')
    h_to_m   = hyd_info.get('H_to_M', 0.0)
    wt_pct   = hyd_info.get('wt_pct', 0.0)
    sites_txt = " ".join(f"<code>{html.escape(s)}</code>" for s in hyd_info.get('filled_sites', []))
    err_msg  = hyd_info.get('error', '')
    cif_path = str(hyd_cif_path) if hyd_cif_path else None
    capped   = hyd_info.get('capped', False)
    h_to_m_max_ach = hyd_info.get('H_to_M_max_achievable', h_to_m)
    auto_expanded = hyd_info.get('auto_expanded', False)
    actual_sc = hyd_info.get('supercell', 2)

    cap_warning = ""
    # 显示扩展信息:当超胞被自动扩展时(无论是否完全达到目标)
    if auto_expanded and H_to_M is not None:
        cap_warning = (
            f'<div style="margin-top:8px;padding:6px 10px;background:#dbeafe;'
            f'border-left:3px solid #3b82f6;border-radius:4px;font-size:12px;color:#1e40af;">'
            f'ℹ️ 请求 H/M = {H_to_M:.2f} 时,为容纳该 H 数量,'
            f'超胞已自动扩展到 <b>{actual_sc}×{actual_sc}×1</b>。<br/>'
            f'   实际生成 H/M = <b>{h_to_m:.2f}</b>, n_H = {n_H}。'
            f'</div>'
        )
    elif capped and H_to_M is not None:
        cap_warning = (
            f'<div style="margin-top:8px;padding:6px 10px;background:#fef3c7;'
            f'border-left:3px solid #f59e0b;border-radius:4px;font-size:12px;color:#92400e;">'
            f'⚠️ 请求 H/M = {H_to_M:.2f} 超过结构可用间隙位上限。<br/>'
            f'   实际生成 H/M = <b>{h_to_m:.2f}</b>, n_H = {n_H}。<br/>'
            f'   此材料的最大可加氢量约为 {h_to_m_max_ach:.2f} H/M。'
            f'</div>'
        )

    if hyd_cif_path and "error" not in hyd_info:
        card = (
            f'<div class="pct-hyd-card">'
            f'  <div style="margin-bottom:8px;">'
            f'    <strong style="font-size:14px;">💧 {html.escape(formula)} 加氢结构</strong>'
            f'    {rec_label}'
            f'  </div>'
            f'  <table style="width:100%;border-collapse:collapse;font-size:13px;">'
            f'    <tr><td style="padding:2px 8px 2px 0;color:#64748b;">原型</td>'
            f'        <td><code>{proto}</code></td>'
            f'        <td style="padding:2px 8px;color:#64748b;">空间群</td>'
            f'        <td>{spacegrp}</td></tr>'
            f'    <tr><td style="padding:2px 8px 2px 0;color:#64748b;">金属原子</td>'
            f'        <td>{n_metal}</td>'
            f'        <td style="padding:2px 8px;color:#64748b;">H 原子</td>'
            f'        <td><b style="color:#0ea5e9">{n_H}</b></td></tr>'
            f'    <tr><td style="padding:2px 8px 2px 0;color:#64748b;">H/M 比</td>'
            f'        <td><b style="color:#10b981">{h_to_m:.3f}</b></td>'
            f'        <td style="padding:2px 8px;color:#64748b;">储氢 wt%</td>'
            f'        <td><b style="color:#f59e0b">{wt_pct:.2f}%</b></td></tr>'
            f'  </table>'
            f'  <div style="margin-top:6px;font-size:12px;color:#64748b;">Wyckoff: {sites_txt}</div>'
            f'  {cap_warning}'
            f'  <div style="margin-top:8px;padding:6px 10px;background:#f0f9ff;border:1px dashed #0ea5e9;'
            f'border-radius:4px;font-size:12px;color:#0369a1;">'
            f'    📂 当前 CIF: <code>{Path(cif_path).name if cif_path else "—"}</code><br/>'
            f'    👉 请使用下方「下载当前 CIF」组件获取文件'
            f'  </div>'
            f'</div>'
        )
    elif err_msg:
        card = f'<div style="color:#ef4444;font-size:13px;">⚠️ 加氢失败: {html.escape(err_msg)}</div>'
    else:
        card = f'<div style="color:#ef4444;font-size:13px;">⚠️ 加氢 CIF 生成失败</div>'

    return card, cif_path


# ============================================================
# Gradio 主回调:单组份完整预测
# ============================================================

def _metric_html(label: str, value: str, unit: str, kind: str = "") -> str:
    """生成 metric 卡片 HTML,与前端 pct-metric-card 样式一致。"""
    cls = f"pct-metric-card {kind}".strip()
    return (
        f'<div class="{cls}">'
        f'<div class="pct-metric-card-label">{label}</div>'
        f'<div class="pct-metric-card-value">{value}</div>'
        f'<div class="pct-metric-card-unit">{unit}</div>'
        f'</div>'
    )


def predict_full(formula: str, V0: float, progress=gr.Progress()):
    """Gradio 主回调:逐步预测 → 出图 → 出报告。

    返回顺序(17 个,严格匹配前端 outputs):
      0  out_metric_v5     HTML
      1  out_metric_v6     HTML
      2  out_metric_cap    HTML
      3  out_metric_p      HTML
      4  out_vh            plot
      5  out_pt            plot
      6  out_pct           plot
      7  out_struct        Markdown
      8  out_cif           File path
      9  out_hyd           Markdown
      10 out_hyd_cif       File path
      11 out_phon          Markdown
      12 out_json          Markdown
      13 inp_HM            float   (推荐 H/M)
      14 hidden_formula    str
      15 hidden_capacity   float
      16 hidden_history    list

    防崩溃约定:
      - 任何子步骤失败,只让该步骤显示错误,绝不 re-raise
      - 因为 Gradio worker 线程一旦异常上抛,会让整个 SSE 连接断掉,
        浏览器侧就显示 "Connection to the server was lost"
      - 返回的 tuple 始终保持 17 个元素,顺序与 UI 严格对齐
    """
    # ---- 默认返回值模板(每种错误都用同一个 shape) ----
    def _err_tuple(msg: str):
        e1 = _metric_html("V5 (van't Hoff 斜率)", "—", "kK", "danger")
        e2 = _metric_html("V6 (van't Hoff 截距)", "—", "—", "danger")
        e3 = _metric_html("容量", "—", "wt%", "danger")
        e4 = _metric_html("平台压 P₂₅℃", "—", "MPa", "danger")
        return (
            e1, e2, e3, e4,        # 0~3 metric
            None, None, None,      # 4~6 plots
            msg, None,             # 7~8 struct
            "", None,              # 9~10 hydride
            "", "",                # 11~12 phon + json
            0.5, "", None, [],     # 13~16 hidden
        )

    # ---- 输入校验(空 / 化学式非法) ----
    if not formula or not formula.strip():
        return _err_tuple("❌ 请输入材料化学式")

    formula = formula.strip()
    try:
        Composition(formula)
    except Exception as e:
        return _err_tuple(f"❌ 化学式解析失败:{e}")

    # ---- V0 范围保护(模型训练时 V0≈293;过大/过小会触发极端预测)----
    if V0 is None or not np.isfinite(float(V0)):
        V0 = 293.0
    if V0 < 0 or V0 > 1000:
        return _err_tuple(
            f"❌ V0 = {V0:.1f} 超出合理范围(0 ~ 1000),"
            "稀土系请填 ~293,其它试 ~290"
        )

    # ---- 进度回调(防止 progress 为 None) ----
    def _progress(step: float, desc: str = "") -> None:
        if progress is not None:
            try:
                progress(step, desc=desc)
            except Exception:
                pass

    # ---- 顶部 try:任何未捕获的异常都收敛到 err_tuple ----
    try:
        _progress(0.05, "⚙️  生成 Magpie 特征 ...")
        time.sleep(0.02)

        _progress(0.30, "🧠  SVR (V5) ... 推理中 ...")
        time.sleep(0.02)
        _progress(0.55, "🌳  LightGBM (V6) ... 推理中 ...")
        time.sleep(0.02)
        _progress(0.80, "🌲  RandomForest ... 容量预测 ...")
        time.sleep(0.02)

        # === 1) 模型推理 ===
        try:
            res = predict_three(formula, V0=V0)
        except Exception as e:
            return _err_tuple(f"❌ 模型推理失败:{e}")

        V5, V6, Cap = res.get("V5"), res.get("V6"), res.get("Capacity")

        if V5 is None or V6 is None or not np.isfinite(V5) or not np.isfinite(V6):
            warn_txt = (
                f"❌ 预测失败,警告:{res.get('warnings', [])}"
                if res.get("warnings") else "❌ 预测失败(模型输出 NaN/Inf)"
            )
            return _err_tuple(warn_txt)

        # === 2) 4 张 metric 卡片 ===
        _progress(0.90, "📈  绘制 van't Hoff / P-T / PCT ...")
        try:
            m_v5 = _metric_html("V5 (van't Hoff 斜率)", f"{float(V5):.4f}", "kK")
            m_v6 = _metric_html("V6 (van't Hoff 截距)", f"{float(V6):.4f}", "—", "success")
            cap_str = f"{float(Cap):.3f}" if (Cap is not None and np.isfinite(Cap)) else "—"
            m_cap = _metric_html("容量", cap_str, "wt%", "warning")
            P_val = res.get("P_298K")
            if P_val is not None and np.isfinite(P_val):
                if abs(P_val) >= 1e-3:
                    p_str = f"{P_val:.3f}"
                else:
                    p_str = f"{P_val:.2e}"
            else:
                p_str = "—"
            m_p = _metric_html("平台压 P₂₅℃", p_str, "MPa", "success")
        except Exception as e:
            return _err_tuple(f"❌ 指标卡片渲染失败:{e}")

        # === 3) 三张图(各自独立 try/except,一张失败不影响其它)===
        def _safe_plot(plot_fn, *args, **kwargs):
            try:
                return plot_fn(*args, **kwargs)
            except Exception as e:
                print(f"[predict_full] {plot_fn.__name__} failed: {e}", flush=True)
                return None

        p1 = _safe_plot(plot_vant_hoff, V5, V6, formula)
        p2 = _safe_plot(plot_p_vs_T,   V5, V6, formula)
        p3 = _safe_plot(plot_pct_isotherms, V5, V6, formula, capacity_mol_per_kg=Cap)

        # === 4) 结构生成(可能很慢,做单独 try) ===
        struct_md_lines = [
            f"### 🧱 {formula} 结构生成  (via PCT-Simulation-Toolkit)",
            "",
        ]
        cif_path = None
        try:
            from vendor.pct_toolkit_wrapper import full_pipeline as _fp2
            r_pipe = _fp2(formula, V0=V0)
            sites = r_pipe['interstitial'].get('sites', {}) or {}
            proto_name = r_pipe.get('prototype', '?')
            n_atoms = getattr(r_pipe.get('structure'), 'num_sites', '?')
            volume = getattr(r_pipe.get('structure'), 'volume', float('nan'))
            spg = r_pipe['interstitial'].get('spacegroup', '?')
            struct_md_lines += [
                f"- **结构原型**: `{proto_name}`",
                f"- **超胞**: 2×2×1 = {n_atoms} 个原子",
                f"- **晶胞体积**: {float(volume):.2f} Å³",
                f"- **空间群**: {spg}",
                "",
                f"**可用间隙位(Wyckoff)**:" +
                (" " + ", ".join(list(sites.keys())[:8]) if sites else " 无"),
                "",
            ]
            cif_path = _safe_plot(structure_to_cif_for_download, formula)
            if cif_path:
                struct_md_lines.append(
                    f"**下载 CIF**: `{cif_path}` ({Path(cif_path).stat().st_size} bytes)")
            else:
                struct_md_lines.append("- ⚠️ 生成失败")
                cif_path = None
        except Exception as e:
            struct_md_lines.append(f"⚠️ 结构生成失败:{e}")
            cif_path = None
        struct_md = "\n".join(struct_md_lines)

        # === 5) 加氢结构 ===
        try:
            rec_HM = recommended_H_to_M(formula, Cap if Cap else 1.5)
            hyd_md, hyd_cif_path = hydrogenation_section(
                formula, fill_fraction=1.0,
                predicted_capacity=(Cap if Cap else 1.5),
                H_to_M=rec_HM,
            )
        except Exception as e:
            hyd_md = f"⚠️ 加氢结构生成失败:{e}"
            hyd_cif_path = None
            rec_HM = 0.5

        # === 6) PhononBench stub ===
        try:
            phon = phonon_check_stub(formula)
            phon_md = (
                f"### 🔬 {formula} PhononBench 动力学稳定性\n\n"
                f"- 状态: **{phon['status']}**\n"
                f"- 原因: {phon['reason']}\n"
                f"- 后续: {phon['next']}\n"
                f"- 端点: [{phon['endpoint']}]"
                f"(http://{phon['endpoint'].replace('http://','')})\n"
            )
        except Exception as e:
            phon_md = f"⚠️ PhononBench 信息获取失败:{e}"

        # === 7) JSON 输出 ===
        try:
            P_json = res.get("P_298K")
            P_str = f"{float(P_json):.6e}" if (P_json is not None and np.isfinite(P_json)) else "null"
            Cap_str = f"{float(Cap):.6f}" if (Cap is not None and np.isfinite(Cap)) else "null"
            json_dump = (
                "```json\n"
                "{\n"
                f'  "formula":  "{formula}",\n'
                f'  "V5":       {float(V5):.6f},\n'
                f'  "V6":       {float(V6):.6f},\n'
                f'  "Capacity": {Cap_str},\n'
                f'  "P_298K_MPa":   {P_str},\n'
                f'  "rec_H_to_M": {float(rec_HM):.4f},\n'
                f'  "V0":       {float(V0):.1f}\n'
                "}\n```"
            )
        except Exception as e:
            json_dump = f"⚠️ JSON 序列化失败:{e}"

        _progress(1.0, "✅  完成")

        return (
            m_v5, m_v6, m_cap, m_p,          # 0~3 metric
            p1, p2, p3,                       # 4~6 plots
            struct_md, cif_path,              # 7~8 struct
            hyd_md, hyd_cif_path,             # 9~10 hydride
            phon_md, json_dump,               # 11~12 phon + json
            float(rec_HM),                    # 13 → inp_HM slider 跳到推荐值
            formula,                          # 14 → hidden_formula
            (float(Cap) if (Cap is not None and np.isfinite(Cap)) else None),  # 15
            [],                               # 16 → hidden_history
        )

    except Exception as e:
        # ===== 终极兜底:任何未捕获的异常都收敛成 err_tuple,绝不 re-raise =====
        print(f"[predict_full] 未捕获异常: {type(e).__name__}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return _err_tuple(f"⚠️ 预测流程异常(已捕获):{type(e).__name__}: {e}")
