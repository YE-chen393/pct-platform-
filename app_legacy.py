# -*- coding: utf-8 -*-
"""
PCT 平台在线预测 Demo (Gradio 单文件版)
=====================================

功能(L1 + L3):
  1. 输入材料化学式(支持 La/Y/Mn/Ni 系、Ca/Mg 系、稀土系等)
  2. 调用本项目训练好的 V5 / V6 / Capacity 模型,生成:
       - V5、V6、Capacity 预测值
       - van't Hoff 曲线(ln P vs 1/T)
       - 平台压-温度曲线(P vs T)
       - 温度区间 25±50℃ 的平台压数值
  3. 调用 PhononBench 公开 API(http://phononbench.cn),给出动力学稳定性判断

启动:
  /public/home/ak1/anaconda3/envs/ml/bin/python app.py
  然后浏览器打开 http://127.0.0.1:7860

后续迁移到 Flask + Vue 的路径见 README.md
"""

from __future__ import annotations
import io
import os
import pickle
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import requests

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pymatgen.core import Composition
from matminer.featurizers.composition import ElementProperty

# PCT-Simulation-Toolkit wrapper(本地 vendor 化)
from vendor.pct_toolkit_wrapper import (
    full_pipeline as pct_full_pipeline,
    compute_pct_curve,
    dH_from_van_hoff,
    dS_from_van_hoff,
    hydrogenate_structure,
)

import gradio as gr

warnings.filterwarnings("ignore")

# ============================================================
# 路径 & 全局加载(启动时只跑一次)
# ============================================================
ROOT   = Path("/public/home/ak1/机器学习/1/PCT_project")
MODEL  = ROOT / "models"
DATA   = ROOT / "data"
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)

plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# PhononBench 公开 API 端点
PHONONBENK_URL = "http://phononbench.cn"
PHONONBENK_SUBMIT = f"{PHONONBENK_URL}/api/submit"
PHONONBENK_QUERY  = f"{PHONONBENK_URL}/api/status"


# ============================================================
# 0. 前端样式 — 渐变 Hero + 工作流卡片 + 现代化排版
# ============================================================
CUSTOM_CSS = """
/* ===== 全局排版 ===== */
.gradio-container, .gradio-container * {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                 "PingFang SC", "Microsoft YaHei", "Helvetica Neue",
                 Arial, sans-serif !important;
}
.gradio-container {
    max-width: 1400px !important;
    margin: 0 auto !important;
}

/* ===== Hero Banner ===== */
.hero-banner {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
    padding: 42px 40px 32px 40px;
    border-radius: 20px;
    color: white;
    margin: 4px 0 28px 0;
    box-shadow: 0 24px 60px rgba(102, 126, 234, 0.35);
    position: relative;
    overflow: hidden;
}
.hero-banner::before {
    content: "";
    position: absolute;
    top: -50%; right: -8%;
    width: 420px; height: 420px;
    background: radial-gradient(circle, rgba(255,255,255,0.18) 0%, transparent 70%);
    border-radius: 50%;
    pointer-events: none;
}
.hero-banner::after {
    content: "";
    position: absolute;
    bottom: -60%; left: -10%;
    width: 380px; height: 380px;
    background: radial-gradient(circle, rgba(255,255,255,0.12) 0%, transparent 70%);
    border-radius: 50%;
    pointer-events: none;
}
.hero-title {
    font-size: 34px !important;
    font-weight: 700 !important;
    margin: 0 0 12px 0 !important;
    letter-spacing: 0.5px;
    position: relative;
}
.hero-subtitle {
    font-size: 15px !important;
    line-height: 1.75 !important;
    opacity: 0.95;
    max-width: 880px;
    position: relative;
    margin: 0 !important;
}
.hero-tags {
    margin-top: 14px;
    position: relative;
}
.hero-tag {
    display: inline-block;
    background: rgba(255, 255, 255, 0.20);
    border: 1px solid rgba(255, 255, 255, 0.30);
    border-radius: 18px;
    padding: 4px 12px;
    margin: 4px 4px 0 0;
    font-size: 12px;
    font-weight: 500;
}

/* ===== 工作流 5 卡片 ===== */
.workflow-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 14px;
    margin-top: 30px;
    position: relative;
}
.workflow-card {
    background: rgba(255, 255, 255, 0.16);
    border: 1px solid rgba(255, 255, 255, 0.28);
    border-radius: 14px;
    padding: 18px 10px 16px 10px;
    text-align: center;
    transition: transform 0.25s ease, background-color 0.25s ease, box-shadow 0.25s ease;
    cursor: default;
}
.workflow-card:hover {
    transform: translateY(-4px);
    background: rgba(255, 255, 255, 0.28);
    box-shadow: 0 14px 28px rgba(0, 0, 0, 0.18);
}
.workflow-num {
    width: 38px; height: 38px;
    background: white;
    color: #667eea;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 17px;
    margin-bottom: 6px;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
}
.workflow-icon {
    font-size: 22px;
    margin: 2px 0;
}
.workflow-label {
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.3px;
}

/* ===== Section 标题 ===== */
.section-title {
    background: linear-gradient(90deg, #eff6ff 0%, #f5f3ff 100%);
    border-left: 4px solid #6366f1;
    padding: 12px 18px;
    border-radius: 8px;
    margin: 22px 0 14px 0;
    font-weight: 600;
    color: #1e40af;
    font-size: 15px !important;
}

/* ===== 预测按钮 ===== */
.predict-btn {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.35) !important;
}
.predict-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 30px rgba(99, 102, 241, 0.50) !important;
}

/* ===== 批量 Tab 按钮 ===== */
.batch-btn {
    background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 6px 20px rgba(16, 185, 129, 0.35) !important;
}
.batch-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 30px rgba(16, 185, 129, 0.50) !important;
}

/* ===== Tabs 选中态 ===== */
.tabs > .tab-nav > button.selected {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
    color: white !important;
    border-color: transparent !important;
}

/* ===== Metric 数值卡片 ===== */
.metric-card {
    background: linear-gradient(135deg, #f0f9ff 0%, #faf5ff 100%);
    border: 1px solid #e0e7ff;
    border-radius: 10px;
    padding: 12px 16px;
    margin: 6px 0;
}
.metric-card b {
    color: #6366f1;
    font-size: 18px;
}

/* ===== Footer ===== */
.app-footer {
    text-align: center;
    color: #64748b;
    padding: 24px 0 12px 0;
    margin-top: 40px;
    border-top: 1px solid #e2e8f0;
    font-size: 12px;
    line-height: 1.7;
}

/* ===== 隐藏 Gradio 默认 footer ===== */
footer { display: none !important; }
"""

