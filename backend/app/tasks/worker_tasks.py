from ...celery import example_task as celery_example_task


def enqueue_example(data):
    """Local wrapper to enqueue the example task. In Phase 3 this will be used
    by the API to push batch jobs to workers.
    """
    return celery_example_task.delay(data)
