"""
Celery Application Configuration
Background task queue for asynchronous operations
"""
from celery import Celery
import os

# Create Celery app
celery_app = Celery(
    "examstutor",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    include=[
        "src.tasks.ai_tasks",
        "src.tasks.email_tasks",
        "src.tasks.analytics_tasks",
        "src.tasks.feedback_tasks"  # NEW: Feedback processing tasks
    ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    broker_connection_retry_on_startup=True,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Existing tasks
    "cleanup-old-sessions": {
        "task": "src.tasks.analytics_tasks.cleanup_old_sessions",
        "schedule": 3600.0,  # Every hour
    },
    "update-subscription-status": {
        "task": "src.tasks.analytics_tasks.update_subscription_status",
        "schedule": 86400.0,  # Every day
    },
    "generate-daily-analytics": {
        "task": "src.tasks.analytics_tasks.generate_daily_analytics",
        "schedule": 86400.0,  # Every day at midnight
    },

    # NEW: Feedback-related tasks
    "generate-feedback-analytics": {
        "task": "src.tasks.analytics_tasks.generate_feedback_analytics",
        "schedule": 86400.0,  # Every day at midnight
    },
    "identify-problem-areas": {
        "task": "src.tasks.analytics_tasks.identify_problem_areas",
        "schedule": 604800.0,  # Every week (7 days)
    },
    "process-unprocessed-feedback": {
        "task": "src.tasks.feedback_tasks.process_unprocessed_feedback",
        "schedule": 1800.0,  # Every 30 minutes
    },
    "invalidate-poor-response-cache": {
        "task": "src.tasks.feedback_tasks.invalidate_poor_response_cache",
        "schedule": 3600.0,  # Every hour
    },
    "detect-feedback-patterns": {
        "task": "src.tasks.feedback_tasks.detect_feedback_patterns",
        "schedule": 21600.0,  # Every 6 hours
    },
    "prepare-finetuning-data": {
        "task": "src.tasks.feedback_tasks.prepare_finetuning_data",
        "schedule": 604800.0,  # Every week (7 days)
    },
    "generate-weekly-feedback-report": {
        "task": "src.tasks.feedback_tasks.generate_weekly_feedback_report",
        "schedule": 604800.0,  # Every week (7 days)
    },
}

if __name__ == "__main__":
    celery_app.start()
