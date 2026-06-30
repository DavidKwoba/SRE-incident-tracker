from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import IncidentUpdateViewSet, IncidentViewSet, LabelViewSet

router = DefaultRouter()
router.register("labels", LabelViewSet, basename="label")
router.register("incidents", IncidentViewSet, basename="incident")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "incidents/<int:incident_pk>/updates/",
        IncidentUpdateViewSet.as_view({"get": "list", "post": "create"}),
        name="incident-updates",
    ),
]
