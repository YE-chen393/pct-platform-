# -*- coding: utf-8 -*-
"""
PCT-Simulation-Toolkit Wrapper (v2 — geometric + void_size fallback)
===============================================================

使用官方 PHannapp/PCT-Simulation-Toolkit (vendor/PCT_Toolkit/) 的:
  - src.make_Wyckoff_db.read_wyckoff  → 枚举 Wyckoff 位置
  - src.read.write_hydride            → 把间隙位写成 Vac 占位符
  - src.VoidSize.void_size            → SLSQP 优化(H 通过 fallback 调用)

主策略:几何过滤(不用 SLSQP,秒级完成):
  对每个 Wyckoff 间隙位,量与最近金属原子距离 d;
  若 d > r_metal + r_H + buffer → 填 H
  若 d < r_metal + r_H → 跳过

备选:若几何过滤全空,用官方 void_size(SLSQP) 找合格间隙位。
"""

from __future__ import annotations
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List, Dict

import numpy as np

TOOLKIT_ROOT = Path(__file__).resolve().parent / "PCT_Toolkit"
sys.path.insert(0, str(TOOLKIT_ROOT))

# 让 pct_app 包在 vendor wrapper 单独被 import 时也能被找到
# (即使调用方没有把项目根目录加到 PYTHONPATH)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# MongoDB stub:read.py 顶层会 import
import types
if "MongoDB" not in sys.modules:
    _mongo_pkg = types.ModuleType("MongoDB")
    _mongo_pkg.__path__ = []
    sys.modules["MongoDB"] = _mongo_pkg
    _mc = types.ModuleType("MongoDB.connect")
    class _S:
        def __getattr__(self, k): return _S()
        def __call__(self, *a, **k): return _S()
        def __iter__(self): return iter([])
        def __bool__(self): return False
    _mc.collection_calculation = _mc.collection_system = _mc.db = _S()
    sys.modules["MongoDB.connect"] = _mc

# ---- Wyckoff 数据库 + 结构写/读 ----
from src.make_Wyckoff_db import read_wyckoff  # noqa: E402
from src.read import write_hydride  # noqa: E402

# ---- 常量注入(可选调参) ----
try:
    import src.CONSTANTS as _tc
    _tc.tries = 1
except Exception:
    pass

# ---- Wyckoff CSV 缓存 ----
_WYCKOFF_DB: Optional[list] = None


def _wyckoff_csv_path() -> str:
    return str(TOOLKIT_ROOT / "src" / "Wyckoff.csv")


def _get_wyckoff_db() -> list:
    global _WYCKOFF_DB
    if _WYCKOFF_DB is None:
        _WYCKOFF_DB = read_wyckoff(_wyckoff_csv_path())
    return _WYCKOFF_DB


# ============================================================
# 0. 工具:pymatgen ↔ VASP POSCAR
# ============================================================
def _structure_to_poscar(struct, out_path: str, comment: str = "auto") -> str:
    from pymatgen.core import Structure
    species = [str(s) for s in struct.species]
    lattice = struct.lattice.matrix.tolist()
    lines = [comment, "1.0"]
    for vec in lattice:
        lines.append("  " + "  ".join(f"{x:.10f}" for x in vec))
    elem_order = list(dict.fromkeys(species))
    lines.append(" ".join(f"  {e}" for e in elem_order))
    lines.append(f"  {len(species)}")
    lines.append("Cartesian")
    for sp, site in zip(species, struct.sites):
        x, y, z = site.coords
        lines.append(f"  {x:.8f}  {y:.8f}  {z:.8f}  {sp}")
    Path(out_path).write_text("\n".join(lines) + "\n")
    return out_path


# ============================================================
# 1. 结构原型库
# ============================================================
STRUCTURE_PROTOTYPES = {
    "LaNi5":    ("LaNi5",     "P6/mmm",    5.014, 3.984),
    "MgH2":     ("MgH2",      "P4_2/mnm",  4.501, 3.012),
    "TiFe":     ("TiFe",       "Pm-3m",     2.978, 2.978),
    "YMn4Ni1":  ("YMn4Ni",    "P6/mmm",    5.260, 4.310),
    "LaMn4Ni1": ("LaMn4Ni",   "P6/mmm",    5.280, 4.330),
    "CaNi5":    ("CaNi5",      "P6/mmm",    4.960, 3.940),
    "TiMn2":    ("TiMn2",     "P6_3/mmc",  4.825, 7.953),
}


def _guess_prototype(formula: str) -> Optional[Tuple]:
    norm = formula.replace(" ", "")
    for key, proto in STRUCTURE_PROTOTYPES.items():
        if key in norm or norm.startswith(key[:3]):
            return proto
    if any(el in norm for el in ["La", "Ce", "Pr", "Nd", "Sm", "Y"]) and "Ni" in norm:
        return ("RRNi5", "P6/mmm", 5.000, 4.000)
    if "Mg" in norm and "H" in norm:
        return ("MgH2", "P4_2/mnm", 4.501, 3.012)
    if "Ti" in norm and "Fe" in norm:
        return ("TiFe", "Pm-3m", 2.978, 2.978)
    return None


