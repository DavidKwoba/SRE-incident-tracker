import pytest
from unittest.mock import patch

from apps.incidents.models import Incident
from apps.incidents.tasks import check_sla_breaches, close_stale_incidents


def make_incident(reporter, team, **kwargs):
    return Incident.objects.create(
        title="Test incident",
        description="Test",
        priority=kwargs.pop("priority", "P3"),
        reporter=reporter,
        reporting_team=team,
        **kwargs,
    )


@pytest.mark.django_db
class TestCheckSLABreaches:
    def test_flags_overdue_open_incidents(self, reporter_user, team):
        from django.utils import timezone
        from datetime import timedelta

        incident = make_incident(reporter_user, team)
        incident.resolution_due_at = timezone.now() - timedelta(hours=1)
        incident.save()

        with patch("apps.incidents.tasks.send_sla_breach_notification") as mock_notify:
            mock_notify.delay = mock_notify
            check_sla_breaches()

        incident.refresh_from_db()
        assert incident.sla_breached is True

    def test_does_not_re_flag_already_breached(self, reporter_user, team):
        from django.utils import timezone
        from datetime import timedelta

        incident = make_incident(reporter_user, team, sla_breached=True)
        incident.resolution_due_at = timezone.now() - timedelta(hours=2)
        incident.save()

        with patch("apps.incidents.tasks.send_sla_breach_notification") as mock_notify:
            check_sla_breaches()
            mock_notify.delay.assert_not_called()

    def test_does_not_flag_resolved_incidents(self, reporter_user, team):
        from django.utils import timezone
        from datetime import timedelta

        incident = make_incident(reporter_user, team, status=Incident.Status.RESOLVED)
        incident.resolution_due_at = timezone.now() - timedelta(hours=1)
        incident.save()

        check_sla_breaches()
        incident.refresh_from_db()
        assert incident.sla_breached is False


@pytest.mark.django_db
class TestCloseStaleIncidents:
    def test_closes_resolved_incidents_older_than_30_days(self, reporter_user, team):
        from django.utils import timezone
        from datetime import timedelta

        incident = make_incident(reporter_user, team, status=Incident.Status.RESOLVED)
        incident.resolved_at = timezone.now() - timedelta(days=31)
        incident.save()

        close_stale_incidents()
        incident.refresh_from_db()
        assert incident.status == Incident.Status.CLOSED

    def test_does_not_close_recently_resolved(self, reporter_user, team):
        from django.utils import timezone
        from datetime import timedelta

        incident = make_incident(reporter_user, team, status=Incident.Status.RESOLVED)
        incident.resolved_at = timezone.now() - timedelta(days=5)
        incident.save()

        close_stale_incidents()
        incident.refresh_from_db()
        assert incident.status == Incident.Status.RESOLVED
