import os
from celery import Celery
from celery.schedules import crontab

# Read broker/result backend from environment (works locally or in Docker)
broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

# Create Celery app
celery_app = Celery("pdf_validator", broker=broker_url, backend=result_backend)

# Tuning defaults suitable for local development and small-scale runs.
# These are conservative defaults; override via environment variables in production.
celery_app.conf.update(
    broker_url=broker_url,
    result_backend=result_backend,
    task_acks_late=True,  # ensure tasks are acknowledged after successful execution
    worker_prefetch_multiplier=int(os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", "1")),
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_default_queue="default",
    worker_max_tasks_per_child=int(os.getenv("CELERY_WORKER_MAX_TASKS_PER_CHILD", "100")),
    task_track_started=True,
)

# Import (or attempt to import) project tasks so they are registered when this module is imported.
# We try a best-effort import path that matches the layout under `backend/app/tasks`.
try:
    # Prefer the package path used by the FastAPI app
    import app.tasks.worker_tasks  # noqa: F401
    # Also attempt to import cleanup task so it's registered for beat
    try:
        import app.tasks.cleanup  # noqa: F401
    except Exception:
        pass
except Exception:
    try:
        # Fallback to import relative to backend package
        import backend.app.tasks.worker_tasks  # noqa: F401
        try:
            import backend.app.tasks.cleanup  # noqa: F401
        except Exception:
            pass
    except Exception:
        # If imports fail, tasks can still be registered when worker modules are explicitly imported.
        pass

# Schedule periodic jobs (run cleanup once daily at 02:00 UTC by default)
celery_app.conf.beat_schedule = {
    'cleanup-old-results-daily': {
        'task': 'backend.app.tasks.cleanup.cleanup_old_results',
        'schedule': crontab(hour=2, minute=0),
        'args': (7,),
    },
}

# Small helper: a lightweight example task that demonstrates chunked processing.
@celery_app.task(bind=True)
def process_in_chunks(self, items, chunk_size: int = 100):
    """Process a list of `items` in chunks and report progress.

    This function demonstrates a single-task chunked-processing approach (no subtask spawning).
    It updates task state with progress metadata so callers can poll the result for progress.
    """
    total = len(items or [])
    processed = 0
    results = []

    for start in range(0, total, chunk_size):
        chunk = items[start : start + chunk_size]
        # Replace the following with the real per-item processing function.
        chunk_result = [len(x) if isinstance(x, (str, bytes)) else 1 for x in chunk]
        results.extend(chunk_result)
        processed += len(chunk)
        # Publish a lightweight progress update
        try:
            self.update_state(state="PROGRESS", meta={"processed": processed, "total": total})
        except Exception:
            # Best-effort: update_state may fail depending on backend/config; ignore to keep processing.
            pass

    return {"status": "completed", "total": total, "processed": processed, "sample": results[:10]}