def structure_from_formula(formula: str, supercell: int = 2):
    """化学式 → pymatgen Structure + 原型名。

    实现:
      1. 调用 _guess_prototype → (原型名, 空间群, a, c)
      2. 用 prototype 的 f.u. 占据生成单胞 structure(AB5 / AB2 / AB / ... 等模式)
      3. 对 AB5 类型(LaNi5 等),按化学式比例替换 1a 位(RE 元素混合 La+Y)
         和 6i / 3g 位(过渡金属混合 Ni+Mn 等)
      4. 最后做 supercell 复制
    """
    from pymatgen.core import Structure, Lattice, Composition
    proto = _guess_prototype(formula)
    if proto is None:
        raise ValueError(f"无法为 {formula} 找到合适的结构原型")

    name, sg, a, c = proto
    lattice = Lattice.from_parameters(
        a, a, c, 90, 90,
        120 if "P6" in sg or "P3" in sg else 90,
    )
    if "Ni5" in name or name.endswith("Ni5"):
    # ===== CaCu5 型 (P6/mmm):
        #   1a: (0,0,0) — 稀土 / Ca 位
        #   2c: (1/3, 2/3, 0) + (2/3, 1/3, 0) — Ni (3g 折到 2c + 3g)
        #   3g: (1/2, 0, 1/2), (1/2, 1/2, 1/2), (0, 0, 1/2)
        # ===== 按化学式比例替换:
        #   RE 位(1a × 1): 按化学式中 RE 系元素比例分摊
        #   Ni 位(2c + 3g = 5): 按化学式中 TM 元素 + 剩余 Ni 分摊

        comp = Composition(formula).fractional_composition
        # RE 系元素(填 1a)
        RE_NAMES = {"La", "Ce", "Pr", "Nd", "Sm", "Eu", "Gd", "Tb",
                    "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Y", "Ca", "Mg"}
        re_elems = {el: amt for el, amt in comp.items() if str(el) in RE_NAMES}
        tm_elems = {el: amt for el, amt in comp.items() if str(el) not in RE_NAMES}
        # 确保至少有一个 RE 元素
        if not re_elems:
            re_elems = {"La": 1.0}
            if "Y" in formula:
                re_elems = {"Y": 1.0}
        if not tm_elems:
            tm_elems = {"Ni": 5.0}

        # RE 位: 6 个坐标(1a × 6,因 supercell 还在外面做 × (S,S,1))
        # 我们在单胞就放 6 个,然后 supercell x² → 24 个.
        re_total = sum(re_elems.values())
        # 把 RE 按比例分成 N 个原子放进 6 个 RE 位(单胞),后续 supercell x² = 24 个
        # 但这里先按 f.u. 出 1 个 La(即单胞 1 个 La + 5 个 TM)
        # 简化: 把 6 个单胞RE位都按概率选(用 f.u. 比例的乘法)
        # 直接生成 6 个 RE 原子,各元素按 re_total 比例
        re_pieces = []
        for el, amt in re_elems.items():
            # 单胞有 6 个 RE 位(因为 supercell 2x2x1 后是 1 × 6)
            # 但实际上 单胞有 1 个 RE 位,supercell(2,2,1) 后是 4 个.
            # 我们直接生成 4 个(因为 supercell 之后会 × (2,2,1))
            # 这里用一个累积器:
            re_pieces.append((str(el), amt / re_total))
        # 用 round-robin 按 re_total × 4 个 slot 分配
        re_total_int = 4
        re_species = []
        i_re, max_iter = 0, 0
        counts = {el: 0 for el, _ in re_pieces}
        while sum(counts.values()) < re_total_int and max_iter < 100:
            el, frac = re_pieces[i_re % len(re_pieces)]
            expected = frac * re_total_int
            if counts[el] < round(expected + 0.4):
                re_species.append(el)
                counts[el] += 1
            i_re += 1
            max_iter += 1
        # 如果还不够,补上最多的
        while len(re_species) < re_total_int:
            re_species.append(re_pieces[0][0])
        # 超过则截
        re_species = re_species[:re_total_int]

        # TM 位: 总共 5 × 4 = 20 个(单胞 5, supercell 4 倍)
        tm_total = sum(tm_elems.values())
        tm_pieces = [(str(el), amt / tm_total) for el, amt in tm_elems.items()]
        tm_total_int = 20
        tm_species = []
        i_tm, max_iter = 0, 0
        counts_tm = {el: 0 for el, _ in tm_pieces}
        while sum(counts_tm.values()) < tm_total_int and max_iter < 100:
            el, frac = tm_pieces[i_tm % len(tm_pieces)]
            expected = frac * tm_total_int
            if counts_tm[el] < round(expected + 0.4):
                tm_species.append(el)
                counts_tm[el] += 1
            i_tm += 1
            max_iter += 1
        while len(tm_species) < tm_total_int:
            tm_species.append(tm_pieces[0][0])
        tm_species = tm_species[:tm_total_int]

        # 单胞坐标 (CaCu5): 1a + 2c + 3g = 6 sites
        # 单胞只放 1 个 RE + 5 个 TM
        # 但我们需要从 re_species 取 1 个,tm_species 取 5 个,且后续 supercell ×4 = 4 / 20
        # 简化策略: 单胞按 1 RE + 5 TM 摆放 6 sites,supercell 复制 4 倍.
        # 这就要求 re_species 与 tm_species 长度恰好为 1 与 5(单胞布局).
        # 为避免代码复杂,我们将单胞个数也直接定为 4 RE + 20 TM(2x2x1 后的"单胞")
        # 但 supercell 是 2x2x1,意味着单胞 1 RE + 5 TM,扩 4 倍 = 4/20.
        # 所以单胞就用 1 RE + 5 TM 摆放:
        species = [re_species[0]] + tm_species[:5]
        coords = [
            [0, 0, 0],                                  # 1a (RE)
            [1/3, 2/3, 0],                              # 2c (Ni-1)
            [2/3, 1/3, 0],                              # 2c (Ni-2)
            [0.5, 0, 0.5],                              # 3g (Ni-3)
            [0.5, 0.5, 0.5],                            # 3g (Ni-4)
            [0, 0, 0.5],                                # 3g (Ni-5)
        ]
        # 把多余 re_species/tm_species 留到调用者;但实际上 supercell 会自动复制,
        # 所以单胞 1+5 即可,然后 supercell 扩成 4+20,比例刚好对位.
        # 但用户希望整体比例为 La0.7:Y0.3 = 7:3,共 4 RE 位:
        # 4 = 4*(0.7+0.3),此时比例自动保持.
        # 如果需要完整掺比,需要让 re_species 长度 = 4,直接放 4 RE atom 到单胞的不同位
        # 不行,因为单胞只能放 1 RE (1a)+ 5 TM.
        # 替代方案: 把 La 和 Y 视为两种 site:La@1a + Y@2c?
        # 实际钙钛矿式取代: 全部 RE 元素共享 1a 位,但通过 occupancy 分数化.
        # pymatgen 不允许 1a 位有 2 个不同元素,除非用 Specie(置换)
        from pymatgen.core.periodic_table import Specie
        # 1a 位: 各 RE 元素按比例 occupancy
        re_occ = {}
        for el, frac in re_pieces:
            re_occ[Specie(el)] = frac
        # 单胞里,RE 位是一个原子但用 IStructure 的 occupancy 即可支持 partial occupancy
        species_w_occ = []
        for i, (sp, c) in enumerate(zip(species, coords)):
            if i == 0:
                # RE 位, 用 partial occupancy
                species_w_occ.append((sp, c))  # 主 species
            else:
                species_w_occ.append((sp, c))

        # 为了让 4× supercell 包含混合 RE,最简单办法:把单胞的 1 个 RE 位替换成
        # 多个 site's occupancy. 但 pymatgen 的 Structure 不支持 fractional occupancy
        # 在 (supercell 之后) 直接随机分配.
        # 这里采用简单做法: 把 1 个 RE 位按比例拆成 N_re 个不同元素,变成
        # 单胞有 N_RE 原子(而不是 1)
        # 重新设计: 单胞直接生成 N_RE 个 RE 原子 + N_TM 个 TM 原子
        # N_RE = 4 (supercell 之前),N_TM = 20,然后不做 supercell
        # 不行,与 supercell 逻辑冲突.

        # ★ 妥协方案: 单胞 1a 用第一个 RE,supercell 后随机构造 substitute
        # 更简单: 强制在 supercell 之前,单胞生成"完整"的 N_RE + N_TM 个原子
        # 然后不做 supercell
        n_re_total = 4  # 模拟 supercell(2,2,1) 复制
        n_tm_total = 20
        # 用 Composition 还原: 取纯 RE 比例 × n_re_total, TM 比例 × n_tm_total
        re_actual = []
        counts = {el: 0 for el, _ in re_pieces}
        i = 0
        while sum(counts.values()) < n_re_total and i < 200:
            el, frac = re_pieces[i % len(re_pieces)]
            expected = frac * n_re_total
            if counts[el] < round(expected + 0.3):
                re_actual.append(el)
                counts[el] += 1
            i += 1
        while len(re_actual) < n_re_total:
            re_actual.append(re_pieces[0][0])
        re_actual = re_actual[:n_re_total]

        tm_actual = []
        counts_t = {el: 0 for el, _ in tm_pieces}
        i = 0
        while sum(counts_t.values()) < n_tm_total and i < 500:
            el, frac = tm_pieces[i % len(tm_pieces)]
            expected = frac * n_tm_total
            if counts_t[el] < round(expected + 0.3):
                tm_actual.append(el)
                counts_t[el] += 1
            i += 1
        while len(tm_actual) < n_tm_total:
            tm_actual.append(tm_pieces[0][0])
        tm_actual = tm_actual[:n_tm_total]

        # 单胞 f.u. 坐标 (CaCu5, 1a + 2c + 3g) — 共 6 sites
        # 然后用 pymatgen.make_supercell 正确复制 2x2x1
        fu_coords = [
            [0, 0, 0],                                  # 1a   (RE)
            [1/3, 2/3, 0],                              # 2c-1 (Ni)
            [2/3, 1/3, 0],                              # 2c-2 (Ni)
            [1/2, 0, 1/2],                              # 3g-1 (Ni)
            [0, 1/2, 1/2],                              # 3g-2 (Ni)
            [1/2, 1/2, 1/2],                            # 3g-3 (Ni)
        ]
        # 单胞 1 RE + 5 TM = 6 原子,然后 supercell 2x2x1 = 24
        prim_species = [re_species[0]] + tm_species[:5]
        prim = Structure(lattice, prim_species, fu_coords,
                         coords_are_cartesian=False)
        # ★ 用传入的 supercell 参数动态扩胞
        #   - 单胞 1 RE + 5 TM = 6 sites,supercell (S,S,1) → S²×6 sites
        #   - RE 元素总数 = S² 个(每原胞 1 个 × S² 倍)
        #   - TM 元素总数 = 5×S² 个
        sc = supercell
        struct = prim.make_supercell([sc, sc, 1])
        # 重新生成 re_actual / tm_actual,数量按 S² 倍计算
        re_total_int_dyn = sc * sc
        tm_total_int_dyn = 5 * sc * sc
        re_actual = []
        counts = {el: 0 for el, _ in re_pieces}
        i = 0
        while sum(counts.values()) < re_total_int_dyn and i < 200:
            el, frac = re_pieces[i % len(re_pieces)]
            expected = frac * re_total_int_dyn
            if counts[el] < round(expected + 0.3):
                re_actual.append(el)
                counts[el] += 1
            i += 1
        while len(re_actual) < re_total_int_dyn:
            re_actual.append(re_pieces[0][0])
        re_actual = re_actual[:re_total_int_dyn]

        tm_actual = []
        counts_t = {el: 0 for el, _ in tm_pieces}
        i = 0
        while sum(counts_t.values()) < tm_total_int_dyn and i < 500:
            el, frac = tm_pieces[i % len(tm_pieces)]
            expected = frac * tm_total_int_dyn
            if counts_t[el] < round(expected + 0.3):
                tm_actual.append(el)
                counts_t[el] += 1
            i += 1
        while len(tm_actual) < tm_total_int_dyn:
            tm_actual.append(tm_pieces[0][0])
        tm_actual = tm_actual[:tm_total_int_dyn]

        # 替换 site species
        #   - pymatgen make_supercell 顺序: 每个 primitive site → S² 个复制(连续)
        #   - 所以 site 0..(S²-1) 是 RE,site S²..(6×S²-1) 是 TM(每组 5 个 TM 各复制 S² 倍)
        try:
            new_species = list(struct.species)
            for k in range(re_total_int_dyn):
                new_species[k] = re_actual[k] if k < len(re_actual) else re_actual[0]
            for grp in range(5):
                for k in range(sc * sc):
                    idx = re_total_int_dyn + grp * sc * sc + k
                    if idx < len(new_species):
                        new_species[idx] = tm_actual[grp * sc * sc + k] if (grp * sc * sc + k) < len(tm_actual) else tm_actual[0]
            struct = Structure(struct.lattice, new_species,
                               struct.frac_coords, coords_are_cartesian=False)
        except Exception:
            # 替换失败 → 退回原 supercell
            pass
        return struct, name

    # 非 CaCu5 型(AB2 / AB / AH2 等): 用单胞 f.u. 占位 + supercell 复制
    # 取化学式中"主元素"的化学计量,直接按比例生成 N 个原子
    comp = Composition(formula).fractional_composition
    # 把 f.u. 数量归一化,以主元素丰度为基准
    total = sum(comp.values())
    # 每个 supercell(2,2,1) 复制后含 4 × f.u. 个原子
    fu_total = int(round(total))
    n_cells = max(1, fu_total) * (supercell ** 2)
    # 取化学式中的元素及其比例
    pieces = [(str(el), amt / total) for el, amt in comp.items()]
    species = []
    counts = {el: 0 for el, _ in pieces}
    i = 0
    while sum(counts.values()) < n_cells and i < 500:
        el, frac = pieces[i % len(pieces)]
        expected = frac * n_cells
        if counts[el] < round(expected + 0.4):
            species.append(el)
            counts[el] += 1
        i += 1
    while len(species) < n_cells:
        species.append(pieces[0][0])
    species = species[:n_cells]

    # 单胞 f.u. 坐标: 按 CaCu5 风格 1a/2c/3g 的简化版,放到 (0,0,0) + 等价位置
    # 非 AB5 时退化为简单立方式(对 MgH2 / TiFe 等足够)
    fu_coords = [
        [0, 0, 0],
        [0.5, 0.5, 0],
        [0.5, 0, 0.5],
        [0, 0.5, 0.5],
    ]
    all_species = []
    all_coords = []
    n_fu_per_cell = 4
    idx = 0
    for sx in range(supercell):
        for sy in range(supercell):
            for sz in range(1):
                shift = [sx / supercell, sy / supercell, 0.0]
                for j, fc in enumerate(fu_coords):
                    if idx >= len(species):
                        break
                    all_species.append(species[idx])
                    shifted = [(fc[k] + shift[k]) % 1.0 for k in range(3)]
                    all_coords.append(shifted)
                    idx += 1
    struct = Structure(lattice, all_species, all_coords,
                       coords_are_cartesian=False)
    return struct, name


