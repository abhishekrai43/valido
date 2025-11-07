"""
local_worker.py - Single-process task runner replacing Celery for Windows-native deployment.

This module provides an in-memory task registry and async processing for single-machine installs.
"""

import asyncio
import threading
import time
from typing import Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
import uuid

from app.tasks.worker_tasks import process_pdfs_sync
from app.tasks.cleanup import cleanup_old_results
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LocalWorker:
    """In-memory task registry for single-process execution."""

    def __init__(self, max_workers: int = 4):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="valido-worker")
        self._shutdown = False
        logger.info(f"LocalWorker initialized with {max_workers} max workers")

    def submit_task(self, task_type: str, task_id: Optional[str] = None, **kwargs) -> str:
        """Submit a task for execution. Returns task ID."""
        if task_id is None:
            task_id = str(uuid.uuid4())
        self.tasks[task_id] = {
            "id": task_id,
            "type": task_type,
            "status": "PROGRESS",  # Set to PROGRESS immediately so frontend shows processing
            "kwargs": kwargs,
            "result": {"processed": 0, "total": 0, "current_file": "", "percent": 0},  # Initialize progress info
            "error": None,
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        logger.info(f"Submitted task {task_id} of type {task_type}")

        # Submit to thread pool
        self.executor.submit(self._execute_task, task_id)
        return task_id

    def _execute_task(self, task_id: str):
        """Execute a task in a worker thread."""
        task = self.tasks.get(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return

        try:
            task["status"] = "PROGRESS"
            task["updated_at"] = time.time()
            logger.info(f"Starting task {task_id}")

            # Create a progress callback that updates the in-memory task entry
            def _progress_cb(state: str, meta: Dict[str, Any]):
                try:
                    # When progress updates are emitted, keep status as PROGRESS
                    if state:
                        task["status"] = state
                    # Merge meta into task.result so frontend can read processed/total/current_file
                    if meta and isinstance(meta, dict):
                        # Keep existing result dict and update keys
                        existing = task.get("result") or {}
                        if not isinstance(existing, dict):
                            existing = {"result": existing}
                        existing.update(meta)
                        task["result"] = existing
                    task["updated_at"] = time.time()
                except Exception:
                    pass

            if task["type"] == "process_pdfs":
                # Pass the callback so process_pdfs_sync can emit live progress
                kwargs = dict(task["kwargs"])
                kwargs["progress_callback"] = _progress_cb
                result = process_pdfs_sync(**kwargs)
            elif task["type"] == "cleanup_old_results":
                result = cleanup_old_results(**task["kwargs"])
            else:
                raise ValueError(f"Unknown task type: {task['type']}")

            task["status"] = "SUCCESS"
            task["result"] = result
            logger.info(f"Task {task_id} completed successfully")

        except Exception as e:
            task["status"] = "FAILURE"
            task["error"] = str(e)
            logger.error(f"Task {task_id} failed: {e}")

        task["updated_at"] = time.time()

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status by ID."""
        return self.tasks.get(task_id)

    def shutdown(self):
        """Shutdown the worker."""
        logger.info("Shutting down LocalWorker")
        self._shutdown = True
        self.executor.shutdown(wait=True)


# Global worker instance
_worker_instance: Optional[LocalWorker] = None


def get_worker() -> LocalWorker:
    """Get or create the global worker instance."""
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = LocalWorker()
    return _worker_instance


def submit_task(task_type: str, task_id: Optional[str] = None, **kwargs) -> str:
    """Submit a task to the local worker."""
    return get_worker().submit_task(task_type, task_id=task_id, **kwargs)


def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get task status from the local worker."""
    return get_worker().get_task_status(task_id)


def shutdown_worker():
    """Shutdown the global worker."""
    global _worker_instance
    if _worker_instance:
        _worker_instance.shutdown()
        _worker_instance = None