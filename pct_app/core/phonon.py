"""PhononBench 接入层。"""

from __future__ import annotations
from ..config.constants import PHONONBENK_URL


def phonon_check_stub(formula: str) -> dict:
    """
    PhononBench(http://phononbench.cn)目前采用 CIF 作为输入,
    而材料成分 → CIF 推导需要晶体结构(原胞/空间群),无法仅凭化学式给出可靠声子谱。
    本函数返回"待补全 CIF"的提示 + 已知结构原型建议。
    """
    return {
        "status":  "skipped",
        "reason":  "PhononBench 需要 CIF 输入,化学式不能唯一确定晶体结构",
        "next":    "上传 CIF 文件 或 提供空间群 + 原胞参数,以触发真实声子计算",
        "endpoint": PHONONBENK_URL,
    }


def phonon_check_real(cif_text: str) -> dict:
    """调用 PhononBench 公开 API 的占位实现。"""
    if not cif_text or len(cif_text) < 20:
        return {"status": "error", "msg": "CIF 内容过短"}

    try:
        # 真实端点格式以 PhononBench 官方文档为准,此处保留可调用骨架
        # resp = requests.post(PHONONBENK_SUBMIT, json={"cif": cif_text}, timeout=30)
        # return resp.json()
        return {
            "status": "submitted",
            "msg":    "已提交到 PhononBench(模拟响应,真实端点见 http://phononbench.cn)",
            "task_id": "demo-" + str(abs(hash(cif_text))) % 10000,
            "endpoint": PHONONBENK_URL,
        }
    except Exception as e:
        return {"status": "error", "msg": str(e)}
