"""核心预测层:纯计算 + IO,无 gradio 依赖

Note:
  - predict_three / predict_full 已搬迁到 pct_app.ui.predictor
  - hydrogenated_cif_for_download 已搬迁到 pct_app.ui.predictor
"""

from .featurize import featurize, MAGPIE
from .io import MODEL_REGISTRY, _load
from .thermodynamics import h_to_m_to_wt_pct
from .plots import plot_vant_hoff, plot_p_vs_T, plot_pct_isotherms
from .structures import structure_to_cif_for_download
from .phonon import phonon_check_stub, phonon_check_real
from .task_queue import (
    create_batch_task, get_task_status, list_recent_tasks,
    TASK_STORE, TASK_EXECUTOR, TaskStatus, TaskInfo
)

__all__ = [
    "featurize", "MAGPIE",
    "MODEL_REGISTRY", "_load",
    "h_to_m_to_wt_pct",
    "plot_vant_hoff", "plot_p_vs_T", "plot_pct_isotherms",
    "structure_to_cif_for_download",
    "phonon_check_stub", "phonon_check_real",
    # 任务队列
    "create_batch_task", "get_task_status", "list_recent_tasks",
    "TASK_STORE", "TASK_EXECUTOR", "TaskStatus", "TaskInfo",
]
