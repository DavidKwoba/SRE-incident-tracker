from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import CustomTokenObtainPairView, TeamViewSet, UserViewSet

router = DefaultRouter()
router.register("teams", TeamViewSet, basename="team")
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("auth/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("", include(router.urls)),
]
