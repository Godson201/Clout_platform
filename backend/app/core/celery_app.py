from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "clout",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.video_processing_tasks",
        "app.tasks.payment_reconciliation_tasks",
        "app.tasks.social_metrics_tasks",
        "app.tasks.settlement_tasks",
        "app.tasks.comment_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=settings.CELERY_TASK_ALWAYS_EAGER,
    # Requires a `celery -A app.core.celery_app beat` process running (not yet
    # added to docker-compose.yml) to actually fire on schedule — the tasks
    # themselves work standalone regardless, via the webhook + on-demand
    # GET .../payment poll paths.
    beat_schedule={
        "reconcile-pending-payments": {
            "task": "reconcile_pending_payments",
            "schedule": 300.0,
        },
        "reconcile-pending-payouts": {
            "task": "reconcile_pending_payouts",
            "schedule": 300.0,
        },
        "reconcile-pending-refunds": {
            "task": "reconcile_pending_refunds",
            "schedule": 300.0,
        },
        "poll-active-post-metrics": {
            "task": "poll_all_active_post_metrics",
            "schedule": 600.0,
        },
        "run-auto-settlement": {
            "task": "run_auto_settlement",
            "schedule": 900.0,
        },
        "poll-active-post-comments": {
            "task": "poll_all_active_post_comments",
            "schedule": 600.0,
        },
    },
)
