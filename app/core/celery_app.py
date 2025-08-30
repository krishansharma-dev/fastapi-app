from celery import Celery
from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "news_processor",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.news_tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_routes={
        "app.tasks.news_tasks.process_article_approval": {"queue": "approval"},
        "app.tasks.news_tasks.categorize_article": {"queue": "categorization"},
    },
)
