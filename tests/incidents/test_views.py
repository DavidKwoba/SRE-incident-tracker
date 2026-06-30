import pytest
from django.urls import reverse

from apps.incidents.models import Incident


def make_incident(reporter, team, priority="P3"):
    return Incident.objects.create(
        title="DB unreachable",
        description="Primary postgres stopped responding",
        priority=priority,
        reporter=reporter,
        reporting_team=team,
    )


@pytest.mark.django_db
class TestIncidentCreate:
    def test_reporter_can_create(self, auth_client, team):
        payload = {
            "title": "Service down",
            "description": "Nothing works",
            "priority": "P2",
            "type": "incident",
            "reporting_team": team.pk,
        }
        response = auth_client.post(reverse("incident-list"), payload, format="json")
        assert response.status_code == 201
        assert response.data["priority"] == "P2"

    def test_sla_deadlines_populated_on_create(self, auth_client, team):
        payload = {
            "title": "T", "description": "D", "priority": "P1",
            "type": "incident", "reporting_team": team.pk,
        }
        response = auth_client.post(reverse("incident-list"), payload, format="json")
        assert response.status_code == 201
        assert response.data["response_due_at"] is not None
        assert response.data["resolution_due_at"] is not None

    def test_unauthenticated_cannot_create(self, api_client, team):
        response = api_client.post(
            reverse("incident-list"),
            {"title": "T", "description": "D", "priority": "P3", "reporting_team": team.pk},
        )
        assert response.status_code == 401


@pytest.mark.django_db
class TestIncidentLifecycle:
    def test_engineer_can_triage(self, engineer_client, reporter_user, team, platform_engineer):
        incident = make_incident(reporter_user, team)
        url = reverse("incident-triage", kwargs={"pk": incident.pk})
        response = engineer_client.post(
            url, {"assignee_id": platform_engineer.pk}, format="json"
        )
        assert response.status_code == 200
        incident.refresh_from_db()
        assert incident.status == Incident.Status.TRIAGED
        assert incident.assignee == platform_engineer

    def test_reporter_cannot_triage(self, auth_client, reporter_user, team):
        incident = make_incident(reporter_user, team)
        url = reverse("incident-triage", kwargs={"pk": incident.pk})
        response = auth_client.post(url, {"assignee_id": reporter_user.pk}, format="json")
        assert response.status_code == 403

    def test_engineer_can_resolve(self, engineer_client, reporter_user, team):
        incident = make_incident(reporter_user, team)
        url = reverse("incident-resolve", kwargs={"pk": incident.pk})
        response = engineer_client.post(
            url, {"resolution_notes": "Fixed by restarting postgres"}, format="json"
        )
        assert response.status_code == 200
        incident.refresh_from_db()
        assert incident.status == Incident.Status.RESOLVED
        assert incident.resolved_at is not None

    def test_reopen_clears_resolved_at(self, engineer_client, reporter_user, team):
        from django.utils import timezone
        incident = make_incident(reporter_user, team)
        incident.status = Incident.Status.RESOLVED
        incident.resolved_at = timezone.now()
        incident.save()

        url = reverse("incident-reopen", kwargs={"pk": incident.pk})
        response = engineer_client.post(url, {"reason": "Problem recurred"}, format="json")
        assert response.status_code == 200
        incident.refresh_from_db()
        assert incident.status == Incident.Status.OPEN
        assert incident.resolved_at is None


@pytest.mark.django_db
class TestIncidentFilters:
    def test_filter_by_priority(self, auth_client, reporter_user, team):
        make_incident(reporter_user, team, priority="P1")
        make_incident(reporter_user, team, priority="P4")
        response = auth_client.get(reverse("incident-list") + "?priority=P1")
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_search_by_title(self, auth_client, reporter_user, team):
        make_incident(reporter_user, team)
        response = auth_client.get(reverse("incident-list") + "?search=DB+unreachable")
        assert response.status_code == 200
        assert response.data["count"] == 1
