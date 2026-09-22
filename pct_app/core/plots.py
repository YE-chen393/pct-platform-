"""绘图函数:van't Hoff / P-T / PCT 等温线族。"""

from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt

from ..config.paths import ASSETS_DIR
from ..config.constants import PLOT_DPI, ISOTHERM_T_LIST_K
from .thermodynamics import h_to_m_to_wt_pct


def plot_vant_hoff(V5: float, V6: float, formula: str) -> str:
    """lnP vs 1/T 图,返回保存路径。"""
    T_list = np.linspace(233, 353, 60)
    invT = 1.0 / T_list
    lnP = (V5 * 1000.0) / T_list + V6

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(invT, lnP, s=8, alpha=0.6, color="#3b82f6", label="ML prediction")
    invT_line = np.linspace(invT.min(), invT.max(), 100)
    ax.plot(invT_line, (V5 * 1000.0) * invT_line + V6,
            color="#ef4444", lw=2,
            label=f"fit: lnP = ({V5:.3f})$\\times 10^{{3}}$/T + ({V6:.2f})")

    for T_mark, lbl in [(298.15, "25$^{\\circ}$C"),
                        (333.15, "60$^{\\circ}$C"),
                        (353.15, "80$^{\\circ}$C")]:
        lnP_m = (V5 * 1000.0) / T_mark + V6
        ax.scatter([1.0 / T_mark], [lnP_m], s=80, zorder=5,
                   edgecolor="black", facecolor="yellow")
        ax.annotate(f"{lbl}\nP={np.exp(lnP_m):.2e} MPa",
                    (1.0 / T_mark, lnP_m),
                    xytext=(10, 10), textcoords="offset points", fontsize=8)

    ax.set_xlabel("1/T  (K$^{-1}$)")
    ax.set_ylabel("ln P  (bar)")
    R = 8.314
    dH_kJ = (-V5 * 1000.0 * R) / 1000.0
    dS_J = V6 * R
    ax.set_title(
        f"van't Hoff plot — {formula}\n"
        f"(V5={V5:.4f}, V6={V6:.4f}; "
        f"$\\Delta H_{{des}}$ = {dH_kJ:.1f} kJ/mol H$_2$, "
        f"$\\Delta S_{{ads}}$ = {dS_J:.1f} J/mol·K)",
        fontsize=10,
    )
    ax.legend(loc="best", fontsize=9)
    ax.grid(alpha=0.3)

    out = ASSETS_DIR / "vant_hoff.png"
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return str(out)


def plot_p_vs_T(V5: float, V6: float, formula: str) -> str:
    """平台压 vs 温度 曲线(van't Hoff) — 单位 MPa。"""
    T_list = np.linspace(233, 353, 120)
    lnP = (V5 * 1000.0) / T_list + V6
    P_MPa = np.exp(lnP)   # 模型直接输出 MPa

    fig, ax = plt.subplots(figsize=(7.5, 5.0))
    ax.plot(T_list - 273.15, P_MPa, lw=2.2, color="#10b981",
            label=f"van't Hoff fit: ln P = {V5:.3f}$\\times 10^3$/T + {V6:.3f}")

    ax.axhline(0.1, color="red",    ls="--", lw=0.9, alpha=0.7, label="0.1 MPa (1 bar)")
    ax.axhline(1.0, color="orange", ls="--", lw=0.9, alpha=0.7, label="1 MPa (10 bar)")
    ax.axvline(25.0, color="gray",   ls=":",  lw=0.9, alpha=0.6, label="$25^{\\circ}$C")

    T_ref = 298.15
    P_ref_MPa = float(np.exp((V5 * 1000.0) / T_ref + V6))
    ax.scatter([25.0], [P_ref_MPa], s=80, zorder=5,
               color="#ef4444", edgecolors="white", linewidth=1.5,
               label=f"P($25^{{\\circ}}$C) = {P_ref_MPa:.2e} MPa")

    ax.set_xlabel("T  /  $^{\\circ}$C", fontsize=12)
    ax.set_ylabel("P  /  MPa",         fontsize=12)
    ax.set_yscale("log")
    ax.set_ylim(1e-3, 1e2)
    ax.set_title(f"{formula}  —  Plateau pressure (van't Hoff)", fontsize=12)
    ax.legend(fontsize=9, loc="best", framealpha=0.9)
    ax.grid(True, which="both", alpha=0.3, ls="-", lw=0.5)

    out = ASSETS_DIR / "p_vs_T.png"
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return str(out)


