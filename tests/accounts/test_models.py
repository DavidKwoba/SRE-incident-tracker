import pytest

from apps.accounts.models import Team, User


@pytest.mark.django_db
class TestTeamModel:
    def test_str(self, team):
        assert str(team) == "Data Team"

    def test_user_can_belong_to_multiple_teams(self, db):
        t1 = Team.objects.create(name="Team A", slug="team-a", email="a@example.com")
        t2 = Team.objects.create(name="Team B", slug="team-b", email="b@example.com")
        user = User.objects.create_user(username="u", email="u@example.com", password="pass")
        user.teams.add(t1, t2)
        assert user.teams.count() == 2

    def test_team_ordering_by_name(self, db):
        Team.objects.create(name="Zebra", slug="zebra", email="z@example.com")
        Team.objects.create(name="Alpha", slug="alpha", email="a@example.com")
        names = list(Team.objects.values_list("name", flat=True))
        assert names == sorted(names)


@pytest.mark.django_db
class TestUserModel:
    def test_str_returns_full_name_when_set(self, db):
        user = User.objects.create_user(
            username="jdoe", first_name="John", last_name="Doe",
            email="j@example.com", password="pass",
        )
        assert str(user) == "John Doe"

    def test_str_falls_back_to_username(self, db):
        user = User.objects.create_user(username="jdoe", email="j@example.com", password="pass")
        assert str(user) == "jdoe"
