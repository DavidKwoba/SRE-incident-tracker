import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestTeamEndpoints:
    def test_list_teams_requires_auth(self, api_client):
        response = api_client.get(reverse("team-list"))
        assert response.status_code == 401

    def test_authenticated_user_can_list_teams(self, auth_client, team):
        response = auth_client.get(reverse("team-list"))
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_only_admin_can_create_team(self, auth_client, admin_client):
        payload = {"name": "New Team", "slug": "new-team", "email": "new@example.com"}
        assert auth_client.post(reverse("team-list"), payload).status_code == 403
        assert admin_client.post(reverse("team-list"), payload).status_code == 201


@pytest.mark.django_db
class TestUserMeEndpoint:
    def test_me_returns_current_user(self, auth_client, reporter_user):
        response = auth_client.get(reverse("user-me"))
        assert response.status_code == 200
        assert response.data["username"] == reporter_user.username

    def test_me_patch_updates_profile(self, auth_client):
        response = auth_client.patch(
            reverse("user-me"), {"phone": "+254700000000"}, format="json"
        )
        assert response.status_code == 200
        assert response.data["phone"] == "+254700000000"