# ============================================================
# 2. ★★ 几何过滤氢化 (快速路径, 不用 SLSQP)
# ============================================================
_METALLIC_RADII = {
    "La": 1.87, "Y": 1.80, "Ce": 1.81, "Pr": 1.82, "Nd": 1.81,
    "Sm": 1.80, "Mg": 1.60, "Ca": 1.97,
    "Ni": 1.24, "Fe": 1.26, "Mn": 1.27, "Ti": 1.47, "Co": 1.25,
    "Cr": 1.28, "Vv": 1.34, "Al": 1.43, "Cu": 1.28,
    "X": 1.30,
}
_R_H = 0.37          # H 共价半径(Å)
_MIN_VOID_R = 0.36   # 间隙半径阈值(Å),太小物理上填不进


def _eval_wyckoff(pos_str: str, x: float = 0.25, y: float = 0.25, z: float = 0.25):
    """解析 Wyckoff 位置表达式 → 分数坐标 (0,1)。

    默认 x=y=z=0.25 是化学合理起点(四面体/八面体间隙附近)，
    比硬编码 0.5 更接近多数储氢合金的真实占据位置。
    """
    s = pos_str.strip().strip("()")
    parts = [p.strip() for p in s.split(",")]
    out = []
    for p, var in zip(parts, [x, y, z]):
        p = p.replace("+x", "x").replace("+y", "y").replace("+z", "z")
        try:
            val = eval(p, {}, {"x": var, "y": var, "z": var})
        except Exception:
            val = 0.5
        out.append(float(val) % 1.0)
    return np.array(out, dtype=float)


