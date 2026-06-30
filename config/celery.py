import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("incident_tracker")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "check-sla-breaches": {
        "task": "apps.incidents.tasks.check_sla_breaches",
        "schedule": crontab(minute="*/5"),
    },
    "send-daily-digest": {
        "task": "apps.incidents.tasks.send_daily_digest",
        "schedule": crontab(hour=8, minute=0),
    },
    "close-stale-incidents": {
        "task": "apps.incidents.tasks.close_stale_incidents",
        "schedule": crontab(hour=0, minute=0),
    },
}