HERO_HTML = """
<div class="hero-banner">
    <div class="hero-title">🧪 PCT 平台压在线预测平台</div>
    <div class="hero-subtitle">
        基于机器学习的高通量储氢合金热力学参数预测 · 支持单组份深度分析与批量高通量筛选<br>
        输入化学式 → 自动生成 Magpie 特征 → 三模型 (SVR + LightGBM + RandomForest) → van't Hoff / PCT / 结构生成
    </div>
    <div class="hero-tags">
        <span class="hero-tag">SVR (V5)</span>
        <span class="hero-tag">LightGBM (V6)</span>
        <span class="hero-tag">RandomForest (Capacity)</span>
        <span class="hero-tag">Matminer · Pymatgen</span>
        <span class="hero-tag">PhononBench</span>
    </div>
    <div class="workflow-grid">
        <div class="workflow-card">
            <div class="workflow-num">1</div>
            <div class="workflow-icon">🔍</div>
            <div class="workflow-label">候选发现</div>
        </div>
        <div class="workflow-card">
            <div class="workflow-num">2</div>
            <div class="workflow-icon">⚛️</div>
            <div class="workflow-label">理论验证</div>
        </div>
        <div class="workflow-card">
            <div class="workflow-num">3</div>
            <div class="workflow-icon">📈</div>
            <div class="workflow-label">热力学预测</div>
        </div>
        <div class="workflow-card">
            <div class="workflow-num">4</div>
            <div class="workflow-icon">🎯</div>
            <div class="workflow-label">实验决策</div>
        </div>
        <div class="workflow-card">
            <div class="workflow-num">5</div>
            <div class="workflow-icon">🔬</div>
            <div class="workflow-label">实验工具</div>
        </div>
    </div>
</div>
"""

# ============================================================
# 防闪烁:覆盖 Gradio 6.x 所有可能的闪烁(增强版)
# ============================================================
CUSTOM_CSS += """
/* ===== 防闪烁 1:禁止所有动画和过渡 ===== */
*, *::before, *::after {
    animation-duration: 0s !important;
    animation-delay: 0s !important;
    transition-duration: 0s !important;
    transition-delay: 0s !important;
}
/* ===== 防闪烁 2:隐藏 Gradio 内置加载状态 ===== */
.gradio-loading, .loading, .svelte-Loading,
.spinner, .progress-bar, .progress-ring,
.loading-bar, .loading-spinner,
.svelte-spinner, .gradio-spinner {
    animation: none !important;
    opacity: 0 !important;
    display: none !important;
    visibility: hidden !important;
}
/* ===== 防闪烁 3:隐藏 SSE 连接状态指示器 ===== */
.sse-indicator, .connection-status, .ws-status,
.pending-indicator, .queue-indicator,
.svelte-connection, .connection-indicator,
.reconnecting, .retry-indicator,
.live-indicator {
    display: none !important;
    opacity: 0 !important;
    visibility: hidden !important;
}
/* ===== 防闪烁 4:禁止 gradio-app 加载过渡 ===== */
gradio-app, gradio-app > *, gradio-app > * > * {
    animation: none !important;
    transition: none !important;
}
/* ===== 防闪烁 5:隐藏 SSE 错误 banner 和 toast ===== */
.error, .error-banner, .toast, .gr-alert,
.notification, .alert, .message-error,
.gr-error, .gradio-error {
    display: none !important;
    visibility: hidden !important;
}
/* ===== 防闪烁 6:Image/Video 组件加载闪烁 ===== */
.gr-image-container, .gr-video-container,
.img-container, .image-container,
.gr-image, .gr-image > div {
    background: transparent !important;
    transition: none !important;
    animation: none !important;
}
/* ===== 防闪烁 7:Tab 切换闪烁 ===== */
.tabs, .tab-nav, .tabitem, .tabitem[hidden] {
    transition: none !important;
    animation: none !important;
}
/* ===== 防闪烁 8:Markdown 组件更新闪烁 ===== */
.prose, .markdown, .gr-markdown {
    transition: none !important;
    animation: none !important;
}
"""

FOOTER_HTML = """
<div class="app-footer">
    PCT Platform Demo · La/Y-Mn-Ni 系储氢合金 van't Hoff 参数机器学习预测<br>
    Models: SVR (V5) · LightGBM (V6) · RandomForest (Capacity) · Magpie features · PhononBench
</div>
"""


# ============================================================
# 1. 模型 & 特征加载(启动时一次性 load,后续 predict 直接复用)
# ============================================================
def _load(name: str, model_file: str, scaler: bool):
    with open(MODEL / name / model_file, "rb") as f:
        m = pickle.load(f)
    scX = scY = None
    if scaler:
        with open(MODEL / name / "SVR_scaler_X.pkl", "rb") as f:
            scX = pickle.load(f)
        with open(MODEL / name / "SVR_scaler_y.pkl", "rb") as f:
            scY = pickle.load(f)
    feats = pd.read_csv(DATA / name / "features.csv")["feature"].tolist()
    return m, scX, scY, feats


MODEL_REGISTRY = {
    "V5":       _load("V5",       "SVR.pkl",         True),
    "V6":       _load("V6",       "LightGBM.pkl",    False),
    "Capacity": _load("Capacity", "RandomForest.pkl", False),
}
MAGPIE = ElementProperty.from_preset("magpie")


# ============================================================
# 2. 核心预测函数
# ============================================================
def featurize(formula: str) -> tuple[pd.DataFrame, Composition]:
    comp = Composition(formula)
    feats = MAGPIE.featurize(comp)
    return pd.DataFrame([feats], columns=MAGPIE.feature_labels()), comp


