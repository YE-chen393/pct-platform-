"""批量预测 Tab — 分层流水线设计。

4 层结构(从外到内):

  Step 1 上传 & 预览
    → Step 2 配置 & 触发
      → Step 3 实时进度(逐条处理)
        → Step 4 分层结果(摘要 / 分布 / 表格 / 下载)
"""

from __future__ import annotations
import gradio as gr
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import uuid
import io
from pathlib import Path as _Path

from ..config.paths import ASSETS_DIR
from ..core.task_queue import create_batch_task, get_task_status, TaskStatus
from .predictor import predict_three
from .composition_space import (
    build_periodic_table_ui,
    generate_compositions,
    RARE_EARTH_ELEMENTS,
)


_STEP_TPL = """
<div class="pct-step pct-step-{idx}">
  <div class="pct-step-bar"></div>
  <div class="pct-step-head">
    <span class="pct-step-num">{idx}</span>
    <span class="pct-step-icon">{icon}</span>
    <span class="pct-step-title">{title}</span>
    <span class="pct-step-status">●  待执行</span>
  </div>
  <div class="pct-step-body">
    {body}
  </div>
</div>
"""


def _step(idx: int, icon: str, title: str, body: str = "") -> str:
    return _STEP_TPL.format(idx=idx, icon=icon, title=title, body=body)


# ============================================================
# 分布图生成
# ============================================================
def _save_batch_plot(result_df: pd.DataFrame, success_n: int) -> str:
    """批量预测后的两图汇总: P(25℃) 分布 + ΔH-P 散点。"""
    P_valid = result_df["P (25℃) bar"].dropna().values

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

    ax = axes[0]
    if len(P_valid):
        logP = np.log10(P_valid)
        bins = np.linspace(logP.min() - 0.2, logP.max() + 0.2, 18)
        ax.hist(logP, bins=bins, color="#6366f1", alpha=0.78,
                edgecolor="white", lw=1.2)
        ax.axvline(0.0, color="#ef4444", ls="--", lw=1.2, label="1 bar")
        ax.axvline(1.0, color="#f59e0b", ls="--", lw=1.2, label="10 bar")
        ax.axvspan(0.0, 1.0, color="#10b981", alpha=0.08,
                   label="实用区间 (0.1~10 bar)")
        ax.set_xlabel("log₁₀ P₂₅℃ / bar", fontsize=11)
        ax.set_ylabel("Count", fontsize=11)
        ax.set_title(f"室温平台压分布  (n={success_n})",
                     fontsize=12, fontweight="bold")
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(alpha=0.3)
    else:
        ax.text(0.5, 0.5, "无有效数据", ha="center", va="center",
                transform=ax.transAxes)
        ax.set_axis_off()

    ax = axes[1]
    dH_valid = result_df["ΔH (kJ/mol H₂)"].values
    if len(P_valid):
        mask = ~(np.isnan(dH_valid) | np.isnan(P_valid))
        ax.scatter(dH_valid[mask], P_valid[mask],
                   s=55, c="#8b5cf6", alpha=0.78, edgecolor="white", lw=1.2)
        ax.axhline(1.0, color="#ef4444", ls="--", lw=1, alpha=0.5)
        ax.axhline(10.0, color="#f59e0b", ls="--", lw=1, alpha=0.5)
        ax.set_yscale("log")
        ax.set_xlabel("ΔH / (kJ/mol H₂)", fontsize=11)
        ax.set_ylabel("P₂₅℃ / bar  (log)", fontsize=11)
        ax.set_title("ΔH — P₂₅℃ 散点", fontsize=12, fontweight="bold")
        ax.grid(alpha=0.3)
    else:
        ax.text(0.5, 0.5, "无有效数据", ha="center", va="center",
                transform=ax.transAxes)
        ax.set_axis_off()

    fig.tight_layout()
    plot_path = str(ASSETS_DIR / "batch_summary.png")
    fig.savefig(plot_path, dpi=140)
    plt.close(fig)
    return plot_path


# ============================================================
# 任务文件夹管理
# ============================================================
from ..core.task_queue import create_batch_task, get_task_status, TaskStatus, TASK_STORE

# 任务根目录: 每个任务一个独立文件夹
_JOBS_ROOT = ASSETS_DIR / "jobs"
_JOBS_ROOT.mkdir(parents=True, exist_ok=True)