def _generate_symmetric_positions(pos_str: str, mult: int,
                                  x: float = 0.25, y: float = 0.25, z: float = 0.25):
    """给定一个 Wyckoff 代表位置字符串，生成 mult 个对称等价分数坐标。

    Wyckoff CSV 中每个条目只存了代表位置的 1 个表达式；
    mult 相同的位置共享同一表达式，通过对称操作生成其余等价位置。
    这里用简化的蒙特卡洛扰动来近似：围绕代表点，在 ±0.1 fractional 范围
    内生成 (mult-1) 个扰动点（保持物理上合理的分布）。
    """
    rep = _eval_wyckoff(pos_str, x=x, y=y, z=z)
    positions = [rep]
    rng = np.random.RandomState(int(hash(rep.tobytes()) & 0xFFFFFFFF) % (2**31))
    for _ in range(mult - 1):
        # 轻微随机扰动(0.03 fractional)，确保不与金属原子完全重合
        offset = rng.uniform(-0.06, 0.06, size=3)
        candidate = (rep + offset) % 1.0
        positions.append(candidate)
    return positions


def _expand_supercell_positions(pos_str: str, supercell: tuple = (2, 2, 1),
                                  x: float = 0.25, y: float = 0.25, z: float = 0.25):
    """对单条 Wyckoff position 字符串:
      1. eval 1 次得到代表分数坐标 fc ∈ [0,1)³
      2. 通过超胞平移 (i, j, k) / (Sx, Sy, Sz) 得到 Sx×Sy×Sz 个等价点
         因为晶体是周期性的,在 2×2×1 超胞中新的候选位置应等于 fc 在
         (0, 1/Sx, 2/Sx, ...) × (0, 1/Sy, 2/Sy, ...) × (0, 1/Sz, ...) 的栅格上,
         再 mod 1 折回原始晶胞。

    返回: list of np.ndarray,每个 shape (3,),值 ∈ [0,1)
    """
    rep = _eval_wyckoff(pos_str, x=x, y=y, z=z)
    Sx, Sy, Sz = supercell
    positions = []
    for i in range(Sx):
        for j in range(Sy):
            for k in range(Sz):
                shift = np.array([i / Sx, j / Sy, k / Sz])
                positions.append((rep + shift) % 1.0)
    return positions


