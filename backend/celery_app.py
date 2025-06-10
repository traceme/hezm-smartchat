from celery import Celery
from config import settings

# Create Celery app
celery_app = Celery(
    "smartchat",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['tasks.document_tasks', 'tasks.vectorization_tasks']
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    result_expires=3600,  # 1 hour
    task_routes={
        'tasks.document_tasks.process_document_task': {'queue': 'document_processing'},
    }
)

# Optional: Configure retry settings
celery_app.conf.task_default_retry_delay = 60  # 1 minute
celery_app.conf.task_max_retries = 3 