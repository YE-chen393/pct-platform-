# -*- coding: utf-8 -*-
"""
预测新材料 La0.1Y0.9Mn4Ni1 的 V5、V6、Capacity

这是一个独立的 CLI 演示,展示如何复用 pct_app 的核心模块做单点预测。

用法:
    PYTHONPATH=. python predict_new_material.py
或者:
    python -m predict_new_material
"""
import sys
from pathlib import Path

# 让 pct_app 包可见(脚本独立运行时)
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import numpy as np

from pct_app.config.paths import MODEL_DIR, DATA_DIR, ROOT
from pct_app.core.featurize import featurize
from pct_app.core.io import _load
from pct_app.ui.predictor import predict_three

# ===== 1. 解析材料成分 =====
formula = "La0.1Y0.9Mn4Ni1"
print("=" * 60)
print(f"预测材料: {formula}")
print("=" * 60)

res = predict_three(formula, V0=293.0)
print(f"V5       (van't Hoff 斜率,kK)     = {res['V5']:.6f}")
print(f"V6       (van't Hoff 截距)          = {res['V6']:.6f}")
print(f"Capacity (mol/kg)                  = {res['Capacity']:.6f}")
print(f"P_298K  (MPa)                      = {res['P_298K']:.6e}")

if res["warnings"]:
    print("\n⚠️ 警告:")
    for w in res["warnings"]:
        print(f"   - {w}")

print("\n📌 说明:")
print("  V5 和 V6 为 van't Hoff 拟合的无量纲相对值")
print(f"  Capacity 单位为 mol/kg;脚本根目录 = {ROOT}")