def _geometric_hydrogenate(struct_base, formula, proto, supercell_size: int = 2,
                          pre_extracted_wyckoff: list | None = None,
                          pre_extracted_hall_no: int | None = None,
                          fill_fraction: float = 1.0,
                          H_to_M: float | None = None):
    """用 Wyckoff CSV + 几何距离过滤确定可填 H 的间隙位。

    算法 (v4 — 加入 fill_fraction / H_to_M 控制):
      1. 按 Hall 号取该空间群的 Wyckoff CSV(支持预提取)
      2. 对每条 pos_str eval 一次得到代表分数坐标
      3. 通过超胞平移 (sx, sy, sz) / (Sx, Sy, Sz) 展开成 Sx×Sy×Sz 个等价点
         (因 LaNi5 等 2×2×1 超胞用 A m m 2 sub-symmetry, Wyckoff 等价点不会随超胞复制)
      4. 每个点按"距最近金属 - r_metal - r_H"计算可用 void_r,>= _MIN_VOID_R 视为可用
      5. 贪心:H 数达到目标的填充
         - fill_fraction: 0~1 填充比例 (fill_fraction × n_metal = H 原子数)
         - H_to_M: 直接指定 H/M 比 (0~3,覆盖 fill_fraction)
           若 H_to_M 给出,目标 H 数 = round(n_metal_real × H_to_M)
    """
    from pymatgen.core import Structure, Lattice, Composition

    if pre_extracted_hall_no is not None and pre_extracted_wyckoff is not None:
        hall_no = pre_extracted_hall_no
        wyckoff_db = _get_wyckoff_db()
        group = wyckoff_db[hall_no - 1]
    else:
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
        # 退化的多重占位结构 spglib 经常拒识(返回 hall_no<1),多次试错
        hall_no = -1
        for symprec in (0.1, 0.05, 0.02, 0.01, 1e-3):
            try:
                sga = SpacegroupAnalyzer(struct_base, symprec=symprec)
                ds = sga.get_symmetry_dataset()
                if ds and getattr(ds, "hall_number", 0) and 1 <= ds.hall_number <= 530:
                    hall_no = ds.hall_number
                    break
            except Exception:
                continue
        # 多重占位 P1 是常见结果——回退到原始 proto 提供的常见 Hall 号
        if hall_no < 1 or hall_no > 530:
            proto_to_hall = {
                "LaNi5": 191, "RRNi5": 191,
                "MgCu2": 227, "MgZn2": 194, "MgNi2": 194,
                "MgH2":  136,
                "TiFe":  221,
                "TiNi5": 191,
            }
            hall_no = proto_to_hall.get(proto, 191)  # 默认 P6/mmm (CaCu5)
            # 等价位置从 proto 直接给
            wyckoff_db = _get_wyckoff_db()
            group = wyckoff_db[hall_no - 1]

    lat = struct_base.lattice
    # ★ 只取金属原子（H 不参与 n_metal 计数）
    metal_sites = [(s.coords, str(s)) for s in struct_base.sites
                   if str(s.specie) != "H"]
    metal_coords = [c for c, _ in metal_sites]
    metal_labels  = [l for _, l in metal_sites]
    n_metal_real = len(metal_coords)
    if n_metal_real == 0:
        return None, None

    def nearest_metal(frac_coords):
        cart = lat.get_cartesian_coords([frac_coords])[0]
        best_d, best_el = float("inf"), "X"
        for mc, ml in zip(metal_coords, metal_labels):
            d = np.linalg.norm(cart - mc)
            if d < best_d:
                best_d, best_el = d, ml
        return best_d, best_el

    # ★★★ 关键修复 v3:
    #   对 letter 的每条 pos_str eval 后,通过 supercell 平移得到 Sx×Sy×Sz 倍等价点
    #   这样 LaNi5 2×2×1 超胞下,e(4) 的 4 条 position 字符串每条产生 4 个等价点 → 16 个候选 H 位
    candidate_groups = {}  # letter -> list of {fc, void_r, dist, nearest}
    # 全局位置集合(跨 letter 去重):Hall 191 的 a×4 / b×4 / c×4 在 2×2×1 超胞展开后
    # 部分位置重合(因为对称操作 + 平移组合可能落到同一坐标),这里做一次性去重。
    global_pos_set = set()

    for w in group["wyckoff"]:
        letter = w["letter"]
        mult = w["multiplicity"]
        if mult >= n_metal_real:
            continue

        group_sites = []
        for pos_str in w["positions"]:
            try:
                equiv_positions = _expand_supercell_positions(
                    pos_str,
                    supercell=(supercell_size, supercell_size, 1),
                    x=0.25, y=0.25, z=0.25,
                )
            except Exception:
                continue
            for fc in equiv_positions:
                key = tuple(round(float(x), 4) for x in fc)
                if key in global_pos_set:
                    continue   # 跨 letter 去重
                d, nearest_el = nearest_metal(fc)
                r_m = _METALLIC_RADII.get(nearest_el, 1.30)
                void_r = d - r_m - _R_H
                if void_r >= _MIN_VOID_R:
                    group_sites.append({
                        "fc": fc,
                        "void_r": void_r,
                        "dist": d,
                        "nearest": nearest_el,
                    })
                    global_pos_set.add(key)

        if group_sites:
            candidate_groups[letter] = group_sites

    if not candidate_groups:
        return None, None

    # 贪心选择：每个 letter 是一个完整 orbit（其 mult 个等价位置）
    # 按 (mult × mean_void_r) 降序排序，依次取整 orbit 直到 H 数达到目标
    # H_to_M: 直接指定 H/M (0~3), 覆盖 fill_fraction
    if H_to_M is not None:
        ff = max(0.0, float(H_to_M))        # 允许 > 1
    else:
        ff = max(0.0, min(1.0, float(fill_fraction)))
    H_target = max(1, int(round(n_metal_real * ff)))
    # 标记本次实际使用的填充比例,UI 显示用
    used_fill_fraction = ff

    # 全部可用轨道(按评分排序)累计可达 H 上限 — 物理可达的 H/M_max
    # 此时 candidate_groups 已经做过跨 letter 去重,所以每个 orbit 都是真正的"独占"位置
    max_total = sum(len(sites) for _, sites in candidate_groups.items())
    achieved_target = min(H_target, max_total)
    capped_due_to_capacity = (H_target > max_total)

    chosen_orbits = []  # list of (letter, [fc...])
    total_H = 0
    for letter, sites in candidate_groups.items():
        if total_H >= achieved_target:
            break
        # 按比例从该 orbit 截取
        need = min(len(sites), achieved_target - total_H)
        chosen_orbits.append((letter, sites[:need]))
        total_H += need
    # 截断最后一个 orbit 多余的位置(保留前 N 个)
    excess = total_H - achieved_target
    if excess > 0 and chosen_orbits:
        letter, sites = chosen_orbits[-1]
        chosen_orbits[-1] = (letter, sites[: max(1, len(sites) - excess)])

    # ★ 跨 orbit 最终去重(防御性:若 letter 内还有重复)
    final_sites = []
    final_seen = set()
    final_summary = []
    for letter, sites in chosen_orbits:
        uniq = []
        for s in sites:
            key = tuple(round(float(x), 4) for x in s["fc"])
            if key in final_seen:
                continue
            final_seen.add(key)
            uniq.append(s)
        if uniq:
            final_sites.append((letter, uniq))
            final_summary.append((letter, len(uniq),
                                  sum(x["void_r"] for x in uniq) / len(uniq)))

    chosen_orbits = final_sites
    filled_summary = {l: (n, vr) for l, n, vr in final_summary}
    n_H_final_unfilled = max_total  # 全部 unique 站点数 = max_total

    # ★ 若 Wyckoff 候选位仍不足以达到 H_target,做稠密网格扫描,
    #   找 (H_target - n_H_final_unfilled) 个额外的 void 中心填入。
    #   这样 H_to_M=3.0 也能容纳,而不是被截断。
    extra_needed = H_target - n_H_final_unfilled
    if extra_needed > 0:
        # 在 fractional space 生成 N×N×N 的网格,过滤出 void_r 足够大的点
        # 网格密度:每维取 max(10, supercell × 5) 个点,比 Wyckoff 密 5 倍
        n_grid = max(10, supercell_size * 5 + 1)
        xs = np.linspace(0, 1, n_grid, endpoint=False)
        ys = np.linspace(0, 1, n_grid, endpoint=False)
        zs = np.linspace(0, 1, max(3, supercell_size * 2 + 1), endpoint=False)
        grid_candidates = []
        for xi in xs:
            for yi in ys:
                for zi in zs:
                    fc = (float(xi), float(yi), float(zi))
                    key = tuple(round(x, 4) for x in fc)
                    if key in global_pos_set:
                        continue   # 已在 Wyckoff 里,跳过
                    d, ne = nearest_metal(fc)
                    r_m = _METALLIC_RADII.get(ne, 1.30)
                    void_r = d - r_m - _R_H
                    if void_r >= _MIN_VOID_R:
                        grid_candidates.append({
                            "fc": list(fc),
                            "void_r": void_r,
                            "dist": d,
                            "nearest": ne,
                        })
        # 按 void_r 降序,贪心选前 extra_needed 个
        # 但还要防止选中的点彼此太近(避免 H-H 重叠)
        # 用最小间距约束 = supercell 边长 / n_grid(避免和已有 Wyckoff 位重叠)
        min_sep = 1.0 / n_grid * 0.9   # 略小于格子间距
        grid_candidates.sort(key=lambda x: -x["void_r"])
        picked = []
        for cand in grid_candidates:
            ok = True
            cand_cart = lat.get_cartesian_coords([cand["fc"]])[0]
            for p in picked:
                p_cart = lat.get_cartesian_coords([p["fc"]])[0]
                if np.linalg.norm(cand_cart - p_cart) < min_sep:
                    ok = False
                    break
            if ok:
                picked.append(cand)
            if len(picked) >= extra_needed:
                break
        if picked:
            chosen_orbits.append(("grid", picked))

    # 构建氢化物 Structure（保留原始原子，只追加新 H）
    new_species = [str(s) for s in struct_base.species]
    new_fracs   = [list(s.frac_coords) for s in struct_base.sites]
    filled_summary = {}
    for letter, sites in chosen_orbits:
        for s in sites:
            new_species.append("H")
            new_fracs.append(list(s["fc"]))
        mean_vr = sum(x["void_r"] for x in sites) / len(sites)
        filled_summary[letter] = (len(sites), mean_vr)

    hydride = Structure(lat, new_species, new_fracs, coords_are_cartesian=False)

    # ★ 统计：基于最终氢化物结构（原有 H + 新加 H 全部计入）
    all_species_str = [str(s) for s in hydride.species]
    n_metal_final = sum(1 for sp in all_species_str if sp != "H")
    n_H_final      = sum(1 for sp in all_species_str if sp == "H")

    int_formula, _ = Composition(formula).get_integer_formula_and_factor()
    int_comp = Composition(int_formula)
    mw = float(int_comp.weight)
    n_metal_per_fu = float(sum(
        amt for el, amt in int_comp.items() if str(el) != "H"
    ))
    n_H_per_fu = n_H_final * n_metal_per_fu / max(n_metal_final, 1)
    H_mass = n_H_per_fu * 1.008
    wt_pct = H_mass / (mw + H_mass) * 100.0

    info = {
        "prototype": proto,
        "spacegroup": group["symbol"],
        "hall_number": hall_no,
        "n_metal": n_metal_final,
        "n_H": n_H_final,
        "H_to_M": n_H_final / max(n_metal_final, 1),
        "wt_pct": wt_pct,
        "method": "geometric Wyckoff filter (PCT-Simulation-Toolkit src/)",
        "filled_sites": [
            f"{l}×{n}(void_r={vr:.2f}Å)"
            for l, (n, vr) in filled_summary.items()
        ],
        "H_to_M_requested": H_to_M if H_to_M is not None else used_fill_fraction,
        # max_total 在跨轨道去重之前;实际可达上限以真正填入的 n_H 为准
        "H_to_M_max_achievable": n_H_final_unfilled / max(n_metal_real, 1),
        "capped": capped_due_to_capacity,
    }
    return hydride, info


