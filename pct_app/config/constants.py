"""物理常数与默认值"""

DEFAULT_V0 = 293.0
DEFAULT_T_RANGE_K = (233.15, 353.15)
DEFAULT_P_RANGE_BAR = (0.001, 100.0)
PLOT_DPI = 140
PCT_N_POINTS = 80

# 默认 3 条等温线:-10 / 25 / 60 ℃
ISOTHERM_T_LIST_K = [263.15, 298.15, 333.15]

# PhononBench 公开 API
PHONONBENK_URL = "http://phononbench.cn"
PHONONBENK_SUBMIT = f"{PHONONBENK_URL}/api/submit"
PHONONBENK_QUERY = f"{PHONONBENK_URL}/api/status"

# 中文字体(原 app.py 的 matplotlib rcParams 写到这)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
