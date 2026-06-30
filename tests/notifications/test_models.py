import pytest

from apps.incidents.models import Incident
from apps.notifications.models import NotificationLog


@pytest.mark.django_db
class TestNotificationLog:
    def test_str(self, reporter_user, team):
        incident = Incident.objects.create(
            title="Test", description="Test", priority="P3",
            reporter=reporter_user, reporting_team=team,
        )
        log = NotificationLog.objects.create(
            incident=incident,
            channel=NotificationLog.Channel.EMAIL,
            recipient="test@example.com",
            event="incident_created",
        )
        assert "email" in str(log)
        assert "test@example.com" in str(log)

    def test_default_status_is_pending(self, reporter_user, team):
        incident = Incident.objects.create(
            title="Test", description="Test", priority="P3",
            reporter=reporter_user, reporting_team=team,
        )
        log = NotificationLog.objects.create(
            incident=incident,
            channel=NotificationLog.Channel.SLACK,
            recipient="#platform-incidents",
            event="incident_created",
        )
        assert log.status == NotificationLog.DeliveryStatus.PENDING