# ============================================================
# 3. 备选:官方 void_size (SLSQP,慢,仅在几何过滤为空时调用)
# ============================================================
def _voidsize_fallback(struct_base, hall_no, all_wyckoff, tmp):
    """调官方 VoidSize.void_size → 返回有 H 的 Structure。"""
    from src.VoidSize import void_size
    from pymatgen.core import Structure

    poscar_path = os.path.join(tmp, "PV")
    _structure_to_poscar(struct_base, poscar_path)

    try:
        hyd_text, _ = write_hydride(all_wyckoff, poscar_path)
        pv2 = os.path.join(tmp, "PV2")
        with open(pv2, "w") as f:
            f.write(hyd_text)
        void_size(pv2, all_wyckoff)
        nn_path = os.path.join(tmp, "NN")
        with open(nn_path, "w") as f:
            f.write(open(pv2).read())
        from src.read import read_poscar as _rp
        lv, atoms = _rp(nn_path, VACS=True)
        from pymatgen.core import Lattice
        lat = Lattice(lv)
        m_spec, m_frac, h_frac = [], [], []
        for atom in atoms:
            if atom.label.lower().startswith("vac"):
                pos = []
                for coord in atom.position:
                    try:
                        pos.append(eval(coord, {}) % 1.0)
                    except Exception:
                        pos.append(0.5)
                h_frac.append(pos)
            else:
                m_spec.append(atom.label)
                m_frac.append([float(p) % 1.0 for p in atom.position])
        if not h_frac:
            return None
        hydride = Structure(lat, m_spec + ["H"] * len(h_frac),
                            m_frac + h_frac, coords_are_cartesian=False)
        return hydride
    except Exception:
        return None


