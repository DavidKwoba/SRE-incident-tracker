import logging

from django.conf import settings

logger = logging.getLogger(__name__)

PRIORITY_EMOJI = {"P1": "🔴", "P2": "🟠", "P3": "🟡", "P4": "🟢"}


def _client():
    from slack_sdk import WebClient
    return WebClient(token=settings.SLACK_BOT_TOKEN)


def _post(channel: str, text: str, blocks: list | None = None):
    if not getattr(settings, "SLACK_BOT_TOKEN", ""):
        return
    try:
        kwargs = {"channel": channel, "text": text}
        if blocks:
            kwargs["blocks"] = blocks
        _client().chat_postMessage(**kwargs)
    except Exception as exc:
        logger.warning("Slack post to %s failed: %s", channel, exc)


def _blocks(incident, header: str) -> list:
    emoji = PRIORITY_EMOJI.get(incident.priority, "⚪")
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{emoji} {header}"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Title:*\n{incident.title}"},
                {"type": "mrkdwn", "text": f"*Priority:*\n{incident.get_priority_display()}"},
                {"type": "mrkdwn", "text": f"*Status:*\n{incident.get_status_display()}"},
                {"type": "mrkdwn", "text": f"*Reporting Team:*\n{incident.reporting_team.name}"},
            ],
        },
    ]


def post_incident_created(incident):
    central = getattr(settings, "SLACK_PLATFORM_INCIDENTS_CHANNEL", "#platform-incidents")
    header = f"New Incident #{incident.pk}: {incident.title}"
    _post(central, header, _blocks(incident, header))
    team_channel = incident.reporting_team.slack_channel
    if team_channel and team_channel != central:
        _post(team_channel, f"Your team raised an incident: {incident.title}", _blocks(incident, header))


def post_status_change(incident, previous_status: str, new_status: str):
    central = getattr(settings, "SLACK_PLATFORM_INCIDENTS_CHANNEL", "#platform-incidents")
    header = f"Incident #{incident.pk} — Status: {previous_status} → {new_status}"
    _post(central, header, _blocks(incident, header))


def post_sla_breach(incident):
    central = getattr(settings, "SLACK_PLATFORM_INCIDENTS_CHANNEL", "#platform-incidents")
    header = f"SLA Breach — Incident #{incident.pk}: {incident.title}"
    _post(central, header, _blocks(incident, header))
