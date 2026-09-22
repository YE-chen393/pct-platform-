# -*- coding: utf-8 -*-
"""
setup_check.py — 跨平台环境验证脚本

检查所有关键依赖是否安装正确、关键路径是否存在、模型是否可加载。
退出码 0 = 一切就绪;非 0 = 需要修复。

用法:
    PYTHONPATH=. python setup_check.py
"""
import sys
import os
import platform
from pathlib import Path

# 让脚本独立运行
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

OK = "✅"
FAIL = "❌"
WARN = "⚠️ "


def check_python():
    print(f"\n=== Python 环境 ===")
    v = sys.version_info
    print(f"  {OK} Python {v.major}.{v.minor}.{v.micro} on {platform.system()}")
    if (v.major, v.minor) < (3, 10):
        print(f"  {FAIL} Python 3.10+ required (当前 {v.major}.{v.minor})")
        return False
    return True


def check_deps():
    print(f"\n=== 核心依赖 ===")
    required = [
        ("gradio",         "Gradio UI"),
        ("pymatgen",       "晶体结构"),
        ("matminer",       "Magpie 特征化"),
        ("pandas",         "数据处理"),
        ("numpy",          "数值计算"),
        ("matplotlib",     "绘图"),
        ("joblib",         "模型加载"),
        ("sklearn",        "scikit-learn (SVR/RF)"),
        ("lightgbm",       "LightGBM (V6)"),
    ]
    failed = []
    for mod, desc in required:
        try:
            __import__(mod)
            print(f"  {OK} {mod:<14} ({desc})")
        except ImportError as e:
            print(f"  {FAIL} {mod:<14} ({desc}) - {e}")
            failed.append(mod)

    optional = [
        ("psutil", "网络接口探测"),
        ("scipy", "SLSQP 优化"),
        ("flask", "REST API"),
        ("flask_cors", "REST API 跨域"),
        ("xgboost", "XGBoost 训练"),
    ]
    for mod, desc in optional:
        try:
            __import__(mod)
            print(f"  {OK} {mod:<14} (可选:{desc})")
        except ImportError:
            print(f"  {WARN} {mod:<14} (可选:{desc}) - 未安装,功能降级)")
    return len(failed) == 0


def check_paths():
    print(f"\n=== 关键路径 ===")
    from pct_app.config.paths import (
        ROOT, MODEL_DIR, DATA_DIR, ASSETS_DIR, VENDOR_DIR,
    )
    items = [
        ("项目根目录",  ROOT,       True),
        ("模型目录",    MODEL_DIR,  True),
        ("数据目录",    DATA_DIR,   True),
        ("资产目录",    ASSETS_DIR, False),  # 运行时自动创建
        ("vendor 目录", VENDOR_DIR, True),
    ]
    for name, p, must_exist in items:
        if p.exists():
            print(f"  {OK} {name:<14} = {p}")
        elif must_exist:
            print(f"  {FAIL} {name:<14} = {p}  (不存在!)")
        else:
            print(f"  {WARN} {name:<14} = {p}  (将自动创建)")
            p.mkdir(parents=True, exist_ok=True)

    # 检查三个模型目录都有 .pkl
    print(f"\n=== 预训练模型 ===")
    targets = {
        "V5":       ("SVR.pkl",         True),
        "V6":       ("LightGBM.pkl",    False),
        "Capacity": ("RandomForest.pkl", False),
    }
    for tgt, (model_file, scaler_required) in targets.items():
        model_dir = MODEL_DIR / tgt
        model_path = model_dir / model_file
        if not model_path.exists():
            # 退到任何可用的 .pkl
            pkls = list(model_dir.glob("*.pkl")) if model_dir.exists() else []
            if pkls:
                print(f"  {WARN} {tgt}: 没找到 {model_file},但有以下 .pkl: {[p.name for p in pkls]}")
            else:
                print(f"  {FAIL} {tgt}: 模型目录 {model_dir} 空,需运行 python train_all.py")
            continue
        print(f"  {OK} {tgt:<10} {model_file} ({model_path.stat().st_size/1024:.1f} KB)")
        if scaler_required:
            scx = model_dir / "SVR_scaler_X.pkl"
            scy = model_dir / "SVR_scaler_y.pkl"
            print(f"    {'✅' if scx.exists() else '❌'} {scx.name}")
            print(f"    {'✅' if scy.exists() else '❌'} {scy.name}")

    # 检查 features.csv
    print(f"\n=== 特征列表 ===")
    for tgt in ("V5", "V6", "Capacity"):
        feat_file = DATA_DIR / tgt / "features.csv"
        if feat_file.exists():
            n = len(feat_file.read_text(encoding="utf-8").splitlines()) - 1
            print(f"  {OK} {tgt:<10} features.csv ({n} features)")
        else:
            print(f"  {FAIL} {tgt:<10} features.csv 缺失")


def check_smoke_test():
    print(f"\n=== 冒烟测试 ===")
    try:
        # 检查导入链
        from pct_app.core import featurize
        from pct_app.core.io import MODEL_REGISTRY
        from pct_app.ui.predictor import predict_three
        print(f"  {OK} pct_app.core.featurize / io / ui.predictor 导入成功")
    except Exception as e:
        print(f"  {FAIL} 导入失败: {e}")
        return False

    try:
        res = predict_three("LaNi5", 293.0)
        print(f"  {OK} predict_three('LaNi5') = V5={res['V5']:.4f}, V6={res['V6']:.4f}, Cap={res['Capacity']:.4f}")
        return True
    except Exception as e:
        print(f"  {FAIL} predict_three 失败: {e}")
        return False


def main():
    print("=" * 60)
    print("  PCT Platform 环境验证")
    print("=" * 60)

    ok_py = check_python()
    ok_dep = check_deps()
    check_paths()
    ok_smoke = check_smoke_test()

    print(f"\n{'=' * 60}")
    if ok_py and ok_dep and ok_smoke:
        print(f"  {OK}  一切就绪!可执行: bash launch.sh")
        return 0
    else:
        print(f"  {FAIL} 环境存在问题,请按上方提示修复")
        if not ok_dep:
            print(f"       → pip install -r requirements.txt")
        if not ok_smoke:
            print(f"       → 检查 PYTHONPATH 或模型文件是否齐全")
        return 1


if __name__ == "__main__":
    sys.exit(main())
