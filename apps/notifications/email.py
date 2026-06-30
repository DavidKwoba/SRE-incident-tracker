import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from .models import NotificationLog

logger = logging.getLogger(__name__)


def _incident_recipients(incident) -> list[str]:
    seen = set()
    recipients = []
    for email in [
        incident.reporter.email,
        incident.reporting_team.email,
        incident.assignee.email if incident.assignee else None,
    ]:
        if email and email not in seen:
            seen.add(email)
            recipients.append(email)
    return recipients


def _send(incident, event: str, subject: str, template: str, context: dict, recipients: list[str]):
    for recipient in recipients:
        log = NotificationLog.objects.create(
            incident=incident,
            channel=NotificationLog.Channel.EMAIL,
            recipient=recipient,
            event=event,
        )
        try:
            html_body = render_to_string(f"emails/{template}", context)
            msg = EmailMultiAlternatives(
                subject=subject,
                body=html_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient],
            )
            msg.attach_alternative(html_body, "text/html")
            msg.send()
            log.status = NotificationLog.DeliveryStatus.SENT
            log.sent_at = timezone.now()
        except Exception as exc:
            logger.warning("Email delivery failed to %s: %s", recipient, exc)
            log.status = NotificationLog.DeliveryStatus.FAILED
            log.error = str(exc)
        finally:
            log.save(update_fields=["status", "sent_at", "error"])


def send_incident_created_email(incident):
    _send(
        incident=incident,
        event="incident_created",
        subject=f"[{incident.priority}] New Incident: {incident.title}",
        template="incident_created.html",
        context={"incident": incident, "base_url": getattr(settings, "FRONTEND_BASE_URL", "")},
        recipients=_incident_recipients(incident),
    )


def send_status_change_email(incident, previous_status: str, new_status: str):
    _send(
        incident=incident,
        event="status_changed",
        subject=f"[{incident.priority}] Incident Updated: {incident.title}",
        template="status_changed.html",
        context={"incident": incident, "previous_status": previous_status, "new_status": new_status},
        recipients=_incident_recipients(incident),
    )


def send_comment_email(incident, update):
    _send(
        incident=incident,
        event="comment_added",
        subject=f"[{incident.priority}] New Comment: {incident.title}",
        template="status_changed.html",
        context={"incident": incident, "update": update},
        recipients=_incident_recipients(incident),
    )


def send_sla_breach_email(incident):
    recipients = _incident_recipients(incident)
    platform_email = getattr(settings, "PLATFORM_TEAM_EMAIL", "")
    if platform_email and platform_email not in recipients:
        recipients.append(platform_email)
    _send(
        incident=incident,
        event="sla_breach",
        subject=f"[SLA BREACH][{incident.priority}] {incident.title}",
        template="sla_breach.html",
        context={"incident": incident},
        recipients=recipients,
    )


def send_daily_digest_email(incidents: list):
    from apps.accounts.models import User

    if not incidents:
        return

    engineers = User.objects.filter(
        groups__name__in=["platform_engineer", "platform_admin"],
        is_active=True,
    ).values_list("email", flat=True).distinct()

    for email in engineers:
        if not email:
            continue
        try:
            html_body = render_to_string("emails/daily_digest.html", {"incidents": incidents})
            msg = EmailMultiAlternatives(
                subject="Platform Incident Tracker — Daily Digest",
                body=html_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
            )
            msg.attach_alternative(html_body, "text/html")
            msg.send()
        except Exception as exc:
            logger.warning("Daily digest delivery failed to %s: %s", email, exc)
