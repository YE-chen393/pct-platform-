"""模型加载层。启动时一次性 load,后续 predict 直接复用。"""

from __future__ import annotations
import pickle
from functools import lru_cache

from ..config.paths import MODEL_DIR, DATA_DIR


@lru_cache(maxsize=8)
def _load(name: str, model_file: str, scaler: bool):
    """加载一个模型 + 配套 scaler + 特征列表。带 lru_cache 避免重复 IO。"""
    with open(MODEL_DIR / name / model_file, "rb") as f:
        m = pickle.load(f)
    scX = scY = None
    if scaler:
        with open(MODEL_DIR / name / "SVR_scaler_X.pkl", "rb") as f:
            scX = pickle.load(f)
        with open(MODEL_DIR / name / "SVR_scaler_y.pkl", "rb") as f:
            scY = pickle.load(f)
    feats_path = DATA_DIR / name / "features.csv"
    # 原 features.csv 格式:列名 + 14 行 feature 名,所以 pd.read_csv + ["feature"] 是正确读法
    import pandas as pd
    feats = pd.read_csv(feats_path)["feature"].tolist()
    return m, scX, scY, feats


# 模型注册表:启动时一次性实例化
MODEL_REGISTRY = {
    "V5":       _load("V5",       "SVR.pkl",         True),
    "V6":       _load("V6",       "LightGBM.pkl",    False),
    "Capacity": _load("Capacity", "RandomForest.pkl", False),
}
