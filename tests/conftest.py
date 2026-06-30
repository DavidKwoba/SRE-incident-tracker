import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from apps.accounts.models import Team, User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def team(db):
    return Team.objects.create(name="Data Team", slug="data-team", email="data@example.com")


@pytest.fixture
def reporter_user(db, team):
    user = User.objects.create_user(
        username="reporter", email="reporter@example.com", password="testpass123"
    )
    user.teams.add(team)
    return user


@pytest.fixture
def platform_engineer(db):
    group, _ = Group.objects.get_or_create(name="platform_engineer")
    user = User.objects.create_user(
        username="engineer", email="engineer@example.com", password="testpass123"
    )
    user.groups.add(group)
    return user


@pytest.fixture
def platform_admin(db):
    group, _ = Group.objects.get_or_create(name="platform_admin")
    user = User.objects.create_user(
        username="admin", email="admin@example.com", password="testpass123"
    )
    user.groups.add(group)
    return user


@pytest.fixture
def auth_client(api_client, reporter_user):
    api_client.force_authenticate(user=reporter_user)
    return api_client


@pytest.fixture
def engineer_client(api_client, platform_engineer):
    api_client.force_authenticate(user=platform_engineer)
    return api_client


@pytest.fixture
def admin_client(api_client, platform_admin):
    api_client.force_authenticate(user=platform_admin)
    return api_client
