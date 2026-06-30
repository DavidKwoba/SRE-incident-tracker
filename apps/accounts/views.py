from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Team, User
from .permissions import IsPlatformAdmin
from .serializers import (
    CustomTokenObtainPairSerializer,
    TeamSerializer,
    UserProfileSerializer,
    UserSerializer,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsPlatformAdmin()]
        return [IsAuthenticated()]

    @action(detail=True, methods=["get"])
    def incidents(self, request, pk=None):
        from apps.incidents.models import Incident
        from apps.incidents.serializers import IncidentSerializer

        team = self.get_object()
        qs = Incident.objects.filter(reporting_team=team).order_by("-created_at")
        serializer = IncidentSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().prefetch_related("teams", "groups")
    serializer_class = UserSerializer
    permission_classes = [IsPlatformAdmin]

    @action(detail=False, methods=["get", "patch"], permission_classes=[IsAuthenticated])
    def me(self, request):
        if request.method == "PATCH":
            serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response(UserProfileSerializer(request.user).data)
