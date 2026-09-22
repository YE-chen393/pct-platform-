# 安装指南 / Installation Guide

## 系统要求

- **Python**: 3.10 或更高(推荐 3.11)
- **操作系统**: Linux / macOS / Windows
- **内存**: ≥ 4 GB(Magpie 特征器首次加载需 ~500 MB)
- **磁盘**: ≥ 500 MB(模型 + 依赖)

## Linux / macOS 安装

```bash
# 1. 克隆代码
git clone <your-github-repo-url>.git
cd PCT_project

# 2. (推荐)创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 3. 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 4. 验证环境
python setup_check.py

# 5. 启动
bash launch.sh
```

## Windows 安装

```powershell
# 1. 克隆代码(在 Git Bash 或 PowerShell)
git clone <your-github-repo-url>.git
cd PCT_project

# 2. 创建虚拟环境
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 4. 验证
python setup_check.py

# 5. 启动
bash launch.sh
# 或者直接:
python run.py
```

## 常见问题

### 1. `pip install matminer` 失败

matminer 依赖较多科学计算包。如果安装失败,试试:
```bash
pip install --only-binary=:all: matminer
# 或先安装 numpy / pandas 再装 matminer
pip install numpy pandas pymatgen
pip install matminer
```

### 2. 启动报 `ModuleNotFoundError: No module named 'pct_app'`

**原因**:Python 找不到 `pct_app/` 包。

**解决**(任选其一):
- 使用 `bash launch.sh` / `bash scripts/pct_service.sh start`(自动设置 PYTHONPATH)
- 手动:`PYTHONPATH=$PWD python run.py` (macOS/Linux)
- 在 IDE 里把项目根目录标记为 Sources Root

### 3. Windows 下报 `bash: command not found`

Git Bash 或 WSL 自带 bash。如果没有:
```powershell
# 直接用 Python 启动
python run.py

# 或者用 cmd 写个等价脚本
set PYTHONPATH=%CD%
python run.py
```

### 4. 端口 7861 被占用

```bash
# Linux/macOS
lsof -i :7861
# 杀掉占用进程
kill -9 <PID>

# 或者换端口
PCT_PORT=8080 bash launch.sh
```

### 5. matplotlib 中文乱码

平台已设置 `WenQuanYi Micro Hei` / `SimHei` 字体回退链。如果还是乱码,系统需要安装:
```bash
# Debian/Ubuntu
sudo apt-get install fonts-wqy-microhei fonts-noto-cjk

# macOS
# 系统自带 PingFang,会自动使用

# Windows
# 系统自带 SimHei / 微软雅黑,会自动使用
```

## Docker 部署

详见 [README.md](README.md#docker部署示例) 的 Docker 章节。

## 性能调优(可选)

启动脚本会调 `demo.max_threads = 1` 防 SSE 重连闪烁。如果你想跑批量预测并发:
- 修改 `pct_app/ui/app.py` 里的 `demo.max_threads`
- 或直接 `python run.py --server-name 0.0.0.0` 让多用户并行访问
