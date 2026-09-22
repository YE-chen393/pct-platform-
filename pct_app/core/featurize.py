"""化学式 → Magpie 特征。"""

from __future__ import annotations
import pandas as pd
from pymatgen.core import Composition
from matminer.featurizers.composition import ElementProperty

# 模块级单例(与原 app.py 一致:启动时 featurize 一次)
MAGPIE = ElementProperty.from_preset("magpie")


def featurize(formula: str) -> tuple[pd.DataFrame, Composition]:
    """对单一化学式做 Magpie 特征化,返回 (特征 DataFrame, Composition 对象)。"""
    comp = Composition(formula)
    feats = MAGPIE.featurize(comp)
    return pd.DataFrame([feats], columns=MAGPIE.feature_labels()), comp
