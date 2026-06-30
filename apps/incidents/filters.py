import django_filters

from .models import Incident


class IncidentFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(method="filter_csv")
    priority = django_filters.CharFilter(method="filter_csv")
    type = django_filters.CharFilter(field_name="type")
    assignee = django_filters.NumberFilter(field_name="assignee__id")
    reporting_team = django_filters.NumberFilter(field_name="reporting_team__id")
    label = django_filters.CharFilter(field_name="labels__name", lookup_expr="iexact")
    sla_breached = django_filters.BooleanFilter(field_name="sla_breached")
    created_after = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = Incident
        fields = [
            "status", "priority", "type",
            "assignee", "reporting_team", "label", "sla_breached",
        ]

    def filter_csv(self, queryset, name, value):
        values = [v.strip() for v in value.split(",") if v.strip()]
        return queryset.filter(**{f"{name}__in": values})