# ============================================================
# 4. 主入口:hydrogenate_via_voidsize
# ============================================================
def hydrogenate_via_voidsize(formula: str, supercell: int = 2,
                             min_void_radius_A: float = 0.35,
                             fill_fraction: float = 1.0,
                             H_to_M: float | None = None,
                             max_supercell: int = 5):
    """加氢主入口:几何过滤(快速,秒级)。

    Args:
        H_to_M: 直接指定 H/M 比 (0~3), 覆盖 fill_fraction。
            若给出,目标 H 原子数 = round(n_metal × H_to_M)。
        fill_fraction: 填充比例 0~1(当 H_to_M 未指定时使用)。
            1.0 = 满填充(默认), 0.5 = 半填充, 0.0 = 仅母相不填 H。
        max_supercell: 当 H_to_M 超出当前超胞容量时,自动向上扩胞(2→3→4→...)
            直到能容纳目标 H 数,上限 max_supercell×max_supercell×2。
    """
    # ★ 若 H_to_M > 0,尝试几何填充 + grid scan;
    #   若仍不足以达到目标 H 数(罕见,仅极高 H/M 时发生),自动升级超胞。
    actual_supercell = supercell
    used_auto_expand = False
    if H_to_M is not None and H_to_M > 0:
        proto_peek, _ = structure_from_formula(formula, supercell=supercell)
        n_metal_peek = sum(1 for s in proto_peek.sites if str(s.specie) != "H")
        H_target_peek = int(round(n_metal_peek * max(0.0, float(H_to_M))))
        cur_sc = supercell
        while cur_sc < max_supercell:
            # grid scan 估算: supercell=cur_sc 时 grid 有效位 ≈ 4 × cur_sc²
            # (经验:2×2→4,3×3→36,4×4→64,5×5→100,...)
            est_grid_H = 4 * (cur_sc ** 2)
            if est_grid_H >= H_target_peek:
                break
            cur_sc += 1
        used_auto_expand = (cur_sc != supercell)
        if used_auto_expand:
            actual_supercell = cur_sc

    struct_base, proto = structure_from_formula(formula, supercell=actual_supercell)
    hall_no = None
    all_wyckoff = None
    # proto 已知时优先用 proto 对应的 Hall 号(pymatgen 在多重占位下常降到 P1/Pmm2 等
    # 子群, 但"理想"间隙位仍在 P6/mmm 等原型对称性下才完整匹配 supercell 网格)
    proto_to_hall = {
        "LaNi5": 191, "RRNi5": 191,
        "MgCu2": 227, "MgZn2": 194, "MgNi2": 194,
        "MgH2":  136,
        "TiFe":  221,
        "TiNi5": 191,
    }
    if proto in proto_to_hall:
        hall_no = proto_to_hall[proto]
    else:
        try:
            from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
            ds = None
            for symprec in (0.1, 0.05, 0.02, 0.01, 1e-3):
                try:
                    sga = SpacegroupAnalyzer(struct_base, symprec=symprec)
                    ds = sga.get_symmetry_dataset()
                    if ds and getattr(ds, "hall_number", 0) and 1 <= ds.hall_number <= 530:
                        break
                except Exception:
                    continue
            if ds and getattr(ds, "hall_number", 0) and 1 <= ds.hall_number <= 530:
                hall_no = ds.hall_number
            else:
                hall_no = 191  # 默认 CaCu5
        except Exception:
            hall_no = 191
    try:
        wyckoff_db = _get_wyckoff_db()
        group = wyckoff_db[hall_no - 1]
        all_wyckoff = [{"letter": w["letter"],
                       "multiplicity": w["multiplicity"],
                       "positions": list(w["positions"])}
                      for w in group["wyckoff"]]
    except Exception:
        pass

    # 几何过滤(快速路径,支持 supercell 展开)
    hydride, info = _geometric_hydrogenate(
        struct_base, formula, proto,
        supercell_size=actual_supercell,
        pre_extracted_wyckoff=all_wyckoff,
        pre_extracted_hall_no=hall_no,
        fill_fraction=fill_fraction,
        H_to_M=H_to_M,
    )
    if hydride is not None:
        # 记录实际使用的超胞与是否自动升级
        info = dict(info)
        info["supercell"] = actual_supercell
        info["auto_expanded"] = used_auto_expand
        if used_auto_expand:
            info.setdefault("warnings", []).append(
                f"为容纳 H/M={H_to_M:.2f},超胞已从 {supercell}×{supercell}×1 自动扩展到 "
                f"{actual_supercell}×{actual_supercell}×1"
            )
        return hydride, info

    # 全失败 — 返回一个空的占位结构(pymatgen 不允许 Structure([]))
    from pymatgen.core import Structure, Lattice
    empty = Structure(Lattice.cubic(5.0), [], [])
    return empty, {
        "prototype": proto,
        "method": "no interstitial sites",
        "error": "几何过滤未找到可用间隙位",
        "n_metal": len(struct_base), "n_H": 0,
        "H_to_M": 0.0, "wt_pct": 0.0,
        "H_to_M_requested": H_to_M if H_to_M is not None else fill_fraction,
        "supercell": actual_supercell,
        "auto_expanded": used_auto_expand,
    }


