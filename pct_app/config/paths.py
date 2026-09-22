"""路径常量。所有 IO 都从 ROOT 出发,避免硬编码绝对路径。"""

from pathlib import Path

# ROOT = pct_app 的上一级,也就是 PCT_project/
ROOT = Path(__file__).resolve().parent.parent.parent

MODEL_DIR = ROOT / "models"
DATA_DIR = ROOT / "data"
ASSETS_DIR = ROOT / "assets"
RESULTS_DIR = ROOT / "results"
VENDOR_DIR = ROOT / "vendor"

# 确保 ASSETS_DIR 一定存在(原 app.py 也做了 mkdir)
ASSETS_DIR.mkdir(exist_ok=True)
