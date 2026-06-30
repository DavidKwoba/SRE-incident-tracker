from rest_framework import serializers

from .models import Incident, IncidentUpdate, Label
from .sla import calculate_sla_deadlines


class LabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = ["id", "name", "color"]
        read_only_fields = ["id"]


class IncidentUpdateSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = IncidentUpdate
        fields = [
            "id", "update_type", "body", "previous_value", "new_value",
            "author", "author_name", "created_at",
        ]
        read_only_fields = [
            "id", "author", "author_name",
            "previous_value", "new_value", "created_at",
        ]

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.username


class IncidentSerializer(serializers.ModelSerializer):
    labels = LabelSerializer(many=True, read_only=True)
    label_ids = serializers.PrimaryKeyRelatedField(
        queryset=Label.objects.all(),
        many=True,
        write_only=True,
        source="labels",
        required=False,
    )
    reporter_name = serializers.SerializerMethodField()
    assignee_name = serializers.SerializerMethodField()
    reporting_team_name = serializers.CharField(source="reporting_team.name", read_only=True)

    class Meta:
        model = Incident
        fields = [
            "id", "title", "description", "type", "priority", "status",
            "reporter", "reporter_name",
            "reporting_team", "reporting_team_name",
            "assignee", "assignee_name",
            "labels", "label_ids",
            "affected_service", "external_ref",
            "created_at", "updated_at",
            "triaged_at", "resolved_at", "closed_at",
            "response_due_at", "resolution_due_at", "sla_breached",
        ]
        read_only_fields = [
            "id", "reporter", "reporter_name",
            "reporting_team_name", "assignee_name",
            "created_at", "updated_at",
            "triaged_at", "resolved_at", "closed_at",
            "response_due_at", "resolution_due_at", "sla_breached",
        ]

    def get_reporter_name(self, obj):
        return obj.reporter.get_full_name() or obj.reporter.username

    def get_assignee_name(self, obj):
        if obj.assignee:
            return obj.assignee.get_full_name() or obj.assignee.username
        return None

    def create(self, validated_data):
        deadlines = calculate_sla_deadlines(validated_data["priority"])
        validated_data.update(deadlines)
        return super().create(validated_data)


class IncidentTriageSerializer(serializers.Serializer):
    assignee_id = serializers.IntegerField()
    note = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_assignee_id(self, value):
        from apps.accounts.models import User
        try:
            return User.objects.get(pk=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")


class IncidentResolveSerializer(serializers.Serializer):
    resolution_notes = serializers.CharField()


class IncidentCloseSerializer(serializers.Serializer):
    resolution_summary = serializers.CharField()


class IncidentReopenSerializer(serializers.Serializer):
    reason = serializers.CharField()
