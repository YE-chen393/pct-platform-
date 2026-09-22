# PCT Platform Demo · 稀土储氢合金智能预测平台

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Gradio](https://img.shields.io/badge/Gradio-5%2B-orange.svg)](https://gradio.app/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](#license)

> La / Y-Mn-Ni 系稀土储氢合金热力学参数在线预测平台。基于三个预训练模型
> （SVR / LightGBM / RandomForest）+ Magpie 特征 + pymatgen 结构生成。
> 单文件入口 `run.py`,启动即开 Web UI。

---

## 🌐 在线体验（无需部署）

> **直接在浏览器打开下方链接即可使用，无需任何环境配置！**
>
> ### 🎯 在线演示地址
>
> **<https://writer-comic-thirty-lobby.trycloudflare.com>**
>
> 📡 由作者服务器托管，通过 Cloudflare Tunnel 提供 HTTPS 公网访问。
> 任何设备（手机 / 电脑 / 平板）打开即用，与本地启动的体验完全一致。

> ⚠️ **URL 是临时的**：托管服务器重启或隧道断开时，此 URL 会变化或失效。
> 如果链接打不开，你有两个选择：
> 1. **自己部署**（见下方 `🚀 一分钟启动`）— 5 分钟在本机或服务器启动一个永久实例
> 2. **联系服务方** 恢复在线演示（见底部「服务提供方」)
>
> 💡 想要长期稳定的访问？建议在自己机器上部署（一次 5 分钟，享受永久服务）。

---

## 🏫 校园网永久链接（昆明理工大学）

> 🎓 **本校师生专属**：连接 **昆明理工大学校园网 / 校园 WiFi** 后，
> **直接在浏览器打开以下地址即可永久访问**（URL 永远不变，无需外网、无需账号）。
>
> ### 🔗 校内访问地址
>
> **<http://10.102.81.1:7861>**
>
> 📍 由作者实验室服务器 `master`（IP: `10.102.81.1`，端口 `7861`）直接提供。
> 只要服务器开机 + 应用运行，校内任何终端（电脑 / 平板 / 手机连校园 WiFi）都能访问。

### ✅ 使用方法

1. **连接校园网**：有线网、校园 WiFi（`KMUST-WiFi` / `KMUST-Auto` 等）均可
2. **浏览器打开**：<http://10.102.81.1:7861>
3. **开始使用**：与在线演示体验一致

### ❌ 校外用户

