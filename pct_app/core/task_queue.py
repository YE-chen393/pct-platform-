# -*- coding: utf-8 -*-
"""
任务状态管理模块
================

提供批量预测任务的异步队列和状态跟踪功能。

采用 TaskStore + TaskExecutor 双层架构:
  - TaskStore:    线程安全的任务元数据存储(in-memory + 最近 100 条)
  - TaskExecutor: 后台线程池(默认 2 worker)
"""

from __future__ import annotations
import uuid
import threading
import queue
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Any
from datetime import datetime
from pathlib import Path
import pandas as pd

# ============================================================
# 任务状态枚举
# ============================================================
class TaskStatus(str, Enum):
    """任务执行状态"""
    PENDING = "pending"      # 等待中
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"   # 已取消


# ============================================================
# 任务数据类
# ============================================================
@dataclass
class TaskInfo:
    """任务信息数据结构"""
    job_id: str                           # 任务唯一ID (8位)
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0                 # 0.0 ~ 1.0
    total: int = 0                        # 总材料数
    processed: int = 0                   # 已处理数
    success_count: int = 0               # 成功数
    fail_count: int = 0                  # 失败数
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    error: Optional[str] = None
    output_dir: Optional[str] = None
    result_df: Optional[pd.DataFrame] = None
    filtered_df: Optional[pd.DataFrame] = None
    
    def to_dict(self) -> dict:
        """转换为字典，用于JSON序列化"""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress": round(self.progress * 100, 1),
            "total": self.total,
            "processed": self.processed,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "error": self.error,
            "output_dir": self.output_dir,
        }


# ============================================================
# 全局任务存储
# ============================================================
class TaskStore:
    """
    线程安全的任务存储与查询
    
    类似于之前项目的 TASK_STATUS 字典，但采用面向对象设计。
    """
    
    def __init__(self, max_tasks: int = 100):
        self._tasks: dict[str, TaskInfo] = {}
        self._lock = threading.RLock()
        self._max_tasks = max_tasks
    
    def create_task(self, total: int = 0) -> str:
        """创建新任务，返回 job_id"""
        job_id = str(uuid.uuid4())[:8]
        task = TaskInfo(
            job_id=job_id,
            total=total,
            start_time=datetime.now().isoformat()
        )
        with self._lock:
            self._tasks[job_id] = task
            self._cleanup_old_tasks()
        return job_id
    
    def get_task(self, job_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        with self._lock:
            return self._tasks.get(job_id)
    
    def update_task(self, job_id: str, **kwargs) -> bool:
        """更新任务字段"""
        with self._lock:
            task = self._tasks.get(job_id)
            if task is None:
                return False
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            return True
    
    def list_tasks(self, limit: int = 20) -> list[dict]:
        """列出最近的任务"""
        with self._lock:
            tasks = sorted(
                self._tasks.values(),
                key=lambda t: t.start_time or "",
                reverse=True
            )[:limit]
            return [t.to_dict() for t in tasks]
    
    def _cleanup_old_tasks(self):
        """清理旧任务，保持存储在限制范围内"""
        if len(self._tasks) <= self._max_tasks:
            return
        # 删除最旧的已完成任务
        old_tasks = sorted(
            self._tasks.values(),
            key=lambda t: t.start_time or ""
        )
        for task in old_tasks:
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                del self._tasks[task.job_id]
                if len(self._tasks) <= self._max_tasks:
                    break


# 全局任务存储实例
TASK_STORE = TaskStore(max_tasks=100)


# ============================================================
# 任务执行器
# ============================================================
class TaskExecutor:
    """
    后台任务执行器
    
    使用独立线程池处理批量预测任务，避免阻塞主线程。
    """
    
    def __init__(self, max_workers: int = 2):
        self._thread_pool: list[threading.Thread] = []
        self._task_queue = queue.Queue()
        self._running = True
        self._workers = max_workers
        
        # 启动工作线程
        for i in range(max_workers):
            t = threading.Thread(
                target=self._worker,
                name=f"TaskWorker-{i}",
                daemon=True
            )
            t.start()
            self._thread_pool.append(t)
    
    def _worker(self):
        """工作线程主循环"""
        while self._running:
            try:
                task_item = self._task_queue.get(timeout=1.0)
                if task_item is None:
                    continue
                job_id, func, args, kwargs = task_item
                self._execute_task(job_id, func, args, kwargs)
                self._task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[TaskExecutor] Worker error: {e}")
    
    def _execute_task(self, job_id: str, func: Callable, args: tuple, kwargs: dict):
        """执行单个任务"""
        TASK_STORE.update_task(job_id, status=TaskStatus.RUNNING)
        try:
            result = func(*args, **kwargs)
            TASK_STORE.update_task(
                job_id,
                status=TaskStatus.COMPLETED,
                progress=1.0,
                end_time=datetime.now().isoformat()
            )
            return result
        except Exception as e:
            TASK_STORE.update_task(
                job_id,
                status=TaskStatus.FAILED,
                error=str(e),
                end_time=datetime.now().isoformat()
            )
            raise
    
    def submit(self, job_id: str, func: Callable, *args, **kwargs) -> None:
        """提交任务到队列"""
        self._task_queue.put((job_id, func, args, kwargs))
    
    def shutdown(self, wait: bool = True):
        """关闭执行器"""
        self._running = False
        if wait:
            self._task_queue.join()
            for t in self._thread_pool:
                t.join(timeout=2.0)


# 全局任务执行器实例
TASK_EXECUTOR = TaskExecutor(max_workers=2)


# ============================================================
# 便捷函数
# ============================================================
def create_batch_task(total: int = 0) -> str:
    """创建批量预测任务"""
    return TASK_STORE.create_task(total)


def get_task_status(job_id: str) -> Optional[dict]:
    """获取任务状态"""
    task = TASK_STORE.get_task(job_id)
    return task.to_dict() if task else None


def list_recent_tasks(limit: int = 20) -> list[dict]:
    """列出最近任务"""
    return TASK_STORE.list_tasks(limit)