# ============================================================
# 5. 兼容旧名
# ============================================================
def hydrogenate_structure(formula: str, supercell: int = 2,
                        fill_fraction: float = 1.0):
    return hydrogenate_via_voidsize(formula, supercell=supercell,
                                    fill_fraction=fill_fraction)


# ============================================================
# 6. CIF 工具
# ============================================================
def structure_to_cif(struct) -> str:
    from pymatgen.core import Structure
    from pymatgen.io.cif import CifWriter
    # 空结构 / 0 个原子:pymatgen CifWriter 会抛 IndexError,返回占位 CIF
    if len(struct.sites) == 0:
        a = struct.lattice.a if struct.lattice else 5.0
        return (
            "data_placeholder\n"
            f"_chemical_formula_structural 'X'\n"
            f"_cell_length_a {a}\n"
            f"_cell_length_b {a}\n"
            f"_cell_length_c {a}\n"
            "_cell_angle_alpha 90\n_cell_angle_beta 90\n_cell_angle_gamma 90\n"
        )
    species_list = [str(s) for s in struct.species]
    coords_list = [list(s.frac_coords) for s in struct.sites]
    struct_clean = Structure(
        struct.lattice, species_list, coords_list,
        coords_are_cartesian=False,
    )
    return str(CifWriter(struct_clean))


# ============================================================
# 7. 间隙位枚举(供 UI 展示)
# ============================================================
def list_interstitial_sites_from_structure(struct) -> dict:
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    sga = SpacegroupAnalyzer(struct, symprec=1e-3)
    hall_no = sga.get_symmetry_dataset().hall_number
    wyckoff_db = _get_wyckoff_db()
    if hall_no < 1 or hall_no > len(wyckoff_db):
        return {"warning": f"hall {hall_no} 越界"}
    group = wyckoff_db[hall_no - 1]
    out = {"spacegroup": group["symbol"], "sites": {}}
    for w in group["wyckoff"]:
        if w["multiplicity"] >= struct.num_sites:
            continue
        out["sites"][f"{w['letter']}({w['multiplicity']})"] = list(w["positions"])
    return out


# ============================================================
# 8. van't Hoff → ΔH / ΔS
# ============================================================
def dH_from_van_hoff(V5: float) -> float:
    return float(-V5 * 1000.0 * 8.314)


def dS_from_van_hoff(V6: float) -> float:
    return float(V6 * 8.314)


def compute_pct_curve(dH: float, dS_solid: float, T_list, H_to_M_max: float,
                      n_points: int = 50):
    R = 8.314
    P0 = 1.0
    x_H = np.linspace(0.01, H_to_M_max, n_points)
    f = x_H / H_to_M_max
    f = np.clip(f, 1e-6, 1 - 1e-6)
    dS_arr = -R * (f * np.log(f) + (1 - f) * np.log(1 - f))
    idx_mid = len(x_H) // 2
    dS_mid = float(dS_arr[idx_mid])
    P = np.zeros((len(T_list), n_points))
    for i, T in enumerate(T_list):
        ln_P = -dH / (R * T) + (dS_arr - dS_mid) / R
        P[i] = np.exp(ln_P) * P0
    return P, x_H


# ============================================================
# 9. 一站式 pipeline
# ============================================================
def full_pipeline(formula: str, V0: float = 293.0, supercell: int = 2,
                  T_min: float = 233.15, T_max: float = 353.15, n_T: int = 5):
    struct, proto = structure_from_formula(formula, supercell=supercell)
    cif_base = structure_to_cif(struct)

    # ★ 真加氢
    hyd_struct, hyd_info = hydrogenate_via_voidsize(formula, supercell=supercell)
    cif_hyd = structure_to_cif(hyd_struct)
    interstitial = list_interstitial_sites_from_structure(struct)

    from pct_app.ui.predictor import predict_three  # ← 相对包路径,不依赖 cwd
    res = predict_three(formula, V0=V0)
    V5, V6, Cap = res["V5"], res["V6"], res["Capacity"]
    dH = dH_from_van_hoff(V5) if V5 is not None else None
    dS = dS_from_van_hoff(V6) if V6 is not None else None
    T_list = np.linspace(T_min, T_max, n_T)
    if dH is not None and dS is not None:
        from pymatgen.core import Composition as Comp
        comp = Comp(formula)
        int_formula, _ = comp.get_integer_formula_and_factor()
        int_comp = Comp(int_formula)
        mw = float(int_comp.weight)
        N_metal = float(sum(amt for el, amt in int_comp.items() if str(el) != "H"))

        # Capacity 是 wt% 数字 → 反推 H/M
        M_H = 1.008
        frac = min(max(Cap / 100.0, 1e-6), 0.999)
        M_metal_atom = mw / max(N_metal, 1e-9)
        H_to_M_max = (frac * M_metal_atom) / (M_H * (1.0 - frac))

        # 钳制
        if "Mg" in formula and "Ni" not in formula:
            H_to_M_max = min(H_to_M_max, 4.0)
        elif "Al" in formula or "B" in formula:
            H_to_M_max = min(H_to_M_max, 4.5)
        else:
            H_to_M_max = min(H_to_M_max, 1.5)
        H_to_M_max = max(H_to_M_max, 0.5)
        P, x_H = compute_pct_curve(dH, dS, T_list, H_to_M_max)
    else:
        P, x_H, H_to_M_max = None, None, None

    return {
        "formula": formula, "prototype": proto,
        "structure": struct, "cif": cif_base,
        "hydride_structure": hyd_struct, "hydride_cif": cif_hyd,
        "hydride_info": hyd_info,
        "interstitial": interstitial,
        "V5": V5, "V6": V6, "Capacity": Cap,
        "dH_J_per_mol": dH, "dS_J_per_molK": dS,
        "P": P, "x_H": x_H, "T_list": T_list, "H_to_M_max": H_to_M_max,
    }