此地址仅限校园网内可访问。如在校外，请使用顶部 [「🌐 在线体验」](#-在线体验无需部署) 中的公网 URL，或自行部署。

> 💬 服务器运行状态 / 校内访问问题请联系服务方（见底部「📡 服务提供方」）。

---

## ✨ 核心功能

- 🎯 **单组份预测**:输入化学式 → 自动获得 V5 / V6 / Capacity / 25℃ 平台压 / van't Hoff / P-T / PCT 等温曲线
- 📊 **批量筛选**:上传 CSV → 数百条材料一次性预测 → 按 V5/V6/Capacity 范围筛选 → 导出 CSV
- 🧪 **组份空间设计器**:周期表点选元素 → 自动生成 AB5 / A2B7 / AB3 / AB2 候选化学式 → 一键送入批量预测
- 🔬 **CIF 结构生成**:pymatgen 结构原型 + 加氢(Wyckoff CSV + 几何过滤)
- 📚 **历史任务管理**:每次批量预测自动归档到 `assets/jobs/<job_id>/`,支持下载 / 删除
- 🌍 **零配置部署**:所有路径用 `pathlib` 相对解析,不依赖任何机器特定目录

---

## 🚀 一分钟启动

### 1. 克隆 & 安装依赖

```bash
git clone <your-github-repo-url>.git
cd PCT_project

# 推荐:虚拟环境
python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 启动 Gradio UI

```bash
bash launch.sh                      # 自动检测 Python + 端口 7861
# 或:
python run.py                       # 直接用当前 python
# 或:
python run.py --share               # 72 小时公网分享链接
```

启动后浏览器打开 **<http://127.0.0.1:7861>**,首次加载会编译 Magpie 特征器(几秒)。

> 想自定义端口?`PCT_PORT=8080 bash launch.sh`

---

## 📂 项目结构

```
PCT_project/
├── run.py                          # ⭐ 主入口 (Gradio UI)
├── launch.sh                       # 一键启动脚本 (自动检测 Python)
├── requirements.txt                # pip 依赖
├── app.py                          # 兼容 shim,允许 `python app.py`
├── predict_new_material.py         # 单点预测 CLI 示例
├── train_all.py                    # 重训三模型(可选)
├── make_notebooks.py               # 生成 Jupyter Notebook(可选)
│
├── pct_app/                        # 项目本体(可作为 Python 包使用)
│   ├── config/
│   │   ├── paths.py                # ROOT / MODEL_DIR / DATA_DIR / ASSETS_DIR
│   │   └── constants.py            # 默认 V0 / T 范围 / DPI
│   ├── core/                       # 纯计算 + IO(无 gradio 依赖)
│   │   ├── featurize.py            # 化学式 → Magpie 特征
│   │   ├── io.py                   # 模型加载 + MODEL_REGISTRY
│   │   ├── plots.py                # van't Hoff / P-T / PCT 曲线
│   │   ├── thermodynamics.py       # H/M ↔ wt% 换算
│   │   ├── structures.py           # CIF 生成 + 加氢
│   │   ├── batch_predict.py        # 异步批量预测
│   │   └── task_queue.py           # 任务队列(TaskStore + TaskExecutor)
│   ├── api.py                      # 可选 Flask REST API
│   └── ui/                         # Gradio UI 层
│       ├── app.py                  # 顶层组装
│       ├── single.py               # 单组份 Tab
│       ├── batch.py                # 批量 Tab
│       ├── composition_space.py    # 周期表点选
│       └── css.py / hero.py / predictor.py
│
├── models/                         # 预训练 joblib 模型(直接推上 GitHub)
│   ├── V5/SVR.pkl + SVR_scaler_*.pkl
│   ├── V6/LightGBM.pkl
│   └── Capacity/RandomForest.pkl
│
├── data/                           # 训练数据 + features.csv
│   ├── V5/, V6/, Capacity/
│
├── vendor/                         # 第三方工具
│   ├── pct_toolkit_wrapper.py      # PCT-Simulation-Toolkit wrapper
│   ├── PCT_Toolkit/                # 官方 PHannapp/PCT-Simulation-Toolkit
│   └── MongoDB/                    # Stub: read.py 顶层 import 占位
│
├── assets/                         # 运行时生成(已 gitignored)
│   ├── *.png, *.cif                #   绘图 + 结构 CIF
│   └── jobs/<job_id>/              #   批量任务历史
│
├── scripts/                        # 运维脚本
│   ├── pct_service.sh              # PID 管理
│   ├── pct_public.sh               # Cloudflare Tunnel 公网发布
│   └── README.md
│
├── docs/                           # V5/V6/Capacity 训练报告
│
├── .gitignore                      # GitHub 友好:排除缓存 / 临时 / 任务历史
└── README.md                       # 本文件
```

---

## 🔧 依赖说明

`requirements.txt` 列出的核心包:

| 包 | 版本 | 用途 |
|---|---|---|
| `gradio` | ≥5.0 | Web UI 框架 |
| `pymatgen` | ≥2024.1 | 晶体结构 / 化学式解析 |
| `matminer` | ≥0.9 | Magpie 元素特征化 |
| `scikit-learn` | ≥1.3 | SVR / RandomForest + scaler |
| `lightgbm` | ≥4.0 | V6 模型 |
| `pandas`, `numpy`, `matplotlib` | - | 数据 + 绘图 |
| `requests`, `tqdm`, `joblib` | - | 辅助 |

**可选**:`flask`, `flask-cors`(REST API), `psutil`(网络接口探测), `scipy`(SLSQP 备用算法)。

> 如果 `pip install` 之后 import 报错 `ModuleNotFoundError`,请检查是否在同一个虚拟环境里。

---

## 🧪 验证安装

启动后,在浏览器里:
1. **单组份 Tab**:点示例按钮 "LaNi5 [AB5]" → 应在 2~3 秒内看到 4 个 metric + 3 张图 + 1 个 CIF 文件
2. **批量 Tab**:点 "📤 送入批量预测"(已点选周期表)→ 应能下载 CSV + 看到分布图
3. **CLI 验证**:
   ```bash
   PYTHONPATH=. python -c "
   from pct_app.ui.predictor import predict_three
   print(predict_three('LaNi5', 293.0))
   "
   ```

---

## 🌍 跨平台 / 容器部署

### Docker(示例)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 7861
ENV PYTHONPATH=/app
CMD ["python", "run.py", "--server-name", "0.0.0.0", "--server-port", "7861"]
```

```bash
docker build -t pct-platform .
docker run -p 7861:7861 pct-platform
```

### 公网临时分享(零账号)

```bash
bash scripts/pct_public.sh start    # 自动下载 cloudflared + 建隧道
bash scripts/pct_public.sh status   # 查看公网 URL
bash scripts/pct_public.sh stop     # 停止
```

72 小时临时 HTTPS 链接(`https://xxx.trycloudflare.com`)可直接发给任何人。

---

## 🧱 模块依赖图

```
config                  # 路径 + 常量(ROOT 自动以 pct_app/ 位置为基准)
  ↑
core/{featurize,io,thermodynamics}
  ↑          ↘
core/{predictor, plots, structures, batch_predict, task_queue}
  ↑
ui/{css, hero, single, batch, app}
  ↑
run.py / app.py
```

- `core/*` **不**依赖 gradio,可单独 import 做脚本/Notebook
- `ui/*` 只 `from pct_app.core import ...`,不反向依赖

---

## 📝 重训模型(可选)

如需重新训练三个模型:

```bash
python train_all.py                  # 全部重训
python make_notebooks.py             # 配套生成 4 个 Jupyter Notebook
```

输出:
- `models/{V5,V6,Capacity}/*.pkl` + scaler
- `results/figures/fig_*.png`
- `results/tables/metrics_*.csv`
- `docs/{V5,V6,Capacity}_report.md`

---

## ❓ FAQ

### Q: 启动后报 `ModuleNotFoundError: No module named 'pct_app'`
A: 请用 `bash launch.sh` 或 `PYTHONPATH=. python run.py`,或在 IDE 里把项目根目录标记为 Sources Root。

### Q: `vendor/pct_toolkit_wrapper.full_pipeline` 报 `from app import predict_three` 失败
A: 这个问题在 v0.3.0 已修复(改为 `from pct_app.ui.predictor import predict_three`)。如果你 fork 的是旧版本,请更新 `vendor/pct_toolkit_wrapper.py`。

### Q: 模型文件太大推不上 GitHub?
A: 单个 pkl 在 0.5~2 MB,三个加起来 ~15 MB,GitHub 单文件 100 MB 限制完全够。如果想更精简,可用 [Git LFS](https://git-lfs.github.com/)。

### Q: 想换一批材料重新训练?
A: 把 CSV 放到 `data/<Target>/{features.csv,X_train.csv,X_val.csv,X_test.csv,y_train.csv,y_val.csv,y_test.csv}`,然后 `python train_all.py`。每个 y CSV 一列名为 `target`。

---

## 📄 License

MIT License — 详见 `LICENSE`。

## 📡 服务提供方

本仓库 README 中的「在线演示地址」由原作者服务器托管。如需：
- 申请恢复 / 重启在线演示
- 报告在线演示不可用
- 咨询私有部署 / 模型定制 / 数据集合作

联系方式（任选其一）：
- **邮箱**：[nkdudx29387o@outlook.com](mailto:nkdudx29387o@outlook.com)
- **GitHub Issues**：[YE-chen393/pct-platform-](https://github.com/YE-chen393/pct-platform-/issues)

---

## 🙏 致谢

- [pymatgen](https://pymatgen.org/) — 材料学 Python 生态
- [matminer](https://hackingmaterials.lbl.gov/matminer/) — 特征化
- [Gradio](https://gradio.app/) — ML Demo Web UI
- [PHannapp/PCT-Simulation-Toolkit](https://github.com/PHannapp/PCT-Simulation-Toolkit) — 加氢结构生成