def list_jobs() -> list[dict]:
    """枚举所有任务文件夹(从磁盘读取),按 job_id 倒序。

    每个 dict 包含:
      - job_id
      - path  (绝对路径)
      - mtime (文件夹修改时间,ISO 格式)
      - has_plot, has_csv, has_filtered (bool)
      - n_csv (完整 CSV 行数,可空)
    """
    import json as _json
    import os
    jobs = []
    if not _JOBS_ROOT.exists():
        return jobs
    for p in sorted(_JOBS_ROOT.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if not p.is_dir():
            continue
        meta_file = p / "summary.json"
        meta = {}
        if meta_file.exists():
            try:
                meta = _json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                meta = {}
        jobs.append({
            "job_id": p.name,
            "path": str(p),
            "mtime": meta.get("end_time") or "",
            "total": meta.get("total", 0),
            "success_n": meta.get("success_count", 0),
            "fail_n": meta.get("fail_count", 0),
            "has_csv": (p / "predictions.csv").exists(),
            "has_filtered_csv": (p / "predictions_filtered.csv").exists(),
            "has_plot": (p / "summary.png").exists(),
        })
    return jobs


def pack_job_zip(job_id: str) -> str | None:
    """把一个任务文件夹打成 zip,返回 zip 路径。"""
    import zipfile, shutil
    src = _JOBS_ROOT / job_id
    if not src.exists():
        return None
    zip_path = ASSETS_DIR / f"job_{job_id}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in src.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(src))
    return str(zip_path)


def delete_job(job_id: str) -> bool:
    """删除任务文件夹(及同名 zip)。返回是否删除成功。"""
    import shutil
    if not job_id or not all(c.isalnum() or c == "-" for c in job_id):
        # 防止路径穿越
        return False
    src = _JOBS_ROOT / job_id
    ok = False
    if src.exists():
        shutil.rmtree(src, ignore_errors=True)
        ok = True
    zip_path = ASSETS_DIR / f"job_{job_id}.zip"
    if zip_path.exists():
        zip_path.unlink()
        ok = True
    return ok


def _render_jobs_html(jobs: list[dict]) -> str:
    """把 jobs 列表渲染成 HTML(每行一个历史任务的卡片)。"""
    if not jobs:
        return """
        <div class="pct-empty-state">
          <div class="pct-empty-icon">📭</div>
          <div class="pct-empty-title">暂无历史任务</div>
          <div class="pct-empty-hint">完成一次批量预测后,任务会自动列在这里</div>
        </div>"""

    rows = []
    for j in jobs:
        chip_csv = "<span class='pct-chip-ok'>✓ CSV</span>" if j["has_csv"] else ""
        chip_filt = "<span class='pct-chip-info'>✓ 过滤</span>" if j["has_filtered_csv"] else ""
        chip_plot = "<span class='pct-chip-warn'>✓ 图</span>" if j["has_plot"] else ""
        chips = " ".join(c for c in [chip_csv, chip_filt, chip_plot] if c) or "<span style='color:#94a3b8;font-size:11px;'>空</span>"
        mtime = j["mtime"][:19].replace("T", " ") if j["mtime"] else "—"
        rows.append(f"""
        <div class="pct-job-row" data-job-id="{j['job_id']}">
          <div class="pct-job-row-head">
            <code class="pct-job-id-tag">📋 {j['job_id']}</code>
            <span class="pct-job-mtime">{mtime}</span>
          </div>
          <div class="pct-job-row-body">
            <span class="pct-meta-label">总</span> <b>{j['total']}</b>
            &nbsp;·&nbsp;
            <span class="pct-meta-label" style="color:#10b981;">成功</span> <b>{j['success_n']}</b>
            &nbsp;·&nbsp;
            <span class="pct-meta-label" style="color:#ef4444;">失败</span> <b>{j['fail_n']}</b>
          </div>
          <div class="pct-job-row-chips">{chips}</div>
          <div class="pct-job-row-actions">
            <a href="/file={j['path']}/predictions.csv" target="_blank"
               class="pct-job-link" {"disabled" if not j['has_csv'] else ""}>📥 完整 CSV</a>
            <a href="/file={j['path']}/predictions_filtered.csv" target="_blank"
               class="pct-job-link" {"disabled" if not j['has_filtered_csv'] else ""}>🔍 过滤 CSV</a>
            <a href="/file={j['path']}/summary.png" target="_blank"
               class="pct-job-link" {"disabled" if not j['has_plot'] else ""}>📈 图</a>
          </div>
        </div>""")

    return f"""
    <div class="pct-jobs-wrap">
      {''.join(rows)}
    </div>
    """


# ============================================================
# 批量预测入口
# ============================================================
def predict_batch(file_obj,
                 filt_V5_min: float, filt_V5_max: float,
                 filt_V6_min: float, filt_V6_max: float,
                 filt_Cap_min: float, filt_Cap_max: float,
                 job_id_input: str = "",
                 custom_job_name: str = "",
                 batch_V0: float = 293.0,
                 progress=gr.Progress()):
    """
    批量预测:四阶段流水线 + 实时 V5/V6/Capacity 范围过滤。
    
    新增功能（借鉴自程序开发项目）:
    - 任务ID跟踪: 每个批量任务生成唯一8位ID
    - 实时状态: 通过 job_id_input 组件显示当前任务ID
    - 历史查询: 用户可输入历史任务ID查询进度
    """
    # Guard progress against None (when called outside Gradio)
    def _p(step: float, desc: str = "") -> None:
        if progress is not None:
            progress(step, desc=desc)

    # ===== 任务ID管理 =====
    current_job_id = job_id_input.strip() if job_id_input else None
    
    # 如果用户输入了历史任务ID，尝试查询
    if current_job_id and len(current_job_id) == 8:
        task_info = get_task_status(current_job_id)
        if task_info:
            return _build_task_status_response(task_info, filt_V5_min, filt_V5_max,
                                              filt_V6_min, filt_V6_max,
                                              filt_Cap_min, filt_Cap_max)
    
    if file_obj is None:
        return (
            None,
            "<div class='pct-empty-state pct-empty-state-error'>"
            "<div class='pct-empty-icon'>📁</div>"
            "<div class='pct-empty-title'>未上传文件</div>"
            "<div class='pct-empty-hint'>请先在 Step 1 上传 CSV 文件</div>"
            "</div>",
            None, None, None, None,
        )

    try:
        df = pd.read_csv(file_obj.name)
    except Exception as e:
        return (
            None,
            f"<div class='pct-empty-state pct-empty-state-error'>"
            f"<div class='pct-empty-icon'>❌</div>"
            f"<div class='pct-empty-title'>读取 CSV 失败</div>"
            f"<div class='pct-empty-hint'>{e}</div>"
            f"</div>",
            None, None, None, None,
        )

    if "formula" not in df.columns:
        return (
            None,
            "<div class='pct-empty-state pct-empty-state-error'>"
            "<div class='pct-empty-icon'>⚠️</div>"
            "<div class='pct-empty-title'>CSV 缺 formula 列</div>"
            "<div class='pct-empty-hint'>"
            "必须包含 <code>formula</code> 列,可选 <code>V0</code> / "
            "<code>name</code> / <code>note</code> 等透传列"
            "</div></div>",
            None, None, None, None,
        )

    # ===== 创建新任务 =====
    passthrough_cols = [c for c in df.columns if c not in ("formula", "V0")]
    has_V0 = "V0" in df.columns
    formulas = df["formula"].astype(str).tolist()
    n = len(formulas)

    if n == 0:
        return None, (
            "<div class='pct-empty-state pct-empty-state-error'>"
            "<div class='pct-empty-icon'>📭</div>"
            "<div class='pct-empty-title'>CSV 没有有效行</div>"
            "<div class='pct-empty-hint'>请检查 CSV 内容</div></div>"
        ), None, None, None, None

    # 生成任务ID — 优先使用用户自定义名称,否则用 UUID
    if custom_job_name and custom_job_name.strip():
        # 用户命名:只用小写字母/数字/下划线/连字符
        safe_name = "".join(c.lower() for c in custom_job_name.strip() if c.isalnum() or c in ("_", "-"))
        if safe_name and len(safe_name) >= 2:
            current_job_id = safe_name[:16]  # 限制长度
        else:
            current_job_id = str(uuid.uuid4())[:8]
    else:
        current_job_id = str(uuid.uuid4())[:8]
    # 创建任务专属文件夹
    job_dir = _JOBS_ROOT / current_job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # 写 params.json (任务的输入参数)
    import json as _json
    params = {
        "job_id": current_job_id,
        "start_time": str(__import__("datetime").datetime.now()),
        "input_file": getattr(file_obj, "name", None),
        "filter_V5": [filt_V5_min, filt_V5_max],
        "filter_V6": [filt_V6_min, filt_V6_max],
        "filter_Capacity": [filt_Cap_min, filt_Cap_max],
        "total": n,
    }
    (job_dir / "params.json").write_text(
        _json.dumps(params, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _p(0.01, desc=f"📋 任务ID: {current_job_id} · 准备预测 {n} 个材料...")

    rows = []
    success_count = 0
    fail_count = 0
    
    for i, formula in enumerate(formulas):
        # 每个材料分配 0.05 ~ 0.90 的进度,留 10% 给汇总
        p = 0.05 + 0.85 * (i / n)
        _p(p, desc=f"📋 {current_job_id} · {i+1}/{n} 预测 {formula}")

        V0 = float(df["V0"].iloc[i]) if has_V0 else float(batch_V0)
        try:
            res = predict_three(formula, V0=V0)
            row = {
                "formula":            formula,
                "V5":                 res["V5"],
                "V6":                 res["V6"],
                "ΔH (kJ/mol H₂)":    (-res["V5"] * 1000 * 8.314 / 1000.0)
                                     if res["V5"] is not None else None,
                "ΔS (J/mol·K)":      (res["V6"] * 8.314)
                                     if res["V6"] is not None else None,
                "Capacity (mol/kg)":  res["Capacity"],
                "P (25℃) bar":       res["P_298K"],
            }
        except Exception as e:
            row = {
                "formula":            formula,
                "V5":                 None, "V6":                 None,
                "ΔH (kJ/mol H₂)":    None, "ΔS (J/mol·K)":      None,
                "Capacity (mol/kg)":  None, "P (25℃) bar":       None,
                "_error":             str(e),
            }
            fail_count += 1
        for c in passthrough_cols:
            row[c] = df[c].iloc[i]
        rows.append(row)
        if row.get("V5") is not None:
            success_count += 1

    _p(0.92, desc="⚙️  阶段 3/4 · 汇总统计 ...")
    result_df = pd.DataFrame(rows)
    if "_error" in result_df.columns:
        errs = result_df.pop("_error")
        result_df["_error"] = errs

    success_n = int(result_df["V5"].notna().sum())
    fail_n = n - success_n
    P_valid = result_df["P (25℃) bar"].dropna().values
    in_band_n = int(((P_valid >= 0.1) & (P_valid <= 10.0)).sum()) if len(P_valid) else 0

    # ===== 任务状态记录 =====
    task_record = {
        "job_id": current_job_id,
        "total": n,
        "processed": n,
        "success_count": success_n,
        "fail_count": fail_n,
        "output_dir": str(job_dir),
    }

    # ===== 阶段 4:输出(分层摘要 + 分布图 + 表格 + CSV) =====
    summary_md = (
        f"### 📋 任务ID: `{current_job_id}`  ·  批量预测完成\n\n"
        f"<div class='pct-metric-grid'>"
        f"<div class='pct-metric pct-metric-total'>"
        f"<div class='pct-metric-label'>总材料数</div>"
        f"<div class='pct-metric-value'>{n}</div></div>"
        f"<div class='pct-metric pct-metric-ok'>"
        f"<div class='pct-metric-label'>预测成功</div>"
        f"<div class='pct-metric-value'>{success_n}</div></div>"
        f"<div class='pct-metric pct-metric-fail'>"
        f"<div class='pct-metric-label'>预测失败</div>"
        f"<div class='pct-metric-value'>{fail_n}</div></div>"
        f"<div class='pct-metric pct-metric-hit'>"
        f"<div class='pct-metric-label'>实用区间命中</div>"
        f"<div class='pct-metric-value'>{in_band_n}</div>"
        f"<div class='pct-metric-sub'>0.1 ~ 10 bar</div></div>"
        f"</div>\n"
    )
    summary_md += (
        f"<div class='pct-job-id-box'>"
        f"<span class='pct-job-id-label'>📎 任务ID (可复制查询)</span>"
        f"<code class='pct-job-id'>{current_job_id}</code>"
        f"</div>\n"
    )
    summary_md += (
        f"<div class='pct-folder-hint'>"
        f"💾 所有结果已保存到: <code>assets/jobs/{current_job_id}/</code>"
        f"</div>\n"
    )
    if len(P_valid):
        summary_md += (
            f"<div class='pct-range'>"
            f"<b>P₂₅℃ 范围</b>  "
            f"{float(P_valid.min()):.2e}  ~  {float(P_valid.max()):.2e} bar"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;"
            f"<b>中位数</b>  {float(np.median(P_valid)):.2e} bar"
            f"</div>\n"
        )
    if fail_n:
        summary_md += "\n⚠️ 部分材料预测失败,详见结果表 `_error` 列。\n"

    plot_path = ""
    try:
        _p(0.95, desc="📈  阶段 4/4 · 绘制分布图 ...")
        # 把分布图写到任务专属文件夹
        job_plot_path = job_dir / "summary.png"
        plot_path = str(_save_batch_plot_to(result_df, success_n, str(job_plot_path)))
    except Exception as e:
        summary_md += f"\n\n⚠️ 分布图生成失败:{e}\n"

    # ===== 阶段 4:过滤 + 输出(分层摘要 + 分布图 + 表格 + CSV) =====
    # 应用 V5 / V6 / Capacity 范围过滤
    mask = pd.Series(True, index=result_df.index)
    v5_col = result_df["V5"]
    v6_col = result_df["V6"]
    cap_col = result_df["Capacity (mol/kg)"]

    if v5_col.notna().any():
        mask &= ((v5_col.isna()) | (v5_col >= filt_V5_min) & (v5_col <= filt_V5_max))
    if v6_col.notna().any():
        mask &= ((v6_col.isna()) | (v6_col >= filt_V6_min) & (v6_col <= filt_V6_max))
    if cap_col.notna().any():
        mask &= ((cap_col.isna()) | (cap_col >= filt_Cap_min) & (cap_col <= filt_Cap_max))

    filtered_n = int(mask.sum())
    filtered_df = result_df[mask].copy()
    out_csv = job_dir / "predictions.csv"           # 任务专属完整 CSV
    out_csv_filtered = job_dir / "predictions_filtered.csv"  # 任务专属过滤 CSV

    # 补充过滤统计
    summary_md += (
        f"<div class='pct-metric-grid'>"
        f"<div class='pct-metric pct-metric-total'>"
        f"<div class='pct-metric-label'>过滤后材料数</div>"
        f"<div class='pct-metric-value'>{filtered_n}</div></div>"
        f"<div class='pct-metric pct-metric-ok'>"
        f"<div class='pct-metric-label'>V5 范围</div>"
        f"<div class='pct-metric-sub'>{filt_V5_min:.4f} ~ {filt_V5_max:.4f}</div></div>"
        f"<div class='pct-metric pct-metric-ok'>"
        f"<div class='pct-metric-label'>V6 范围</div>"
        f"<div class='pct-metric-sub'>{filt_V6_min:.4f} ~ {filt_V6_max:.4f}</div></div>"
        f"<div class='pct-metric pct-metric-ok'>"
        f"<div class='pct-metric-label'>Capacity 范围</div>"
        f"<div class='pct-metric-sub'>{filt_Cap_min:.3f} ~ {filt_Cap_max:.3f}</div></div>"
        f"</div>\n"
    )

    # 写完整 CSV 和过滤后 CSV (写到任务文件夹)
    try:
        result_df.to_csv(out_csv, index=False, encoding="utf-8-sig")
        csv_path = str(out_csv)
    except Exception as e:
        summary_md += f"\n\n⚠️ CSV 写出失败:{e}\n"
        csv_path = ""

    try:
        filtered_df.to_csv(out_csv_filtered, index=False, encoding="utf-8-sig")
        filtered_csv_path = str(out_csv_filtered)
    except Exception as e:
        summary_md += f"\n\n⚠️ 过滤 CSV 写出失败:{e}\n"
        filtered_csv_path = ""

    # 写 summary.json (供历史任务面板读取)
    try:
        import json as _json2
        summary_obj = {
            "job_id": current_job_id,
            "total": n,
            "processed": n,
            "success_count": success_n,
            "fail_count": fail_n,
            "filtered_count": filtered_n,
            "in_band_count": in_band_n,
            "P_min": float(P_valid.min()) if len(P_valid) else None,
            "P_max": float(P_valid.max()) if len(P_valid) else None,
            "P_median": float(np.median(P_valid)) if len(P_valid) else None,
            "start_time": params["start_time"],
            "end_time": str(__import__("datetime").datetime.now()),
            "input_file": params["input_file"],
            "filter_V5": [filt_V5_min, filt_V5_max],
            "filter_V6": [filt_V6_min, filt_V6_max],
            "filter_Capacity": [filt_Cap_min, filt_Cap_max],
        }
        (job_dir / "summary.json").write_text(
            _json2.dumps(summary_obj, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        # 同时打包 ZIP 到 assets/ 顶层
        try:
            zip_p = pack_job_zip(current_job_id)
        except Exception:
            zip_p = None
    except Exception as e:
        summary_md += f"\n\n⚠️ summary.json 写入失败:{e}\n"
        zip_p = None

    _p(1.0, desc="✅  全部完成")
    # CSV 和过滤 CSV 也对外提供顶层 ZIP 下载
    return (
        filtered_df, summary_md, plot_path or None,
        csv_path or None, filtered_csv_path or None, current_job_id,
    )


def _save_batch_plot_to(result_df: pd.DataFrame, success_n: int, output_path: str) -> str:
    """与 _save_batch_plot 等价,但允许指定输出路径(写到任务文件夹)。"""
    P_valid = result_df["P (25℃) bar"].dropna().values

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

    ax = axes[0]
    if len(P_valid):
        logP = np.log10(P_valid)
        bins = np.linspace(logP.min() - 0.2, logP.max() + 0.2, 18)
        ax.hist(logP, bins=bins, color="#6366f1", alpha=0.78,
                edgecolor="white", lw=1.2)
        ax.axvline(0.0, color="#ef4444", ls="--", lw=1.2, label="1 bar")
        ax.axvline(1.0, color="#f59e0b", ls="--", lw=1.2, label="10 bar")
        ax.axvspan(0.0, 1.0, color="#10b981", alpha=0.08,
                   label="实用区间 (0.1~10 bar)")
        ax.set_xlabel("log₁₀ P₂₅℃ / bar", fontsize=11)
        ax.set_ylabel("Count", fontsize=11)
        ax.set_title(f"室温平台压分布  (n={success_n})",
                     fontsize=12, fontweight="bold")
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(alpha=0.3)
    else:
        ax.text(0.5, 0.5, "无有效数据", ha="center", va="center",
                transform=ax.transAxes)
        ax.set_axis_off()

    ax = axes[1]
    dH_valid = result_df["ΔH (kJ/mol H₂)"].values
    if len(P_valid):
        mask = ~(np.isnan(dH_valid) | np.isnan(P_valid))
        ax.scatter(dH_valid[mask], P_valid[mask],
                   s=55, c="#8b5cf6", alpha=0.78, edgecolor="white", lw=1.2)
        ax.axhline(1.0, color="#ef4444", ls="--", lw=1, alpha=0.5)
        ax.axhline(10.0, color="#f59e0b", ls="--", lw=1, alpha=0.5)
        ax.set_yscale("log")
        ax.set_xlabel("ΔH / (kJ/mol H₂)", fontsize=11)
        ax.set_ylabel("P₂₅℃ / bar  (log)", fontsize=11)
        ax.set_title("ΔH — P₂₅℃ 散点", fontsize=12, fontweight="bold")
        ax.grid(alpha=0.3)
    else:
        ax.text(0.5, 0.5, "无有效数据", ha="center", va="center",
                transform=ax.transAxes)
        ax.set_axis_off()

    fig.tight_layout()
    fig.savefig(output_path, dpi=140)
    plt.close(fig)
    return output_path


# ============================================================
# 任务状态查询响应构建
# ============================================================
def _build_task_status_response(task_info: dict,
                                filt_V5_min: float, filt_V5_max: float,
                                filt_V6_min: float, filt_V6_max: float,
                                filt_Cap_min: float, filt_Cap_max: float) -> tuple:
    """构建任务状态查询的响应"""
    status = task_info.get("status", "unknown")
    progress = task_info.get("progress", 0)
    total = task_info.get("total", 0)
    processed = task_info.get("processed", 0)
    success = task_info.get("success_count", 0)
    fail = task_info.get("fail_count", 0)
    job_id = task_info.get("job_id", "")
    
    if status == "completed":
        status_icon = "✅"
        status_text = "已完成"
    elif status == "running":
        status_icon = "🔄"
        status_text = "运行中"
    elif status == "failed":
        status_icon = "❌"
        status_text = "失败"
    elif status == "cancelled":
        status_icon = "🚫"
        status_text = "已取消"
    else:
        status_icon = "⏳"
        status_text = "等待中"
    
    summary_md = (
        f"### 📋 任务ID: `{job_id}`  ·  {status_icon} {status_text}\n\n"
        f"<div class='pct-metric-grid'>"
        f"<div class='pct-metric pct-metric-total'>"
        f"<div class='pct-metric-label'>总材料数</div>"
        f"<div class='pct-metric-value'>{total}</div></div>"
        f"<div class='pct-metric pct-metric-ok'>"
        f"<div class='pct-metric-label'>已处理</div>"
        f"<div class='pct-metric-value'>{processed}</div></div>"
        f"<div class='pct-metric pct-metric-ok'>"
        f"<div class='pct-metric-label'>成功</div>"
        f"<div class='pct-metric-value'>{success}</div></div>"
        f"<div class='pct-metric pct-metric-fail'>"
        f"<div class='pct-metric-label'>失败</div>"
        f"<div class='pct-metric-value'>{fail}</div></div>"
        f"</div>\n"
    )
    summary_md += (
        f"<div class='pct-job-id-box'>"
        f"<span class='pct-job-id-label'>📎 任务ID (可复制查询)</span>"
        f"<code class='pct-job-id'>{job_id}</code>"
        f"</div>\n"
    )
    summary_md += f"\n<div class='pct-progress-bar'><div class='pct-progress-fill' style='width:{progress}%'></div></div>\n"
    summary_md += f"<div class='pct-progress-text'>进度: {progress}%</div>\n"
    
    if task_info.get("error"):
        summary_md += f"\n⚠️ 错误: {task_info['error']}\n"
    
    return None, summary_md, None, None, None, job_id


# ============================================================
# UI 构建
# ============================================================

# ============================================================
# UI 构建
# ============================================================
def build_batch_tab() -> None:
    """批量预测 Tab — 5 步分层流水线。

    Step 1 组份空间设计器(稀土专属):周期表点选元素 → 生成化学式
    Step 2 CSV 上传
    Step 3 触发批量预测
    Step 4 过滤结果
    Step 5 分层结果展示
    """

    # ================================================================
    # Step 1: 组份空间设计器
    # ================================================================
    
    # ---- 1.1 先声明所有状态组件（必须在事件绑定前声明）----
    # 注意:render=False 让组件进入"待渲染"队列,在 build_periodic_table_ui
    # 内部由 render() 控制渲染位置,避免被 Gradio 自动渲染到声明处。
    # 注意:hidden_textbox 需要 visible=True + CSS 隐藏，因为 Gradio 6 中 visible=False
    # 的组件不会渲染到 DOM，导致 JS 无法访问。
    space_hidden = gr.Textbox(
        visible=True, value="",
        elem_id="pt-hidden-selected", render=False,
    )
    space_status = gr.Textbox(
        label="🎯 已选元素 (RE★ = 粉红色, B 位 = 白底)",
        value="(尚未点选元素 — 请在下方周期表上点击元素)",
        interactive=True,
        elem_classes="pct-input",
        info="稀土元素会自动高亮。手动编辑时请用逗号分隔",
        render=False,
    )
    space_max_n = gr.Slider(
        label="最多生成组份数",
        minimum=10, maximum=500, value=200, step=10,
        info="防止组合爆炸。>500 会显著拖慢预测",
        render=False,
    )
    space_strict_re = gr.Checkbox(
        label="强制至少 1 个稀土元素 (RE★)",
        value=True,
        info="本平台仅支持稀土储氢合金,关闭此选项可生成非稀土候选",
        render=False,
    )
    space_preview = gr.HTML(
        value="""
        <div class="pct-empty-state">
            <div class="pct-empty-icon">🧪</div>
            <div class="pct-empty-title">尚未生成组份</div>
            <div class="pct-empty-hint">
                1) 在下方周期表点选稀土(A 位★粉红)与 B 位元素<br>
                2) 点击「🧬 生成组份预览」<br>
                3) 确认后点击「📤 送入批量预测」<br>
                或点击「下载 CSV」自行编辑后上传 Step 2
            </div>
        </div>
        """,
        elem_classes="pct-empty-wrap",
        render=False,
    )
    space_gen_btn = gr.Button(
        "🧬 生成组份预览", variant="primary",
        elem_classes="batch-btn", size="md",
        render=False,
    )
    space_send_btn = gr.Button(
        "📤 送入批量预测", variant="primary",
        elem_classes="predict-btn", size="md",
        render=False,
    )

    # 用隐藏 textbox 代替 gr.State 存储生成的化学式列表
    space_formulas_hidden = gr.Textbox(
        visible=True, value="",
        elem_id="pt-formulas-hidden", render=False,
    )

    # Step 2 CSV 组件需要先声明（作为 build_periodic_table_ui 的输出参数）
    batch_file = gr.File(
        label="📁 上传 CSV 文件",
        file_types=[".csv"],
        type="filepath",
        interactive=True,
        elem_classes="pct-input",
        render=False,
    )
    batch_csv_preview = gr.HTML(
        value="",
        render=False,
    )

    # ---- 1.2 UI 渲染顺序：Step 1 标题 → 周期表 → 控件/按钮/预览（已在 build_periodic_table_ui 渲染）----
    gr.HTML(_step(
        1, "🧪", "组份空间设计 — 在周期表上勾选稀土(A 位) + 配位元素(B 位)",
        "<span style='color:#64748b;font-size:13px;'>"
        "稀土元素(★粉红): La/Ce/Pr/Nd/Sm.../Y/Sc · B 位: Ni/Mn/Co/Al... &nbsp;"
        "点击元素按钮 → 展开为 AB5 / A2B7 / AB3 / AB2 等候选化学式 → 送入批量预测</span>",
    ))

    # 注意:space_status / space_max_n / space_strict_re / space_gen_btn /
    # space_send_btn / space_preview 等组件已经在 build_periodic_table_ui()
    # 内部通过 .render() 渲染过,这里不能再 render(),否则会触发 DuplicateBlockError。
    # 渲染顺序:status_textbox → 主周期表 → slider/checkbox → buttons → preview

    # 周期表渲染
    build_periodic_table_ui(
        hidden_textbox=space_hidden,
        status_textbox=space_status,
        generate_btn=space_gen_btn,
        send_btn=space_send_btn,
        max_n_slider=space_max_n,
        strict_re_checkbox=space_strict_re,
        preview_html=space_preview,
        formulas_hidden=space_formulas_hidden,
        batch_file_ref=batch_file,
        batch_preview_ref=batch_csv_preview,
    )

    # Step 2 CSV 上传（渲染在 Step 1 之后，但组件引用已在上面传入）
    gr.HTML(_step(
        2, "📂", "上传 CSV  ·  解析与预览",
        "<span style='color:#64748b;font-size:13px;'>"
        "或用上方 Step 1「组份空间设计器」生成候选化学式送入此处;"
        "必须含 <code>formula</code> 列,可选 <code>V0</code></span>",
    ))

    with gr.Row():
        with gr.Column(scale=1, min_width=320):
            batch_file.render()
            gr.HTML(
                """
                <div class="pct-csv-hint">
                    <b>📋 CSV 格式示例</b>
                    <pre class="pct-csv-pre">formula,V0,name,note
La0.7Y0.3Ni4.5Mn0.5,293.0,Sample-A,AB5 RE baseline
LaNi5,293.0,Sample-B,LaNi5 reference
La0.5Ce0.5Ni5,293.0,Sample-C,Mixed RE</pre>
                    <div class="pct-csv-legend">
                        <span><b>formula</b> 必填,化学式</span>
                        <span><b>V0</b> 可选,默认 293</span>
                        <span><b>name / note</b> 自动透传</span>
                    </div>
                </div>
                """
            )
        with gr.Column(scale=2, min_width=600):
            batch_csv_preview.render()

    # Step 2.1: V0 批量统一设置（当 CSV 无 V0 列时生效）
    gr.HTML(
        '<div class="pct-csv-v0-wrap">'
        '<div class="pct-csv-v0-label">'
        '<span class="pct-csv-v0-icon">🌡️</span>'
        '批量 V0 设置 — CSV 无 V0 列时,所有材料统一使用此值'
        '</div>'
    )
    batch_V0 = gr.Slider(
        label="🌡️ 批量预测统一 V0 (K)",
        minimum=200.0, maximum=500.0, value=293.0, step=1.0,
        info="默认 293.0 K (= 20℃)。CSV 中有 V0 列时优先使用列值",
        elem_classes="pct-input",
    )
    gr.HTML('</div>')

    # ---- Step 3:触发 ----
    gr.HTML(_step(
        3, "🚀", "触发批量预测",
        "<span style='color:#64748b;font-size:13px;'>"
        "点击按钮启动流水线: 特征 → 逐条推理 → 汇总 → 过滤 → 输出</span>",
    ))

    with gr.Row():
        with gr.Column(scale=2):
            batch_btn = gr.Button(
                "🚀 开始批量预测", variant="primary",
                elem_classes="batch-btn", size="lg",
            )
            # 任务名称 — 用户可自命名文件夹
            custom_job_name = gr.Textbox(
                label="📛 任务名称 (选填,用于命名文件夹)",
                placeholder="例如: LaY_NiMn_screening_v2",
                info="留空则自动生成 UUID。文件夹名将只保留字母/数字/下划线/连字符",
                interactive=True,
                elem_classes="pct-input",
            )
        with gr.Column(scale=1):
            job_id_input = gr.Textbox(
                label="📎 任务ID (可输入历史ID查询)",
                placeholder="任务名称或8位UUID",
                interactive=True,
                elem_classes="pct-input",
            )
            batch_job_id = gr.Textbox(
                label="📋 当前任务ID",
                interactive=False,
                elem_classes="pct-job-id-display",
            )

    # ---- Step 4:过滤控制 ----
    gr.HTML(_step(
        4, "🔍", "过滤结果",
        "<span style='color:#64748b;font-size:13px;'>"
        "用范围滑块过滤 V5 / V6 / Capacity,立即生效</span>",
    ))

    with gr.Row():
        with gr.Column():
            gr.HTML(
                "<div style='font-size:13px;font-weight:600;color:#475569;"
                "margin-bottom:8px;'>V5 (van't Hoff 斜率,单位 kK)</div>"
            )
            filt_V5_min = gr.Number(label="V5 最小值", value=-2.0, precision=4)
            filt_V5_max = gr.Number(label="V5 最大值", value=2.0, precision=4)
        with gr.Column():
            gr.HTML(
                "<div style='font-size:13px;font-weight:600;color:#475569;"
                "margin-bottom:8px;'>V6 (van't Hoff 截距)</div>"
            )
            filt_V6_min = gr.Number(label="V6 最小值", value=-5.0, precision=4)
            filt_V6_max = gr.Number(label="V6 最大值", value=15.0, precision=4)
        with gr.Column():
            gr.HTML(
                "<div style='font-size:13px;font-weight:600;color:#475569;"
                "margin-bottom:8px;'>Capacity (mol/kg)</div>"
            )
            filt_Cap_min = gr.Number(label="Capacity 最小值", value=0.0, precision=3)
            filt_Cap_max = gr.Number(label="Capacity 最大值", value=10.0, precision=3)

    # ---- Step 5:结果 — 分层 ----
    gr.HTML(_step(
        5, "📊", "分层结果展示",
        "<span style='color:#64748b;font-size:13px;'>"
        "执行后逐层展开:摘要 → 分布图 → 表格 → 下载</span>",
    ))

    # Layer A:摘要
    with gr.Group(elem_classes="pct-result-panel pct-layer-a"):
        gr.HTML(
            "<div class='pct-layer-tag pct-layer-tag-a'>"
            "🅰️ 摘要  Summary</div>"
        )
        batch_summary = gr.HTML(label="📊 预测汇总")

    # Layer B:分布图
    with gr.Group(elem_classes="pct-result-panel pct-layer-b"):
        gr.HTML(
            "<div class='pct-layer-tag pct-layer-tag-b'>"
            "🅱️ 分布  Distribution</div>"
        )
        batch_plot = gr.Image(label="📈 P₂₅℃ 分布 + ΔH-P 散点",
                              elem_classes="pct-plot")

    # Layer C:表格
    with gr.Group(elem_classes="pct-result-panel pct-layer-c"):
        gr.HTML(
            "<div class='pct-layer-tag pct-layer-tag-c'>"
            "🅲 数据表  Table</div>"
        )
        batch_table = gr.Dataframe(label="📋 预测结果表",
                                  interactive=False, wrap=True)

    # Layer D:下载
    with gr.Group(elem_classes="pct-result-panel pct-layer-d"):
        gr.HTML(
            "<div class='pct-layer-tag pct-layer-tag-d'>"
            "🅳 下载  Download</div>"
        )
        batch_csv = gr.File(
            label="⬇️ 完整结果 CSV(UTF-8 BOM,Excel 友好)",
            interactive=False,
        )
        batch_csv_filtered = gr.File(
            label="⬇️ 过滤后结果 CSV(当前范围)",
            interactive=False,
        )

    # =========================================================
    # 事件绑定
    # =========================================================

    # CSV 上传后预览
    def _preview_csv(file_obj):
        if file_obj is None:
            return """
            <div class="pct-empty-state">
                <div class="pct-empty-icon">📊</div>
                <div class="pct-empty-title">未上传文件</div>
            </div>"""
        try:
            df = pd.read_csv(file_obj.name)
        except Exception as e:
            return (
                f"<div class='pct-empty-state pct-empty-state-error'>"
                f"<div class='pct-empty-icon'>❌</div>"
                f"<div class='pct-empty-title'>读取失败</div>"
                f"<div class='pct-empty-hint'>{e}</div></div>"
            )
        n = len(df)
        has_formula = "formula" in df.columns
        has_V0 = "V0" in df.columns
        passthrough = [c for c in df.columns if c not in ("formula", "V0")]
        head = df.head(5).to_html(
            classes="pct-preview-table", index=False, border=0)
        chip_f = "<span class='pct-chip-ok'>✓ formula</span>" if has_formula                  else "<span class='pct-chip-fail'>✗ 缺 formula</span>"
        chip_v = "<span class='pct-chip-ok'>✓ V0</span>" if has_V0                  else "<span class='pct-chip-warn'>○ V0 可选</span>"
        chips_pass = " ".join(
            f"<span class='pct-chip-info'>↪ {c}</span>" for c in passthrough)
        return f"""
        <div class="pct-preview">
          <div class="pct-preview-meta">
            <div class="pct-meta-item">
              <span class="pct-meta-label">总行数</span>
              <span class="pct-meta-value">{n}</span>
            </div>
            <div class="pct-meta-item">
              <span class="pct-meta-label">列数</span>
              <span class="pct-meta-value">{len(df.columns)}</span>
            </div>
            <div class="pct-meta-item pct-meta-chips">
              <span class="pct-meta-label">列识别</span>
              <span class="pct-meta-chips">{chip_f} {chip_v} {chips_pass}</span>
            </div>
          </div>
          <div class="pct-preview-table-wrap">{head}</div>
          <div class="pct-preview-foot">显示前 5 行(共 {n} 行)</div>
        </div>"""

    batch_file.change(
        _preview_csv,
        inputs=[batch_file],
        outputs=[batch_csv_preview],
    )

    batch_btn.click(
        predict_batch,
        inputs=[batch_file, filt_V5_min, filt_V5_max,
                filt_V6_min, filt_V6_max, filt_Cap_min, filt_Cap_max,
                job_id_input, custom_job_name, batch_V0],
        outputs=[batch_table, batch_summary, batch_plot,
                 batch_csv, batch_csv_filtered, batch_job_id],
    )

    # =========================================================
    # Step 6: 任务历史管理 — 列表 / 下载 / 删除
    # =========================================================
    gr.HTML(_step(
        6, "📚", "任务历史管理",
        "<span style='color:#64748b;font-size:13px;'>"
        "每次批量预测都会创建一个独立任务文件夹 <code>assets/jobs/&lt;job_id&gt;/</code>,"
        "下方可浏览历史任务、下载 ZIP 压缩包或删除任务</span>",
    ))

    # CSS for jobs panel
    gr.HTML(
        '<style>'
        '.pct-jobs-wrap{display:flex;flex-direction:column;gap:8px;max-height:520px;'
        'overflow-y:auto;padding:4px 2px;}'
        '.pct-job-row{background:#fff;border:1px solid #e2e8f0;border-radius:10px;'
        'padding:10px 12px;box-shadow:0 1px 2px rgba(15,23,42,.04);'
        'transition:box-shadow .15s,transform .15s;}'
        '.pct-job-row:hover{box-shadow:0 4px 10px rgba(99,102,241,.18);'
        'transform:translateY(-1px);border-color:#c7d2fe;}'
        '.pct-job-row-head{display:flex;justify-content:space-between;align-items:center;'
        'margin-bottom:6px;}'
        '.pct-job-id-tag{background:linear-gradient(135deg,#ede9fe 0%,#fce7f3 100%);'
        'color:#5b21b6;padding:3px 9px;border-radius:5px;font-size:13px;'
        'font-weight:700;letter-spacing:.5px;}'
        '.pct-job-mtime{font-size:11px;color:#94a3b8;}'
        '.pct-job-row-body{font-size:13px;color:#475569;margin:4px 0 6px 0;}'
        '.pct-job-row-body b{color:#1e293b;font-size:14px;}'
        '.pct-job-row-chips{display:flex;gap:6px;margin:6px 0 8px 0;'
        'flex-wrap:wrap;}'
        '.pct-job-row-actions{display:flex;gap:6px;flex-wrap:wrap;}'
        '.pct-job-link{display:inline-block;padding:4px 10px;font-size:12px;'
        'background:linear-gradient(135deg,#eef2ff 0%,#faf5ff 100%);'
        'border:1px solid #c4b5fd;border-radius:6px;color:#5b21b6;'
        'text-decoration:none;font-weight:600;}'
        '.pct-job-link:hover{background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 100%);'
        'color:#fff;border-color:transparent;}'
        '.pct-job-del{display:inline-block;padding:4px 10px;font-size:12px;'
        'background:linear-gradient(135deg,#fee2e2 0%,#fecaca 100%);'
        'border:1px solid #fca5a5;border-radius:6px;color:#991b1b;'
        'text-decoration:none;font-weight:600;cursor:pointer;}'
        '.pct-job-del:hover{background:linear-gradient(135deg,#ef4444 0%,#dc2626 100%);'
        'color:#fff;border-color:transparent;}'
        '.pct-folder-hint{background:linear-gradient(135deg,#ecfdf5 0%,#d1fae5 100%);'
        'border:1px solid #6ee7b7;border-radius:8px;padding:6px 10px;'
        'font-size:12px;color:#047857;margin:6px 0;}'
        '.pct-folder-hint code{background:rgba(255,255,255,.5);padding:1px 6px;'
        'border-radius:4px;font-weight:700;}'
        '.pct-jobs-toolbar{display:flex;gap:10px;align-items:center;'
        'background:linear-gradient(135deg,#eef2ff 0%,#faf5ff 100%);'
        'border:1px solid #c7d2fe;border-radius:10px;padding:8px 12px;'
        'margin:6px 0 10px 0;}'
        '</style>'
    )

    with gr.Row():
        with gr.Column(scale=3):
            gr.HTML(
                "<div style='font-size:13px;color:#475569;'>"
                "<b>📂 任务文件夹根目录</b>: <code>assets/jobs/</code> "
                "(共 <span id='pct-job-count'>0</span> 个历史任务)"
                "</div>"
            )
        with gr.Column(scale=1, min_width=120):
            batch_refresh_btn = gr.Button(
                "🔄 刷新列表", variant="secondary",
                size="sm", elem_classes="batch-btn",
            )
        with gr.Column(scale=1, min_width=160):
            batch_pack_zip_btn = gr.Button(
                "📦 打包当前任务 ZIP", variant="primary",
                size="sm", elem_classes="batch-btn",
            )

    with gr.Row():
        with gr.Column(scale=2, min_width=380):
            jobs_list_html = gr.HTML(
                value=_render_jobs_html([]),
                elem_classes="pct-jobs-list",
            )
        with gr.Column(scale=1, min_width=240):
            job_delete_id = gr.Textbox(
                label="🗑️ 要删除的任务ID",
                placeholder="如 a1b2c3d4",
                interactive=True,
                elem_classes="pct-input",
            )
            batch_delete_btn = gr.Button(
                "🗑️ 删除该任务文件夹", variant="stop",
                size="md", elem_classes="batch-btn",
            )
            batch_zip_file = gr.File(
                label="⬇️ 当前任务 ZIP 下载",
                interactive=False,
            )
            gr.HTML(
                "<div style='font-size:11px;color:#94a3b8;margin-top:8px;'>"
                "<b>💡 操作提示</b><br>"
                "• 每次批量预测完成,自动创建任务文件夹<br>"
                "• 点击任务卡片上的链接直接下载文件<br>"
                "• 输入任务ID可单独删除指定任务<br>"
                "• 「打包 ZIP」按钮会把刚跑完的任务打包成单文件下载"
                "</div>"
            )

    # 任务列表刷新
    def _refresh_jobs():
        jobs = list_jobs()
        return _render_jobs_html(jobs)

    batch_refresh_btn.click(
        _refresh_jobs,
        inputs=[],
        outputs=[jobs_list_html],
    )

    # 删除指定任务
    def _delete_job(job_id: str):
        if not job_id or not job_id.strip():
            return _render_jobs_html(list_jobs()), None, "⚠️ 请先输入要删除的任务ID"
        ok = delete_job(job_id.strip())
        jobs_now = list_jobs()
        msg = (f"✅ 已删除任务 <code>{job_id}</code> 及其 ZIP 包" if ok
               else f"⚠️ 未找到任务 <code>{job_id}</code> (或 ID 非法)")
        return _render_jobs_html(jobs_now), None, msg

    batch_delete_btn.click(
        _delete_job,
        inputs=[job_delete_id],
        outputs=[jobs_list_html, batch_zip_file, batch_summary],
    )

    # 打包当前任务 ZIP
    def _pack_current_zip(current_job_id: str):
        if not current_job_id or not current_job_id.strip():
            return None, "⚠️ 请先完成一次批量预测,再点此按钮打包"
        zp = pack_job_zip(current_job_id.strip())
        if zp is None:
            return None, f"⚠️ 任务 <code>{current_job_id}</code> 不存在或已被删除"
        return zp, f"✅ 已打包任务 <code>{current_job_id}</code> → assets/job_{current_job_id}.zip"

    batch_pack_zip_btn.click(
        _pack_current_zip,
        inputs=[batch_job_id],
        outputs=[batch_zip_file, batch_summary],
    )

    # 每次完整预测后,自动刷新历史列表 (挂在 batch_btn.click 的链式触发上)
    def _refresh_after_predict(current_job_id: str):
        # 让历史面板反映出刚刚跑完的任务
        jobs = list_jobs()
        return _render_jobs_html(jobs), current_job_id or ""

    # 用 gr.on 监听 predict_batch 链式返回 batch_job_id 之后,直接刷新列表
    # 简化做法:让 batch_btn.click 的 outputs 包含 jobs_list_html
    # 由于 batch_btn.click 已注册,我们用 on() 添加二级监听
    batch_btn.click(
        _refresh_after_predict,
        inputs=[batch_job_id],
        outputs=[jobs_list_html, batch_job_id],
    )
