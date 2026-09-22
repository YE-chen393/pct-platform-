# -*- coding: utf-8 -*-
"""
REST API 服务模块
=================

提供任务状态查询的 REST API 接口(基于 Flask)。

使用方法:
    # 与 Gradio 并行运行
    from pct_app.api import run_api_server
    import threading
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()

    # 或者单独启动
    PYTHONPATH="$PWD:$PYTHONPATH" python -m pct_app.api
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
from functools import wraps
from flask import Flask, jsonify, request, send_file, Response
from flask_cors import CORS

# 确保 pct_app 在 Python 路径中
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pct_app.core.task_queue import (
    TASK_STORE, TASK_EXECUTOR, get_task_status, list_recent_tasks,
    TaskStatus
)
from pct_app.core.batch_predict import submit_batch_task, get_batch_progress


# ============================================================
# Flask 应用
# ============================================================
def create_app() -> Flask:
    """创建 Flask 应用"""
    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False
    CORS(app)  # 允许跨域访问
    
    # 注册路由
    register_routes(app)
    
    return app


def register_routes(app: Flask) -> None:
    """注册所有 API 路由"""
    
    # ---- 健康检查 ----
    @app.route("/api/health", methods=["GET"])
    def health_check():
        """健康检查接口"""
        return jsonify({
            "status": "healthy",
            "service": "PCT Platform API",
            "version": "1.0.0"
        })
    
    # ---- 任务管理 ----
    @app.route("/api/tasks", methods=["GET"])
    def list_tasks():
        """列出最近任务"""
        limit = request.args.get("limit", 20, type=int)
        tasks = list_recent_tasks(limit=min(limit, 100))
        return jsonify({
            "tasks": tasks,
            "total": len(tasks)
        })
    
    @app.route("/api/task/<job_id>", methods=["GET"])
    def get_task(job_id: str):
        """获取单个任务状态"""
        task = get_task_status(job_id)
        if task is None:
            return jsonify({"error": "Task not found"}), 404
        return jsonify(task)
    
    @app.route("/api/task/<job_id>/progress", methods=["GET"])
    def get_task_progress(job_id: str):
        """获取任务进度（简化版）"""
        task = TASK_STORE.get_task(job_id)
        if task is None:
            return jsonify({"error": "Task not found"}), 404
        
        return jsonify({
            "job_id": task.job_id,
            "status": task.status.value,
            "progress": round(task.progress * 100, 1),
            "processed": task.processed,
            "total": task.total,
            "success_count": task.success_count,
            "fail_count": task.fail_count,
            "start_time": task.start_time,
            "end_time": task.end_time,
        })
    
    @app.route("/api/task/<job_id>/cancel", methods=["POST"])
    def cancel_task(job_id: str):
        """取消任务（标记为取消状态）"""
        task = TASK_STORE.get_task(job_id)
        if task is None:
            return jsonify({"error": "Task not found"}), 404
        
        if task.status == TaskStatus.COMPLETED:
            return jsonify({"error": "Cannot cancel completed task"}), 400
        
        TASK_STORE.update_task(job_id, status=TaskStatus.CANCELLED)
        return jsonify({
            "job_id": job_id,
            "status": "cancelled",
            "message": "Task cancellation requested"
        })
    
    # ---- 批量预测 API ----
    @app.route("/api/batch/submit", methods=["POST"])
    def api_batch_submit():
        """
        提交批量预测任务
        
        Request (multipart/form-data):
            file: CSV file with 'formula' column
            temperature: float (optional, default 298.0)
        
        Returns:
            job_id: str
            status: str
        """
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "Empty filename"}), 400
        
        if not file.filename.endswith(".csv"):
            return jsonify({"error": "Only .csv files allowed"}), 400
        
        # 获取参数
        temperature = request.form.get("temperature", 298.0, type=float)
        
        # 保存上传文件
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        import uuid
        job_id = str(uuid.uuid4())[:8]
        file_path = upload_dir / f"{job_id}_{file.filename}"
        file.save(file_path)
        
        # 提交任务
        task_id = submit_batch_task(
            input_file=str(file_path),
            temperature=temperature,
        )
        
        return jsonify({
            "job_id": task_id,
            "status": "submitted",
            "message": "Batch prediction task submitted"
        })
    
    @app.route("/api/batch/<job_id>/download", methods=["GET"])
    def api_batch_download(job_id: str):
        """
        下载批量预测结果
        
        Query params:
            type: 'full' or 'filtered' (default 'filtered')
        """
        task = TASK_STORE.get_task(job_id)
        if task is None:
            return jsonify({"error": "Task not found"}), 404
        
        if task.status != TaskStatus.COMPLETED:
            return jsonify({"error": "Task not completed yet"}), 400
        
        download_type = request.args.get("type", "filtered")
        if download_type == "full":
            filename = "full_predictions.csv"
        else:
            filename = "filtered_candidates.csv"
        
        file_path = Path(task.output_dir) / filename if task.output_dir else None
        if file_path is None or not file_path.exists():
            return jsonify({"error": f"File {filename} not found"}), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )
    
    # ---- 预测单点材料 ----
    @app.route("/api/predict", methods=["POST"])
    def api_predict():
        """
        预测单个材料的热力学性质
        
        Request JSON:
            formula: str (required)
            V0: float (optional, default 293.0)
            temperature: float (optional, default 298.0)
        """
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        
        formula = data.get("formula")
        if not formula:
            return jsonify({"error": "Missing 'formula'"}), 400
        
        V0 = data.get("V0", 293.0)
        temperature = data.get("temperature", 298.0)
        
        try:
            from pct_app.ui.predictor import predict_full
            result = predict_full(formula, V0=V0, temperature=temperature)
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # ---- 静态文件服务 (批量输出目录) ----
    @app.route("/download/<path:filepath>", methods=["GET"])
    def download_file(filepath: str):
        """通用文件下载接口"""
        from pct_app.config.paths import ASSETS_DIR
        file_path = ASSETS_DIR / "batch_outputs" / filepath
        
        # 安全检查
        try:
            file_path = file_path.resolve()
            base_path = ASSETS_DIR.resolve()
            if not str(file_path).startswith(str(base_path)):
                return jsonify({"error": "Access denied"}), 403
        except Exception:
            return jsonify({"error": "Invalid path"}), 400
        
        if not file_path.exists():
            return jsonify({"error": "File not found"}), 404
        
        return send_file(file_path, as_attachment=True)
    
    # ---- 错误处理 ----
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Endpoint not found"}), 404
    
    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error"}), 500


# ============================================================
# 应用入口
# ============================================================
def run_api_server(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    """启动 API 服务器"""
    app = create_app()
    print(f"\n🚀 Starting PCT API Server on {host}:{port}")
    print(f"   - Task status: GET  http://{host}:{port}/api/task/<job_id>")
    print(f"   - Batch submit: POST http://{host}:{port}/api/batch/submit")
    print(f"   - Single predict: POST http://{host}:{port}/api/predict")
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PCT Platform API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host address")
    parser.add_argument("--port", default=5000, type=int, help="Port number")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    run_api_server(host=args.host, port=args.port, debug=args.debug)