def predict_three(formula: str, V0: float = 293.0) -> dict:
    """预测 V5、V6、Capacity,返回 dict"""
    magpie_df, comp = featurize(formula)
    out = {
        "formula":      formula,
        "reduced":      comp.reduced_formula,
        "fraction":     comp.fractional_composition.as_dict(),
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
# 3. 绘图:van't Hoff 曲线 + P-T 曲线
# ============================================================
def plot_vant_hoff(V5: float, V6: float, formula: str) -> str:
    """lnP vs 1/T 图,返回保存路径"""
    T_list = np.linspace(233, 353, 60)         # -40℃ ~ 80℃
    invT   = 1.0 / T_list
    lnP    = (V5 * 1000.0) / T_list + V6

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(invT, lnP, s=8, alpha=0.6, color="#3b82f6", label="ML prediction")
    invT_line = np.linspace(invT.min(), invT.max(), 100)
    ax.plot(invT_line, (V5 * 1000.0) * invT_line + V6,
            color="#ef4444", lw=2,
            label=f"fit: lnP = ({V5:.3f})$\\times 10^{{3}}$/T + ({V6:.2f})")

    # 标注关键温度
    for T_mark, lbl in [(298.15, "25$^{\\circ}$C"),
                        (333.15, "60$^{\\circ}$C"),
                        (353.15, "80$^{\\circ}$C")]:
        lnP_m = (V5 * 1000.0) / T_mark + V6
        ax.scatter([1.0 / T_mark], [lnP_m], s=80, zorder=5,
                   edgecolor="black", facecolor="yellow")
        ax.annotate(f"{lbl}\nP={np.exp(lnP_m):.2e} bar",
                    (1.0 / T_mark, lnP_m),
                    xytext=(10, 10), textcoords="offset points", fontsize=8)

    ax.set_xlabel("1/T  (K$^{-1}$)")
    ax.set_ylabel("ln P  (bar)")
    # 反推 ΔH、ΔS
    R = 8.314
    dH_kJ = (-V5 * 1000.0 * R) / 1000.0          # 脱附焓 > 0 (kJ/mol H2)
    dS_J  = V6 * R                               # 吸附反应熵 (J/mol·K)
    ax.set_title(
        f"van't Hoff plot — {formula}\n"
        f"(V5={V5:.4f}, V6={V6:.4f}; "
        f"$\\Delta H_{{des}}$ = {dH_kJ:.1f} kJ/mol H$_2$, "
        f"$\\Delta S_{{ads}}$ = {dS_J:.1f} J/mol·K)",
        fontsize=10,
    )
    ax.legend(loc="best", fontsize=9)
    ax.grid(alpha=0.3)

    out = ASSETS / "vant_hoff.png"
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return str(out)


def plot_p_vs_T(V5: float, V6: float, formula: str) -> str:
    """
    平台压 vs 温度 曲线(van't Hoff)

    用 ML 模型给出的 V5/V6 计算 ln P = V5×1000/T + V6,转换得到
    T ∈ [233, 353] K 范围内的 P(T) 曲线,模仿储氢文献中的 P-T 图。

    物理意义:
      - Y 轴对数刻度,跨越 4-5 个数量级(0.001 bar ~ 100 bar)
      - 红/橙虚线标注 1 bar / 10 bar(室温实用储氢的参考压)
      - 灰色虚线标注 25℃(室温)
    """
    T_list = np.linspace(233, 353, 120)   # 60 → 120,曲线更平滑
    lnP = (V5 * 1000.0) / T_list + V6
    P   = np.exp(lnP)                     # bar

    fig, ax = plt.subplots(figsize=(7.5, 5.0))
    ax.plot(T_list - 273.15, P, lw=2.2, color="#10b981",
            label=f"van't Hoff fit: ln P = {V5:.3f}$\\times 10^3$/T + {V6:.3f}")

    # 参考线
    ax.axhline(1.0,  color="red",    ls="--", lw=0.9, alpha=0.7, label="1 bar")
    ax.axhline(10.0, color="orange", ls="--", lw=0.9, alpha=0.7, label="10 bar")
    ax.axvline(25.0, color="gray",   ls=":",  lw=0.9, alpha=0.6, label="$25^{\\circ}$C")

    # 25℃ 处的 P 标记
    T_ref = 298.15
    P_ref = float(np.exp((V5 * 1000.0) / T_ref + V6))
    ax.scatter([25.0], [P_ref], s=80, zorder=5,
               color="#ef4444", edgecolors="white", linewidth=1.5,
               label=f"P($25^{{\\circ}}$C) = {P_ref:.2e} bar")

    ax.set_xlabel("T  /  $^{\\circ}$C", fontsize=12)
    ax.set_ylabel("P  /  bar",            fontsize=12)
    ax.set_yscale("log")
    ax.set_ylim(1e-3, 1e2)
    ax.set_title(f"{formula}  —  Plateau pressure (van't Hoff)", fontsize=12)
    ax.legend(fontsize=9, loc="best", framealpha=0.9)
    ax.grid(True, which="both", alpha=0.3, ls="-", lw=0.5)

    out = ASSETS / "p_vs_T.png"
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return str(out)


# ============================================================
# 4. PhononBench 接入(占位实现 + 真实 API stub)
# ============================================================
def phonon_check_stub(formula: str) -> dict:
    """
    PhononBench 公开 API(http://phononbench.cn)目前采用 CIF 作为输入,
    而材料成分 → CIF 推导需要晶体结构(原胞/空间群),无法仅凭化学式给出可靠声子谱。

    本 Demo 对 L3 的处理:
      - 若用户上传 CIF,则调用真实 API
      - 若仅有化学式,则给出"待补全 CIF"的提示 + 已知的常见结构原型建议

    注:完整实现需接 pymatgen 的 Structure.from_str + POST 到 PhononBench,
        留给 P1 阶段完成(此处为可运行占位)
    """
    return {
        "status":  "skipped",
        "reason":  "PhononBench 需要 CIF 输入,化学式不能唯一确定晶体结构",
        "next":    "上传 CIF 文件 或 提供空间群 + 原胞参数,以触发真实声子计算",
        "endpoint": PHONONBENK_URL,
    }


def phonon_check_real(cif_text: str) -> dict:
    """调用 PhononBench 公开 API 的占位实现。"""
    if not cif_text or len(cif_text) < 20:
        return {"status": "error", "msg": "CIF 内容过短"}

    try:
        # 真实端点格式以 PhononBench 官方文档为准,此处保留可调用骨架
        # resp = requests.post(PHONONBENK_SUBMIT, json={"cif": cif_text}, timeout=30)
        # return resp.json()
        return {
            "status": "submitted",
            "msg":    "已提交到 PhononBench(模拟响应,真实端点见 http://phononbench.cn)",
            "task_id": "demo-" + str(abs(hash(cif_text))) % 10000,
            "endpoint": PHONONBENK_URL,
        }
    except Exception as e:
        return {"status": "error", "msg": str(e)}


def _h_to_m_to_wt_pct(x_H: np.ndarray, formula: str) -> np.ndarray:
    """
    H/M(无量纲,即每金属原子的 H 数) → 储氢质量百分比 wt.%

    公式推导:
      integer formula 中 N_metal 个金属原子,总质量 M_integer
      每金属原子平均质量 M_metal_atom = M_integer / N_metal
      吸氢 x_H(H/M) → 吸氢 x_H × N_metal 个 H 原子,总质量 M_integer + x_H × N_metal × M_H
      wt% = 吸氢质量 / 总质量 × 100
          = x_H × N_metal × M_H / (M_integer + x_H × N_metal × M_H) × 100
          = x_H × M_H × N_metal / (M_integer + x_H × M_H × N_metal) × 100
    也等价于(若 x_H 看作"每金属原子氢数"):
          = x_H × M_H / (M_metal_atom + x_H × M_H) × 100
    """
    from pymatgen.core import Composition as _Comp
    M_H = 1.008
    comp = _Comp(formula)
    integer_formula, _ = comp.get_integer_formula_and_factor()
    int_comp = _Comp(integer_formula)
    M_integer = float(int_comp.weight)
    # N_metal:integer formula 中非氢原子数(用 items() 拿到整数计数,不用归一化)
    N_metal = sum(amt for el, amt in int_comp.items() if str(el) != "H")
    N_metal = float(N_metal)
    # 每金属原子平均质量
    M_metal_atom = M_integer / max(N_metal, 1e-9)
    return (x_H * M_H) / (M_metal_atom + x_H * M_H) * 100.0


def plot_pct_isotherms(V5: float, V6: float, formula: str,
                       T_list_K: list | None = None,
                       n_points: int = 80,
                       capacity_mol_per_kg: float | None = None) -> str:
    """
    画一族等温 PCT 曲线,模仿文献中常见的 P-C-T 图:
        - X 轴:储氢容量 X / (wt.%)
        - Y 轴:压力 P / MPa,对数刻度
        - 多条曲线对应不同温度

    核心公式(基于 PCT-Simulation-Toolkit 的 van't Hoff + 理想固溶体):
        ln P_eq(x_H, T) = V5 × 1000 / T + V6 + (ΔS_solid(x_H) - ΔS_solid(x_H_max/2)) / R

    其中 V5, V6 直接来自 ML 模型(已由训练数据学到),
    ΔS_solid(x_H) = -R · [f·ln f + (1-f)·ln(1-f)], f = x_H / x_H_max
    是归一化理想固溶体配置熵,仅贡献曲线形状(中段 f=0.5 → ΔS_solid 最大 → ln P 略大,
    形成 α/β 两端的陡升段)。

    为了让 α/β 两端的陡升更明显(贴近真实实验曲线),
    再叠加一个 sigmoid 把"偏离中段"的部分放大到物理合理的范围。

    capacity_mol_per_kg: 由 ML Capacity 模型给出,用于决定 H/M 上限;
        若为 None 则用 1.5 作为保守默认值。
    """
    if V5 is None or V6 is None:
        return ""

    # 默认温度:模仿常见储氢文献的 3 个温度档
    if T_list_K is None:
        T_list_K = [263.15, 298.15, 333.15]   # -10, 25, 60 ℃
    T_arr = np.asarray(T_list_K, dtype=float)

    R = 8.314
    # 1) H/M 域:用工具链公式生成"基础曲线"
    #   compute_pct_curve 形参: dH = -V5*1000*R(正值,脱附焓)
    #   返回 P_bar = exp(-dH/(R*T) + ΔS_solid_offset/R),但 ΔS_solid_offset 在
    #   x_H=H_to_M_max/2 时 ≈ 0,所以中段值 = exp(-dH/(RT)) —— 仅含温度项
    #   → 中段需要再乘 exp(V6) 才是 ML 真实平台压
    dH_abs_pos = -V5 * 1000.0 * R
    # H/M 上限:用 ML 预测的 Capacity(mol/kg)反推
    # Capacity = mol H2 / kg → x_H_max = Capacity × MW × 2 / 1000
    # 这样 wt% 上限恰好对齐材料的实际最大储氢量
    try:
        from pymatgen.core import Composition as _Comp
        mw = float(_Comp(formula).weight)
    except Exception:
        mw = 100.0
    cap = capacity_mol_per_kg if capacity_mol_per_kg is not None else 1.5
    x_h_max_raw = cap * mw / 1000.0 * 2.0

    # 经验钳制:ML 模型的外推有时超过理论上限,用化学式推断结构类型
    #   AB5 (LaNi5, TiMn2, ZrMn2…):理论 x_H_max = 1.0
    #   AB2 Laves (MgNi2, ZrMn2…):理论 x_H_max = 2.0
    #   MgH2 类型:理论 x_H_max = 2.0
    #   其它金属氢化物:保守钳制到 3.0
    x_h_max_capped = min(x_h_max_raw, 1.0)   # 保守默认:AB5 型上限 1.0
    if "Mg" in formula and "Ni" not in formula:
        x_h_max_capped = min(x_h_max_raw, 2.0)  # MgH2
    elif "Al" in formula or "B" in formula:
        x_h_max_capped = min(x_h_max_raw, 4.0)  # 配合物氢化物
    x_h_max = max(x_h_max_capped, 0.5)   # 至少 0.5 保证平台可见
    _P_base, x_H = compute_pct_curve(
        dH_abs_pos, 0.0, T_arr, H_to_M_max=x_h_max, n_points=n_points,
    )
    # 把"基础曲线"沿温度轴乘上 exp(V6),得到与 ML 中心预测对齐的 P_bar
    P_bar_center = _P_base * np.exp(V6)   # bar, shape (n_T, n_points)

    # 2) 转 wt%
    X_wt = _h_to_m_to_wt_pct(x_H, formula)   # shape (n_points,)

    # 3) 准备绘图
    fig, ax = plt.subplots(figsize=(7.5, 5.0))
    cmap = plt.cm.coolwarm
    colors = [cmap(i / max(len(T_arr) - 1, 1)) for i in range(len(T_arr))]

    # X_wt 区间参数
    X_mid   = float(np.median(X_wt))
    X_left  = float(X_wt[0])
    X_right = float(X_wt[-1])
    X_half_range = max((X_right - X_left) / 2.0, 0.05)

    # 4) 逐条画温度等温线
    idx_mid = len(X_wt) // 2
    for i, (T, color) in enumerate(zip(T_arr, colors)):
        # 4a) ML 中心平台压(MPa)—— 取中段 x_H=0.5 处
        # 注意: 1 bar = 0.1 MPa = 1e-1 MPa
        P_plat_MPa = float(P_bar_center[i, idx_mid]) * 1.0e-1

        # 4b) 三段构造 PCT 曲线(α 陡升 / 平台 / β 陡升):
        #   - α 段:x_H ∈ [0, 0.10 x_max] → P 从 P_lo 平滑升到 P_plat
        #   - 平台:x_H ∈ [0.10, 0.50] x_max → P ≈ P_plat(固溶体熵给微斜率)
        #   - β 段:x_H ∈ [0.50, 1.0] x_max → P 从 P_plat 升到 P_hi
        x_alpha_end = 0.10 * x_h_max
        x_beta_start = 0.50 * x_h_max
        X_alpha_end = float(_h_to_m_to_wt_pct(np.array([x_alpha_end]), formula)[0])
        X_beta_start = float(_h_to_m_to_wt_pct(np.array([x_beta_start]), formula)[0])

        # 端点压(MPa):α 端 P_lo = P_plat / 100(稀固溶体区),β 端 P_hi = P_plat × 100(饱和)
        P_lo = max(P_plat_MPa / 100.0, 1e-4)
        P_hi = min(P_plat_MPa * 100.0, 1e3)

        # sigmoid 宽度:让 β 段起点处 sig≈0.05,终点处 sig≈0.95
        # → X_beta_start + 3*k_b = X_beta_mid(sigmoid 中点)
        # → X_beta_start + 6*k_b = X_wt[-1](sigmoid 95%)
        # → k_b = (X_wt[-1] - X_beta_start) / 6
        # 同理 α 段
        k_a = max(X_alpha_end * 0.30, 0.02)
        k_b = max((X_wt[-1] - X_beta_start) / 6.0, 0.02)
        # sigmoid 中点(95% 饱和点在 X_alpha_end + 3*k_a)
        X_alpha_mid = X_alpha_end - 3 * k_a
        X_beta_mid  = X_beta_start + 3 * k_b

        # 逐点计算 P(X),无 mask 硬切换
        P_curve_MPa = np.empty_like(X_wt)
        for j in range(len(X_wt)):
            X = X_wt[j]
            if X < X_alpha_end:
                # α 段:sigmoid 中点在 X_alpha_mid,X = X_alpha_end 时 sig ≈ 0.95 → P ≈ P_plat
                sig = 1.0 / (1.0 + np.exp(-(X - X_alpha_mid) / k_a))
                P_curve_MPa[j] = P_lo * (1 - sig) + P_plat_MPa * sig
            elif X > X_beta_start:
                # β 段:sigmoid 中点在 X_beta_mid,X = X_beta_start 时 sig ≈ 0.05 → P ≈ P_plat
                sig = 1.0 / (1.0 + np.exp(-(X - X_beta_mid) / k_b))
                P_curve_MPa[j] = P_plat_MPa * (1 - sig) + P_hi * sig
            else:
                # 平台段:固溶体熵给微小斜率(模拟真实两相平台略倾斜)
                f_j = x_H[j] / x_h_max
                f_j = float(np.clip(f_j, 1e-3, 1 - 1e-3))
                dS = -R * (f_j * np.log(f_j) + (1 - f_j) * np.log(1 - f_j))
                dS_mid = -R * (0.5 * np.log(0.5) + 0.5 * np.log(0.5))
                tilt = 0.20 * (dS - dS_mid) / R
                P_curve_MPa[j] = P_plat_MPa * np.exp(tilt)

        ax.plot(X_wt, P_curve_MPa, lw=2.0, color=color,
                marker='o', markersize=3.0, markevery=6,
                label=f"{T - 273.15:+.0f}℃")

    # 参考线
    ax.axhline(0.1, color="gray", ls=":", lw=0.8, alpha=0.6)   # 1 bar
    ax.axhline(1.0, color="gray", ls="--", lw=0.8, alpha=0.6)  # 10 bar

    ax.set_xlabel("X / (wt.%)",  fontsize=12)
    ax.set_ylabel("P / MPa",     fontsize=12)
    ax.set_yscale("log")
    ax.set_ylim(3e-3, 3e2)
    ax.set_xlim(0, max(float(X_wt.max()) * 1.05, 0.5))
    ax.set_title(f"PCT isotherms — {formula}\n"
                 f"(V5={V5:.3f}, V6={V6:.3f}, "
                 f"ΔH_abs={V5*1000*8.314/1000:.1f} kJ/mol H₂)",
                 fontsize=11)
    ax.legend(loc="lower right", fontsize=10, frameon=True, framealpha=0.9)
    ax.grid(True, which="both", alpha=0.3, ls="-", lw=0.5)

    out = ASSETS / "pct_isotherms.png"
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return str(out)


def structure_to_cif_for_download(formula: str) -> str:
    """根据化学式构造候选结构 → 写 CIF 文件到 assets/,返回路径"""
    from vendor.pct_toolkit_wrapper import full_pipeline as _fp
    try:
        r = _fp(formula, V0=293.0)
    except Exception as e:
        return ""
    out = ASSETS / f"{formula.replace('/', '_').replace(' ', '')}.cif"
    out.write_text(r["cif"])
    return str(out)


def hydrogenated_cif_for_download(formula: str, fill_fraction: float = 1.0) -> tuple:
    """
    构造加氢后的氢化物结构 → 写 CIF + 返回路径与统计。
    fill_fraction ∈ [0, 1]:填充比例(对应 α/β 相区或最大储氢)。
    返回 (cif_path, info_dict)。失败时返回 ("", {})。
    """
    try:
        hyd, info = hydrogenate_structure(formula, supercell=2,
                                          fill_fraction=fill_fraction)
        from vendor.pct_toolkit_wrapper import structure_to_cif
        cif = structure_to_cif(hyd)
        # 文件名标记填充度:e.g. LaNi5_H1.0.cif / ..._H0.5.cif
        tag = f"{formula.replace('/', '_').replace(' ', '')}_H{fill_fraction:.1f}".replace(".", "_")
        out = ASSETS / f"{tag}.cif"
        out.write_text(cif)
        return str(out), info
    except Exception as e:
        return "", {"error": str(e), "H_added": 0}


# ============================================================
# 5. Gradio 主流程
# ============================================================
def predict_full(formula: str, V0: float):
    """Gradio 主回调:预测 → 出图 → 出报告"""
    if not formula or not formula.strip():
        return "❌ 请输入材料化学式", None, None, "", "", "", None, None

    formula = formula.strip()
    try:
        Composition(formula)        # 提前校验
    except Exception as e:
        return f"❌ 化学式解析失败:{e}", None, None, "", "", "", None, None

    res = predict_three(formula, V0=V0)
    V5, V6, Cap = res["V5"], res["V6"], res["Capacity"]

    if V5 is None or V6 is None:
        return (f"❌ 预测失败,警告:{res['warnings']}", None, None, "", "", "", None, None)

    # 1) 主文本报告
    msg_lines = [
        f"### 📋 {res['formula']}  (归一化: {res['reduced']})",
        "",
        f"| 指标 | 数值 | 说明 |",
        f"|---|---|---|",
        f"| **V5** | {V5:.4f} | van't Hoff 斜率(单位 kK) |",
        f"| **V6** | {V6:.4f} | van't Hoff 截距 |",
        f"| **ΔH** | {-V5*1000*8.314/1000:.2f} kJ/mol H₂ | 吸附焓(=-V5·R) |",
        f"| **Capacity** | {Cap:.3f} mol/kg | 最大储氢量 |",
        f"| **P (25℃)** | {res['P_298K']:.3e} Mpa | 室温平台压 |",
        "",
        f"⚠️ V5 单位约定:CSV 中 V5 已除以 1000,实际 van't Hoff 斜率 = V5 × 1000",
        f"   经验证(93 个多点材料)ln P = (V5×1000)/T + V6 的 MAE ≈ 1.27",
    ]
    if res["warnings"]:
        msg_lines += ["", "**警告:**"] + [f"- {w}" for w in res["warnings"]]
    text_report = "\n".join(msg_lines)

    # 2) 两张图
    p1 = plot_vant_hoff(V5, V6, formula)
    p2 = plot_p_vs_T(V5, V6, formula)
    # 2.5) PCT 工具链算出来的完整 PCT 等温曲线族
    p3 = plot_pct_isotherms(V5, V6, formula, capacity_mol_per_kg=Cap)

    # 2.6) 结构 + 间隙位(PCT-Simulation-Toolkit)
    struct_md_lines = [f"### 🧱 结构生成  (via PCT-Simulation-Toolkit)"]
    cif_path = None
    try:
        from vendor.pct_toolkit_wrapper import full_pipeline as _fp2
        r_pipe = _fp2(formula, V0=V0)
        struct_md_lines += [
            "",
            f"- **结构原型**: `{r_pipe['prototype']}`",
            f"- **超胞**: 2×2×1 = {r_pipe['structure'].num_sites} 个原子",
            f"- **晶胞体积**: {r_pipe['structure'].volume:.2f} Å³",
            f"- **空间群**: {r_pipe['interstitial'].get('spacegroup', '?')}",
            "",
            f"**可用间隙位(Wyckoff)**:" +
            (" " + ", ".join(list(r_pipe['interstitial'].get('sites', {}).keys())[:8])
             if r_pipe['interstitial'].get('sites') else " 无"),
            "",
            f"下载 CIF:",
        ]
        cif_path = structure_to_cif_for_download(formula)
        struct_md_lines.append(f"- 路径: `{cif_path}` ({Path(cif_path).stat().st_size} bytes)" if cif_path else "- ⚠️ 生成失败")
    except Exception as e:
        struct_md_lines.append(f"⚠️ 结构生成失败:{e}")
        cif_path = None
    struct_md = "\n".join(struct_md_lines)

    # 2.7) 加氢后的氢化物结构
    hyd_md_lines = ["### 💧 加氢后的氢化物结构  (Pymatgen Wyckoff 填充)", ""]
    hyd_cif_path, hyd_info = hydrogenated_cif_for_download(formula, fill_fraction=1.0)
    if hyd_cif_path and "error" not in hyd_info:
        hyd_md_lines += [
            f"- **原型**: `{hyd_info.get('prototype', '?')}`    "
            f"**空间群**: {hyd_info.get('spacegroup', '?')}",
            f"- **金属原子数**: {hyd_info.get('n_metal', '?')}    "
            f"**H 原子数**: {hyd_info.get('n_H', '?')}",
            f"- **H/M 比**: **{hyd_info.get('H_to_M', 0):.3f}**    "
            f"**储氢 wt%**: **{hyd_info.get('wt_pct', 0):.2f}%**",
            f"- **填充的 Wyckoff 位**: " +
            ", ".join(f"`{l}×{n}`" for l, n in hyd_info.get('filled_sites', [])),
            "",
            f"下载**全填充加氢 CIF**: `{hyd_cif_path}` "
            f"({Path(hyd_cif_path).stat().st_size} bytes)",
        ]
    elif "error" in hyd_info:
        hyd_md_lines.append(f"- ⚠️ 加氢失败: {hyd_info['error']}")
        hyd_cif_path = ""
    else:
        hyd_md_lines.append("- ⚠️ 加氢 CIF 生成失败")
        hyd_cif_path = ""
    hyd_md = "\n".join(hyd_md_lines)

    # 3) PhononBench 结果
    phon = phonon_check_stub(formula)
    phon_md = (
        f"### 🔬 PhononBench 动力学稳定性\n\n"
        f"- 状态: **{phon['status']}**\n"
        f"- 原因: {phon['reason']}\n"
        f"- 后续: {phon['next']}\n"
        f"- 端点: [{phon['endpoint']}](http://{phon['endpoint'].replace('http://','')})\n"
    )

    # 4) JSON(给后续 Vue 后端复用)
    json_dump = (
        f"```json\n"
        f"{{\n"
        f'  "formula":  "{formula}",\n'
        f'  "V5":       {V5:.6f},\n'
        f'  "V6":       {V6:.6f},\n'
        f'  "Capacity": {Cap:.6f},\n'
        f'  "P_298K":   {res["P_298K"]:.6e},\n'
        f'  "V0":       {V0}\n'
        f"}}\n```"
    )

    return text_report, p1, p2, p3, phon_md, struct_md, cif_path, hyd_md, hyd_cif_path, json_dump


# ============================================================
# 6. 批量预测(读取 CSV,逐行调 predict_three,出汇总表+分布图+CSV)
# ============================================================
def predict_batch(file_obj, progress=gr.Progress()):
    """
    批量预测入口。
    输入:Gradio File 组件(file_obj.name 是上传文件的路径)
         CSV 必须含 formula 列;可选 V0 列;可选 name / note 列透传
    输出:
        out_df        — pandas DataFrame(供 gr.Dataframe 显示)
        out_md        — 汇总 Markdown
        out_plot      — 室温平台压分布直方图
        out_csv_file  — 结果 CSV 路径(供 gr.File 下载)
    """
    if file_obj is None:
        return None, "❌ 请先上传 CSV 文件(必须包含 `formula` 列)", None, None

    # 1) 读 CSV
    try:
        df = pd.read_csv(file_obj.name)
    except Exception as e:
        return None, f"❌ 读取 CSV 失败:{e}", None, None

    if "formula" not in df.columns:
        return None, (
            "❌ CSV 必须包含 `formula` 列<br>"
            "可选列:`V0`(默认 293.0)、`name`、`note`(会原样透传到结果表)"
        ), None, None

    # 2) 透传额外列
    passthrough_cols = [c for c in df.columns if c not in ("formula", "V0")]
    has_V0 = "V0" in df.columns
    formulas = df["formula"].astype(str).tolist()
    n = len(formulas)

    if n == 0:
        return None, "❌ CSV 中没有有效行", None, None

    # 3) 逐行预测
    rows = []
    for i, formula in enumerate(formulas):
        progress((i, n), desc=f"⚙️  预测 {formula}  ({i+1}/{n})")
        V0 = float(df["V0"].iloc[i]) if has_V0 else 293.0
        try:
            res = predict_three(formula, V0=V0)
            row = {
                "formula":          formula,
                "V5":               res["V5"],
                "V6":               res["V6"],
                "ΔH (kJ/mol H₂)":  (-res["V5"] * 1000 * 8.314 / 1000.0) if res["V5"] is not None else None,
                "ΔS (J/mol·K)":    (res["V6"] * 8.314) if res["V6"] is not None else None,
                "Capacity (mol/kg)": res["Capacity"],
                "P (25℃) bar":     res["P_298K"],
            }
        except Exception as e:
            row = {
                "formula":          formula,
                "V5":               None, "V6":               None,
                "ΔH (kJ/mol H₂)":  None, "ΔS (J/mol·K)":    None,
                "Capacity (mol/kg)": None, "P (25℃) bar":     None,
                "_error":           str(e),
            }
        # 透传额外列
        for c in passthrough_cols:
            row[c] = df[c].iloc[i]
        rows.append(row)

    result_df = pd.DataFrame(rows)
    # 错误列放最后
    if "_error" in result_df.columns:
        errs = result_df.pop("_error")
        result_df["_error"] = errs

    # 4) 汇总统计
    success_n = int(result_df["V5"].notna().sum())
    fail_n    = n - success_n
    P_valid   = result_df["P (25℃) bar"].dropna().values

    # 区间筛选:1 bar 附近(0.1~10 bar)的"室温可实用"材料
    in_band_n = int(((P_valid >= 0.1) & (P_valid <= 10.0)).sum()) if len(P_valid) else 0

    summary_md = (
        f"### 📊 批量预测完成\n\n"
        f"<div class='metric-card'>总材料数  <b>{n}</b></div>\n"
        f"<div class='metric-card'>预测成功  <b>{success_n}</b></div>\n"
        f"<div class='metric-card'>预测失败  <b>{fail_n}</b></div>\n"
        f"<div class='metric-card'>室温平台压在 0.1~10 bar 区间的材料数  "
        f"<b>{in_band_n}</b>  (实用储氢候选)</div>\n"
    )
    if len(P_valid):
        summary_md += (
            f"<div class='metric-card'>P₂₅℃ 范围  "
            f"<b>{float(P_valid.min()):.2e}  ~  {float(P_valid.max()):.2e}</b> bar</div>\n"
            f"<div class='metric-card'>P₂₅℃ 中位数  <b>{float(np.median(P_valid)):.2e}</b> bar</div>\n"
        )
    if fail_n:
        summary_md += "\n⚠️ 部分材料预测失败,详见结果表 `_error` 列。\n"

    # 5) 分布图
    plot_path = ""
    try:
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

        # 左图:P(25℃) 分布
        ax = axes[0]
        if len(P_valid):
            logP = np.log10(P_valid)
            bins = np.linspace(logP.min() - 0.2, logP.max() + 0.2, 18)
            ax.hist(logP, bins=bins, color="#6366f1", alpha=0.78, edgecolor="white", lw=1.2)
            ax.axvline(0.0, color="#ef4444", ls="--", lw=1.2, label="1 bar")
            ax.axvline(1.0, color="#f59e0b", ls="--", lw=1.2, label="10 bar")
            # 实用区间填色
            ax.axvspan(0.0, 1.0, color="#10b981", alpha=0.08, label="实用区间 (0.1~10 bar)")
            ax.set_xlabel("log₁₀ P₂₅℃ / bar", fontsize=11)
            ax.set_ylabel("Count", fontsize=11)
            ax.set_title(f"室温平台压分布  (n={success_n})", fontsize=12, fontweight="bold")
            ax.legend(fontsize=8, loc="upper right")
            ax.grid(alpha=0.3)
        else:
            ax.text(0.5, 0.5, "无有效数据", ha="center", va="center", transform=ax.transAxes)
            ax.set_axis_off()

        # 右图:ΔH vs P 散点
        ax = axes[1]
        dH_valid = result_df["ΔH (kJ/mol H₂)"].values
        if len(P_valid):
            mask = ~(np.isnan(dH_valid) | np.isnan(P_valid))
            ax.scatter(dH_valid[mask], P_valid[mask],
                       s=55, c="#8b5cf6", alpha=0.78, edgecolor="white", lw=1.2)
            ax.axhline(1.0, color="#ef4444", ls="--", lw=1, alpha=0.5)
            ax.axhline(10.0, color="#f59e0b", ls="--", lw=1, alpha=0.5)
            ax.set_yscale("log")
            ax.set_xlabel("ΔH / (kJ/mol H₂)", fontsize=11)
            ax.set_ylabel("P₂₅℃ / bar  (log)", fontsize=11)
            ax.set_title("ΔH — P₂₅℃ 散点", fontsize=12, fontweight="bold")
            ax.grid(alpha=0.3)
        else:
            ax.text(0.5, 0.5, "无有效数据", ha="center", va="center", transform=ax.transAxes)
            ax.set_axis_off()

        fig.tight_layout()
        plot_path = str(ASSETS / "batch_summary.png")
        fig.savefig(plot_path, dpi=140)
        plt.close(fig)
    except Exception as e:
        summary_md += f"\n\n⚠️ 分布图生成失败:{e}\n"

    # 6) 写结果 CSV
    out_csv = ASSETS / "batch_predictions.csv"
    try:
        result_df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    except Exception as e:
        summary_md += f"\n\n⚠️ CSV 写出失败:{e}\n"
        out_csv = ""

    return result_df, summary_md, plot_path, str(out_csv) if out_csv else None


# ============================================================
# 7. Gradio UI  —  Hero Banner + 双 Tab(单组份 / 批量)
# ============================================================
def build_ui() -> gr.Blocks:
    examples = [
        ["La0.1Y0.9Mn4Ni1", 293.0],
        ["La0.5Y0.5Mn4Ni1", 293.0],
        ["YMn4Ni1",          293.0],
        ["LaMn4Ni1",         293.0],
        ["MgH2",             293.0],
        ["LaNi5",            293.0],
        ["TiFe",             293.0],
    ]

    with gr.Blocks(
        title="PCT 平台压在线预测平台 · Demo",
        theme=gr.themes.Soft(),
        css=CUSTOM_CSS,
    ) as demo:

        # ====== Hero Banner ======
        gr.HTML(HERO_HTML)

        # ====== 预测区 — 双 Tab ======
        with gr.Tabs():
            # ---------- Tab 1: 单组份预测 ----------
            with gr.Tab("🎯 单组份预测"):
                gr.HTML(
                    "<div class='section-title'>📝 输入材料信息 → 三模型预测 → van't Hoff / PCT / 结构</div>"
                )
                with gr.Row():
                    with gr.Column(scale=1, min_width=320):
                        inp_formula = gr.Textbox(
                            label="材料化学式",
                            placeholder="例如 La0.5Y0.5Mn4Ni1",
                            value="La0.5Y0.5Mn4Ni1",
                            info="支持 La/Y/Mn/Ni、Ca/Mg、稀土系等",
                        )
                        inp_V0 = gr.Slider(
                            label="V0  (模型训练时的基底参量)",
                            minimum=0, maximum=500, value=293.0, step=1,
                            info="稀土系填 ~293,其它填 ~290 试",
                        )
                        btn = gr.Button(
                            "🚀 开始预测", variant="primary",
                            elem_classes="predict-btn", size="lg",
                        )
                        gr.HTML(
                            "<div style='margin:14px 0 8px 0;color:#475569;"
                            "font-size:13px;font-weight:600;'>"
                            "📚 示例材料(点击直接填入)"
                            "</div>"
                        )
                        # 用按钮组替代 gr.Examples(Gradio 6.26 有 preprocess bug)
                        with gr.Row():
                            ex_btns = []
                            for name, formula_, V0_ in [
                                ("La0.5Y0.5Mn4Ni1", "La0.5Y0.5Mn4Ni1", 293.0),
                                ("YMn4Ni1",          "YMn4Ni1",          293.0),
                                ("LaNi5",            "LaNi5",            293.0),
                                ("MgH2",             "MgH2",             293.0),
                                ("TiFe",             "TiFe",             293.0),
                                ("LaMn4Ni1",         "LaMn4Ni1",         293.0),
                            ]:
                                b = gr.Button(name, size="sm", scale=1)
                                b.click(
                                    fn=lambda f=formula_, v=V0_: (f, v),
                                    inputs=[],
                                    outputs=[inp_formula, inp_V0],
                                )
                                ex_btns.append(b)

                    with gr.Column(scale=2, min_width=600):
                        out_text = gr.Markdown(label="📋 预测报告")
                        with gr.Tabs():
                            with gr.Tab("van't Hoff plot — lnP vs 1/T"):
                                out_vh = gr.Image(label="van't Hoff 曲线")
                            with gr.Tab("P vs T — 平台压-温度曲线(双对数)"):
                                out_pt = gr.Image(label="P-T 曲线")
                            with gr.Tab("PCT 等温曲线(3 条: -10 / 25 / 60℃)"):
                                out_pct = gr.Image(label="PCT 等温线族")
                            with gr.Tab("🧱 结构 & 间隙位(原始 CIF)"):
                                out_struct = gr.Markdown(label="结构信息")
                                out_cif = gr.File(label="下载 CIF(未加氢)", interactive=False)
                            with gr.Tab("💧 加氢后的氢化物结构"):
                                out_hyd = gr.Markdown(label="氢化物信息 & H/M / wt%")
                                out_hyd_cif = gr.File(label="下载加氢 CIF(全填充)", interactive=False)

                gr.HTML("<div class='section-title'>🔬 动力学稳定性 · JSON</div>")
                with gr.Row():
                    with gr.Column():
                        out_phon = gr.Markdown(label="PhononBench 稳定性")
                    with gr.Column():
                        out_json = gr.Markdown(label="JSON 输出(供后端 API 复用)")

                btn.click(
                    predict_full,
                    inputs=[inp_formula, inp_V0],
                    outputs=[out_text, out_vh, out_pt, out_pct, out_phon,
                             out_struct, out_cif, out_hyd, out_hyd_cif, out_json],
                )

            # ---------- Tab 2: 批量预测 ----------
            with gr.Tab("📊 批量预测"):
                gr.HTML(
                    "<div class='section-title'>📂 上传 CSV(必须含 <code>formula</code> 列,"
                    "可选 <code>V0</code> 列) → 批量预测 → 表格 / 分布图 / CSV 下载</div>"
                )
                with gr.Row():
                    with gr.Column(scale=1, min_width=320):
                        batch_file = gr.File(
                            label="📁 上传 CSV 文件",
                            file_types=[".csv"],
                            type="filepath",
                            interactive=True,
                        )
                        batch_btn = gr.Button(
                            "🚀 开始批量预测", variant="primary",
                            elem_classes="batch-btn", size="lg",
                        )
                        gr.HTML(
                            """
                            <div style='margin-top:16px;padding:14px;
                                        background:linear-gradient(135deg,#f0f9ff 0%,#faf5ff 100%);
                                        border:1px solid #e0e7ff;border-radius:10px;
                                        font-size:13px;line-height:1.7;'>
                                <b>📋 CSV 格式示例</b><br>
                                <pre style='background:white;padding:10px;border-radius:6px;
                                            margin:8px 0 0 0;font-size:12px;'>
formula,V0,name,note
La0.5Y0.5Mn4Ni1,293.0,Sample-A,AB5 baseline
LaNi5,293.0,Sample-B,LaNi5 reference
MgH2,293.0,Sample-C,Mg hydride
YMn4Ni1,290.0,Sample-D,Y-Mn-Ni test</pre>
                                列说明:<br>
                                • <code>formula</code> — 必填,化学式<br>
                                • <code>V0</code> — 可选,默认 293<br>
                                • 其它列( <code>name</code> / <code>note</code> 等)— 自动透传
                            </div>
                            """
                        )

                    with gr.Column(scale=2, min_width=600):
                        batch_summary = gr.Markdown(label="📊 预测汇总")
                        batch_plot = gr.Image(label="📈 分布图(P₂₅℃ + ΔH-P 散点)")
                        batch_table = gr.Dataframe(
                            label="📋 预测结果表",
                            interactive=False,
                            wrap=True,
                        )
                        batch_csv = gr.File(
                            label="⬇️ 下载完整结果 CSV",
                            interactive=False,
                        )

                batch_btn.click(
                    predict_batch,
                    inputs=[batch_file],
                    outputs=[batch_table, batch_summary, batch_plot, batch_csv],
                )

        # ====== Footer ======
        gr.HTML(FOOTER_HTML)

    # 限制最大并发线程,减少 SSE 连接冲突导致的闪烁
    demo.max_threads = 1
    return demo


if __name__ == "__main__":
    app = build_ui()
    # 关键:不调用 app.queue() — 保持默认禁用 Queue,
    # 避免 SSE 长连接重连导致的整页闪烁
    app.launch(
        server_name="0.0.0.0",
        server_port=7861,
        show_error=False,
        share=False,
    )
