from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_api_key.permissions import HasAPIKey

from apps.accounts.permissions import IsPlatformAdmin, IsPlatformEngineer

from .filters import IncidentFilter
from .models import Incident, IncidentUpdate, Label
from .serializers import (
    IncidentCloseSerializer,
    IncidentResolveSerializer,
    IncidentReopenSerializer,
    IncidentSerializer,
    IncidentTriageSerializer,
    IncidentUpdateSerializer,
    LabelSerializer,
)


class LabelViewSet(viewsets.ModelViewSet):
    queryset = Label.objects.all()
    serializer_class = LabelSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsPlatformEngineer()]
        return [IsAuthenticated()]


class IncidentViewSet(viewsets.ModelViewSet):
    queryset = (
        Incident.objects
        .select_related("reporter", "reporting_team", "assignee")
        .prefetch_related("labels")
        .order_by("-created_at")
    )
    serializer_class = IncidentSerializer
    filterset_class = IncidentFilter
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "updated_at", "priority", "status"]

    def get_permissions(self):
        if self.action == "destroy":
            return [IsPlatformAdmin()]
        if self.action in ("triage", "resolve", "close", "reopen"):
            return [IsPlatformEngineer()]
        return [IsAuthenticated() | HasAPIKey()]

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)

    def perform_destroy(self, instance):
        instance.status = Incident.Status.CLOSED
        instance.closed_at = timezone.now()
        instance.save(update_fields=["status", "closed_at"])

    def _record_status_change(self, incident, author, previous_status, body=""):
        IncidentUpdate.objects.create(
            incident=incident,
            author=author,
            update_type=IncidentUpdate.UpdateType.STATUS_CHANGE,
            body=body,
            previous_value=previous_status,
            new_value=incident.status,
        )
        from .tasks import send_status_change_notification
        send_status_change_notification.delay(incident.pk, previous_status, incident.status)

    @action(detail=True, methods=["post"])
    def triage(self, request, pk=None):
        incident = self.get_object()
        serializer = IncidentTriageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        prev = incident.status
        incident.status = Incident.Status.TRIAGED
        incident.assignee = serializer.validated_data["assignee_id"]
        incident.triaged_at = timezone.now()
        incident.save(update_fields=["status", "assignee", "triaged_at"])

        self._record_status_change(incident, request.user, prev, serializer.validated_data["note"])
        return Response(IncidentSerializer(incident, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        incident = self.get_object()
        serializer = IncidentResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        prev = incident.status
        incident.status = Incident.Status.RESOLVED
        incident.resolved_at = timezone.now()
        incident.save(update_fields=["status", "resolved_at"])

        self._record_status_change(
            incident, request.user, prev, serializer.validated_data["resolution_notes"]
        )
        return Response(IncidentSerializer(incident, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        incident = self.get_object()
        serializer = IncidentCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        prev = incident.status
        incident.status = Incident.Status.CLOSED
        incident.closed_at = timezone.now()
        incident.save(update_fields=["status", "closed_at"])

        self._record_status_change(
            incident, request.user, prev, serializer.validated_data["resolution_summary"]
        )
        return Response(IncidentSerializer(incident, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        incident = self.get_object()
        serializer = IncidentReopenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        prev = incident.status
        incident.status = Incident.Status.OPEN
        incident.resolved_at = None
        incident.closed_at = None
        incident.save(update_fields=["status", "resolved_at", "closed_at"])

        self._record_status_change(
            incident, request.user, prev, serializer.validated_data["reason"]
        )
        return Response(IncidentSerializer(incident, context={"request": request}).data)


class IncidentUpdateViewSet(viewsets.GenericViewSet,
                            viewsets.mixins.ListModelMixin,
                            viewsets.mixins.CreateModelMixin):
    serializer_class = IncidentUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            IncidentUpdate.objects
            .filter(incident_id=self.kwargs["incident_pk"])
            .select_related("author")
        )

    def perform_create(self, serializer):
        incident = Incident.objects.get(pk=self.kwargs["incident_pk"])
        update = serializer.save(
            incident=incident,
            author=self.request.user,
            update_type=IncidentUpdate.UpdateType.COMMENT,
        )
        from .tasks import send_comment_notification
        send_comment_notification.delay(incident.pk, update.pk)
