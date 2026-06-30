from django.urls import path

from .views import MTTRMetricsView, SLAMetricsView, SummaryMetricsView

urlpatterns = [
    path("metrics/summary/", SummaryMetricsView.as_view(), name="metrics-summary"),
    path("metrics/sla/", SLAMetricsView.as_view(), name="metrics-sla"),
    path("metrics/mttr/", MTTRMetricsView.as_view(), name="metrics-mttr"),
]