def plot_pct_isotherms(V5: float, V6: float, formula: str,
                       T_list_K: list | None = None,
                       n_points: int = 80,
                       capacity_mol_per_kg: float | None = None) -> str:
    """画一族等温 PCT 曲线: X=wt%, Y=P/MPa 对数刻度。"""
    from vendor.pct_toolkit_wrapper import compute_pct_curve

    if V5 is None or V6 is None:
        return ""

    if T_list_K is None:
        T_list_K = ISOTHERM_T_LIST_K
    T_arr = np.asarray(T_list_K, dtype=float)

    R = 8.314
    dH_abs_pos = -V5 * 1000.0 * R
    try:
        from pymatgen.core import Composition as _Comp
        comp = _Comp(formula)
        int_formula, _ = comp.get_integer_formula_and_factor()
        int_comp = _Comp(int_formula)
        mw = float(int_comp.weight)
        N_metal = float(sum(amt for el, amt in int_comp.items() if str(el) != "H"))
    except Exception:
        mw = 100.0
        N_metal = 1.0

    # ----- Capacity 单位:wt%(模型直接输出)→ H/M -----
    # Capacity 字段 = wt% 数字 (LaNi5 ≈ 1.5 wt%, MgH2 ≈ 7.66 wt%)
    cap_wt_pct = capacity_mol_per_kg if capacity_mol_per_kg is not None else 1.5

    # 反推 H/M:  wt% = x_H × M_H / (MW/N_metal + x_H × M_H) × 100
    # 解方程:  x_H = (wt%/100) × MW/N_metal / (M_H × (1 - wt%/100))
    M_H = 1.008
    frac = min(max(cap_wt_pct / 100.0, 1e-6), 0.999)
    M_metal_atom = mw / max(N_metal, 1e-9)
    x_h_max_raw = (frac * M_metal_atom) / (M_H * (1.0 - frac))

    # 经验钳制(根据元素类别放宽上限)
    x_h_max_capped = min(x_h_max_raw, 1.5)        # 默认上限 1.5
    if "Mg" in formula and "Ni" not in formula:
        x_h_max_capped = min(x_h_max_raw, 4.0)    # MgH2 类可达 2.0
    elif "Al" in formula or "B" in formula:
        x_h_max_capped = min(x_h_max_raw, 4.5)    # AlH3, B 类
    elif "La" in formula or "Y" in formula or "Ca" in formula:
        x_h_max_capped = min(x_h_max_raw, 1.5)    # AB5/AB2 类
    elif "Li" in formula or "Na" in formula:
        x_h_max_capped = min(x_h_max_raw, 2.0)    # LiH, NaH
    x_h_max = max(x_h_max_capped, 0.5)

    _P_base, x_H = compute_pct_curve(
        dH_abs_pos, 0.0, T_arr, H_to_M_max=x_h_max, n_points=n_points,
    )
    P_bar_center = _P_base * np.exp(V6)
    X_wt = h_to_m_to_wt_pct(x_H, formula)

    # 3) 绘图
    fig, ax = plt.subplots(figsize=(7.5, 5.0))
    cmap = plt.cm.coolwarm
    colors = [cmap(i / max(len(T_arr) - 1, 1)) for i in range(len(T_arr))]

    idx_mid = len(X_wt) // 2
    for i, (T, color) in enumerate(zip(T_arr, colors)):
        P_plat_MPa = float(P_bar_center[i, idx_mid]) * 1.0e-1

        x_alpha_end = 0.10 * x_h_max
        x_beta_start = 0.50 * x_h_max
        X_alpha_end = float(h_to_m_to_wt_pct(np.array([x_alpha_end]), formula)[0])
        X_beta_start = float(h_to_m_to_wt_pct(np.array([x_beta_start]), formula)[0])

        P_lo = max(P_plat_MPa / 100.0, 1e-4)
        P_hi = min(P_plat_MPa * 100.0, 1e3)

        k_a = max(X_alpha_end * 0.30, 0.02)
        k_b = max((X_wt[-1] - X_beta_start) / 6.0, 0.02)
        X_alpha_mid = X_alpha_end - 3 * k_a
        X_beta_mid = X_beta_start + 3 * k_b

        P_curve_MPa = np.empty_like(X_wt)
        for j in range(len(X_wt)):
            X = X_wt[j]
            if X < X_alpha_end:
                sig = 1.0 / (1.0 + np.exp(-(X - X_alpha_mid) / k_a))
                P_curve_MPa[j] = P_lo * (1 - sig) + P_plat_MPa * sig
            elif X > X_beta_start:
                sig = 1.0 / (1.0 + np.exp(-(X - X_beta_mid) / k_b))
                P_curve_MPa[j] = P_plat_MPa * (1 - sig) + P_hi * sig
            else:
                f_j = x_H[j] / x_h_max
                f_j = float(np.clip(f_j, 1e-3, 1 - 1e-3))
                dS = -R * (f_j * np.log(f_j) + (1 - f_j) * np.log(1 - f_j))
                dS_mid = -R * (0.5 * np.log(0.5) + 0.5 * np.log(0.5))
                tilt = 0.20 * (dS - dS_mid) / R
                P_curve_MPa[j] = P_plat_MPa * np.exp(tilt)

        ax.plot(X_wt, P_curve_MPa, lw=2.0, color=color,
                marker='o', markersize=3.0, markevery=6,
                label=f"{T - 273.15:+.0f}℃")

    ax.axhline(0.1, color="gray", ls=":", lw=0.8, alpha=0.6)
    ax.axhline(1.0, color="gray", ls="--", lw=0.8, alpha=0.6)
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

    out = ASSETS_DIR / "pct_isotherms.png"
    fig.tight_layout()
    fig.savefig(out, dpi=PLOT_DPI)
    plt.close(fig)
    return str(out)
