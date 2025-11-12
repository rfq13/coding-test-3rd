"""
Celery application setup
"""
from celery import Celery
from app.core.config import settings


# Use Redis for broker and result backend (from settings)
celery_app = Celery(
    "fund_analysis",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Basic config
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Autodiscover tasks under app.tasks
celery_app.autodiscover_tasks(["app.tasks"])

# Ensure tasks modules are imported so registration occurs
try:
    import app.tasks.documents  # noqa: F401
except Exception:
    # In case of import issues during startup, Celery will still run but tasks won't be discovered.
    # Logs will indicate unregistered tasks; fix import paths if that happens.
    pass