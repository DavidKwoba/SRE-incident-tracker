from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Team, User


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["id", "name", "slug", "email", "slack_channel", "created_at"]
        read_only_fields = ["id", "created_at"]


class UserSerializer(serializers.ModelSerializer):
    teams = TeamSerializer(many=True, read_only=True)
    team_ids = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(),
        many=True,
        write_only=True,
        source="teams",
        required=False,
    )

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "teams", "team_ids", "slack_user_id", "phone",
            "is_active", "date_joined",
        ]
        read_only_fields = ["id", "date_joined", "is_active"]


class UserProfileSerializer(serializers.ModelSerializer):
    teams = TeamSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "teams", "slack_user_id", "phone",
        ]
        read_only_fields = ["id", "username"]


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["email"] = user.email
        return token
