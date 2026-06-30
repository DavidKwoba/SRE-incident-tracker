from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsPlatformAdmin
from apps.incidents.models import Incident


class SummaryMetricsView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        qs = Incident.objects.all()
        by_status = dict(
            qs.values_list("status").annotate(n=Count("id")).values_list("status", "n")
        )
        by_priority = dict(
            qs.values_list("priority").annotate(n=Count("id")).values_list("priority", "n")
        )
        by_type = dict(
            qs.values_list("type").annotate(n=Count("id")).values_list("type", "n")
        )
        open_statuses = [
            Incident.Status.OPEN,
            Incident.Status.TRIAGED,
            Incident.Status.IN_PROGRESS,
        ]
        return Response({
            "total": qs.count(),
            "open": qs.filter(status__in=open_statuses).count(),
            "sla_breached": qs.filter(sla_breached=True).count(),
            "by_status": by_status,
            "by_priority": by_priority,
            "by_type": by_type,
        })


class SLAMetricsView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        results = {}
        for priority in Incident.Priority.values:
            total = Incident.objects.filter(priority=priority).count()
            breached = Incident.objects.filter(priority=priority, sla_breached=True).count()
            results[priority] = {
                "total": total,
                "breached": breached,
                "breach_rate_pct": round(breached / total * 100, 1) if total else 0.0,
            }
        return Response(results)


class MTTRMetricsView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        resolved_statuses = [Incident.Status.RESOLVED, Incident.Status.CLOSED]
        results = {}
        for priority in Incident.Priority.values:
            agg = (
                Incident.objects
                .filter(
                    priority=priority,
                    status__in=resolved_statuses,
                    resolved_at__isnull=False,
                )
                .annotate(
                    resolution_time=ExpressionWrapper(
                        F("resolved_at") - F("created_at"),
                        output_field=DurationField(),
                    )
                )
                .aggregate(avg=Avg("resolution_time"))
            )
            avg = agg["avg"]
            results[priority] = {
                "mttr_seconds": int(avg.total_seconds()) if avg else None,
                "mttr_hours": round(avg.total_seconds() / 3600, 2) if avg else None,
            }
        return Response(results)
