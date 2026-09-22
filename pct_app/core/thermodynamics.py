"""热力学计算:H/M ↔ wt% 换算"""

from __future__ import annotations
import numpy as np
from pymatgen.core import Composition as _Comp

M_H = 1.008


def h_to_m_to_wt_pct(x_H: np.ndarray, formula: str) -> np.ndarray:
    """
    H/M(无量纲,即每金属原子的 H 数) → 储氢质量百分比 wt.%

    推导: integer formula 中 N_metal 个金属原子,总质量 M_integer。
    每金属原子平均质量 M_metal_atom = M_integer / N_metal。
    吸氢 x_H(H/M) → 吸氢 x_H × N_metal 个 H 原子,总质量 M_integer + x_H × N_metal × M_H。
    wt% = x_H × M_H × N_metal / (M_integer + x_H × M_H × N_metal) × 100
    """
    comp = _Comp(formula)
    integer_formula, _ = comp.get_integer_formula_and_factor()
    int_comp = _Comp(integer_formula)
    M_integer = float(int_comp.weight)
    # N_metal:integer formula 中非氢原子数
    N_metal = sum(amt for el, amt in int_comp.items() if str(el) != "H")
    N_metal = float(N_metal)
    M_metal_atom = M_integer / max(N_metal, 1e-9)
    return (x_H * M_H) / (M_metal_atom + x_H * M_H) * 100.0
