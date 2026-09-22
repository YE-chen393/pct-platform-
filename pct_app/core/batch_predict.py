# -*- coding: utf-8 -*-
"""
异步批量预测模块
================

支持后台任务队列的批量预测实现。

功能:
- 异步提交任务到后台执行
- 实时更新任务进度
- 支持取消任务
- 生成完整的预测结果和筛选结果
"""

from __future__ import annotations
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Callable, Any
from dataclasses import dataclass
import pandas as pd
import numpy as np

from .task_queue import (
    TASK_STORE, TASK_EXECUTOR, TaskStatus,
    create_batch_task, get_task_status
)
from .featurize import featurize
from .io import _load
from ..config.paths import ASSETS_DIR


# ============================================================
# 默认筛选条件
# ============================================================
DEFAULT_FILTERS = {
    "capacity_wt%": (1.0, 6.0),            # 重量百分比 (wt%)
    "enthalpy_kJ_mol": (-50.0, -20.0),     # 焓 (kJ/mol)
    "entropy_J_molK": (80.0, 140.0),        # 熵 (J/mol·K)
    "platform_pressure_bar": (0.01, 100.0), # 平台压 (bar)
}


# ============================================================
# 批量预测核心函数（同步版本）
# ============================================================
def batch_predict_sync(
    input_file: str,
    output_dir: str,
    temperature: float = 298.0,
    filters: Optional[Dict[str, Tuple[float, float]]] = None,
    job_id: Optional[str] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    同步批量预测函数,支持进度回调。

    设计:用 TaskInfo 内嵌的 progress_callback + job_id 两条更新通道,
    方便 Gradio 进度条和异步监控两个场景共用同一份逻辑。

    Parameters:
    ----------
    input_file : str
        输入CSV文件路径，必须包含 'formula' 列
    output_dir : str
        输出目录路径
    temperature : float
        预测温度 (K)
    filters : dict, optional
        筛选条件 {字段名: (最小值, 最大值)}
    job_id : str, optional
        任务ID，用于更新任务状态
    progress_callback : callable, optional
        进度回调函数 (progress: float, message: str)
    
    Returns:
    -------
    df_full : pd.DataFrame
        所有成功预测结果
    df_filtered : pd.DataFrame
        通过筛选条件的候选材料
    """
    # 合并筛选条件
    final_filters = DEFAULT_FILTERS.copy()
    if filters:
        final_filters.update(filters)
    
    # 读取输入文件
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    df_input = pd.read_csv(input_path)
    if "formula" not in df_input.columns:
        raise ValueError("Input CSV must contain a 'formula' column.")
    
    n_total = len(df_input)
    formulas = df_input["formula"].astype(str).tolist()
    has_V0 = "V0" in df_input.columns
    
    if progress_callback:
        progress_callback(0.0, f"读取到 {n_total} 个材料，开始预测...")
    
    # 更新任务状态
    if job_id:
        TASK_STORE.update_task(job_id, total=n_total)
    
    # 预测循环
    results = []
    for i, formula in enumerate(formulas):
        # 更新进度
        progress = (i + 1) / n_total
        msg = f"预测 {i+1}/{n_total}: {formula}"
        
        if progress_callback:
            progress_callback(progress, msg)
        
        if job_id:
            TASK_STORE.update_task(
                job_id,
                progress=progress,
                processed=i + 1,
            )
        
        # 获取V0
        V0 = float(df_input["V0"].iloc[i]) if has_V0 else 293.0
        
        try:
            # 调用预测
            from ..ui.predictor import predict_three
            res = predict_three(formula, V0=V0)
            
            if res.get("V5") is not None and res.get("V6") is not None:
                # 计算热力学性质
                R = 8.314  # J/(mol·K)
                dH_kJ = -res["V5"] * 1000 * R / 1000.0  # kJ/mol
                dS = res["V6"] * R  # J/(mol·K)
                
                # 计算平台压 (van't Hoff方程)
                if dH_kJ < 0 and dS > 0:
                    lnP = dH_kJ * 1000 / (R * temperature) - dS / R
                    P_bar = np.exp(lnP) / 100000  # Pa -> bar
                else:
                    P_bar = np.nan
                
                # 计算H含量
                if res.get("Capacity") is not None:
                    cap_wt = res["Capacity"] * 2.016 / 1000  # mol/kg -> wt%
                else:
                    cap_wt = np.nan
                
                results.append({
                    "formula": formula,
                    "V0": V0,
                    "V5": res["V5"],
                    "V6": res["V6"],
                    "dH_kJ_mol": dH_kJ,
                    "dS_J_molK": dS,
                    "P_bar": P_bar,
                    "Capacity_mol_kg": res["Capacity"],
                    "Capacity_wt%": cap_wt,
                    "success": True,
                })
                
                if job_id:
                    TASK_STORE.update_task(
                        job_id,
                        success_count=len([r for r in results if r["success"]])
                    )
            else:
                results.append({
                    "formula": formula,
                    "V0": V0,
                    "success": False,
                    "error": "V5 or V6 is None",
                })
        except Exception as e:
            results.append({
                "formula": formula,
                "V0": V0,
                "success": False,
                "error": str(e),
            })
            if job_id:
                TASK_STORE.update_task(
                    job_id,
                    fail_count=TASK_STORE.get_task(job_id).fail_count + 1 if TASK_STORE.get_task(job_id) else 1
                )
    
    # 构建DataFrame
    df_full = pd.DataFrame(results)
    df_success = df_full[df_full["success"]].copy()
    
    # 应用筛选
    mask = pd.Series([True] * len(df_success))
    for col, (low, high) in final_filters.items():
        if col in df_success.columns:
            col_mask = (df_success[col] >= low) & (df_success[col] <= high)
            mask &= col_mask
    
    df_filtered = df_success[mask].copy().reset_index(drop=True)
    
    # 保存结果
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    df_full.to_csv(output_path / "full_predictions.csv", index=False)
    df_filtered.to_csv(output_path / "filtered_candidates.csv", index=False)
    
    if progress_callback:
        progress_callback(1.0, f"完成! 成功 {len(df_success)}, 筛选通过 {len(df_filtered)}")
    
    return df_full, df_filtered


# ============================================================
# 异步任务提交
# ============================================================
def submit_batch_task(
    input_file: str,
    temperature: float = 298.0,
    filters: Optional[Dict[str, Tuple[float, float]]] = None,
) -> str:
    """
    提交批量预测任务到后台执行。
    
    Returns:
    -------
    job_id : str
        任务ID，用于查询进度
    """
    # 创建任务
    job_id = create_batch_task()
    
    # 创建输出目录
    output_dir = str(ASSETS_DIR / "batch_outputs" / job_id)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # 更新任务输出目录
    TASK_STORE.update_task(job_id, output_dir=output_dir)
    
    # 提交到后台执行
    TASK_EXECUTOR.submit(
        job_id,
        batch_predict_sync,
        input_file,
        output_dir,
        temperature,
        filters,
        job_id,
        None,  # progress_callback 在worker线程中不可用
    )
    
    return job_id


# ============================================================
# 获取任务结果
# ============================================================
def get_task_result(job_id: str) -> Optional[Dict[str, Any]]:
    """
    获取任务结果（完成后可用）
    
    Returns:
    -------
    dict with keys:
        - job_id: str
        - status: str
        - result_df: pd.DataFrame or None
        - filtered_df: pd.DataFrame or None
        - output_dir: str or None
    """
    task = TASK_STORE.get_task(job_id)
    if task is None:
        return None
    
    result = task.to_dict()
    
    if task.status == TaskStatus.COMPLETED and task.result_df is not None:
        result["result_df"] = task.result_df
        result["filtered_df"] = task.filtered_df
    
    return result


# ============================================================
# 便捷函数
# ============================================================
def get_batch_progress(job_id: str) -> Optional[dict]:
    """获取批量任务进度（简化版）"""
    task = TASK_STORE.get_task(job_id)
    if task is None:
        return None
    
    return {
        "job_id": task.job_id,
        "status": task.status.value,
        "progress": task.progress,
        "processed": task.processed,
        "total": task.total,
        "success_count": task.success_count,
        "fail_count": task.fail_count,
    }
