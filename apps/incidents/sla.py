from datetime import timedelta

from django.utils import timezone

SLA_WINDOWS = {
    "P1": {"response": timedelta(minutes=15), "resolution": timedelta(hours=1)},
    "P2": {"response": timedelta(hours=1), "resolution": timedelta(hours=4)},
    "P3": {"response": timedelta(hours=4), "resolution": timedelta(hours=24)},
    "P4": {"response": timedelta(hours=24), "resolution": timedelta(hours=72)},
}


def calculate_sla_deadlines(priority: str, created_at=None) -> dict:
    now = created_at or timezone.now()
    window = SLA_WINDOWS.get(priority, SLA_WINDOWS["P3"])
    return {
        "response_due_at": now + window["response"],
        "resolution_due_at": now + window["resolution"],
    }
