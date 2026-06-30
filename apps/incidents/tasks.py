from celery import shared_task
from django.utils import timezone


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_incident_created_notification(self, incident_id: int):
    try:
        from apps.incidents.models import Incident
        from apps.notifications.email import send_incident_created_email
        from apps.notifications.slack import post_incident_created

        incident = (
            Incident.objects
            .select_related("reporter", "reporting_team", "assignee")
            .get(pk=incident_id)
        )
        send_incident_created_email(incident)
        post_incident_created(incident)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_status_change_notification(self, incident_id: int, previous_status: str, new_status: str):
    try:
        from apps.incidents.models import Incident
        from apps.notifications.email import send_status_change_email
        from apps.notifications.slack import post_status_change

        incident = (
            Incident.objects
            .select_related("reporter", "reporting_team", "assignee")
            .get(pk=incident_id)
        )
        send_status_change_email(incident, previous_status, new_status)
        post_status_change(incident, previous_status, new_status)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_comment_notification(self, incident_id: int, update_id: int):
    try:
        from apps.incidents.models import Incident, IncidentUpdate
        from apps.notifications.email import send_comment_email

        incident = (
            Incident.objects
            .select_related("reporter", "reporting_team", "assignee")
            .get(pk=incident_id)
        )
        update = IncidentUpdate.objects.select_related("author").get(pk=update_id)
        send_comment_email(incident, update)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_sla_breach_notification(self, incident_id: int):
    try:
        from apps.incidents.models import Incident
        from apps.notifications.email import send_sla_breach_email
        from apps.notifications.slack import post_sla_breach

        incident = (
            Incident.objects
            .select_related("reporter", "reporting_team", "assignee")
            .get(pk=incident_id)
        )
        send_sla_breach_email(incident)
        post_sla_breach(incident)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def check_sla_breaches():
    from apps.incidents.models import Incident

    now = timezone.now()
    breached_qs = Incident.objects.filter(
        status__in=[
            Incident.Status.OPEN,
            Incident.Status.TRIAGED,
            Incident.Status.IN_PROGRESS,
        ],
        resolution_due_at__lt=now,
        sla_breached=False,
    )
    for incident in breached_qs:
        incident.sla_breached = True
        incident.save(update_fields=["sla_breached"])
        send_sla_breach_notification.delay(incident.pk)


@shared_task
def send_daily_digest():
    from apps.incidents.models import Incident
    from apps.notifications.email import send_daily_digest_email

    open_incidents = list(
        Incident.objects
        .filter(
            status__in=[
                Incident.Status.OPEN,
                Incident.Status.TRIAGED,
                Incident.Status.IN_PROGRESS,
            ]
        )
        .select_related("reporter", "reporting_team", "assignee")
        .order_by("priority", "-created_at")
    )
    send_daily_digest_email(open_incidents)


@shared_task
def close_stale_incidents():
    from datetime import timedelta
    from apps.incidents.models import Incident

    cutoff = timezone.now() - timedelta(days=30)
    Incident.objects.filter(
        status=Incident.Status.RESOLVED,
        resolved_at__lt=cutoff,
    ).update(status=Incident.Status.CLOSED, closed_at=timezone.now())
