from celery import Celery

# Celery configuration stub. Replace broker URL with real Redis/RabbitMQ in Phase 3.
celery_app = Celery("pdf_validator", broker="redis://localhost:6379/0")


@celery_app.task(bind=True)
def example_task(self, data):
    # Minimal task stub demonstrating where batch processing code will run.
    return {"status": "received", "len": len(data or [])}
