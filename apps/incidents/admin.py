from django.contrib import admin

from .models import Incident, IncidentUpdate, Label


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ["name", "color"]
    search_fields = ["name"]


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = [
        "title", "priority", "status", "type",
        "reporter", "reporting_team", "assignee",
        "sla_breached", "created_at",
    ]
    list_filter = ["status", "priority", "type", "sla_breached"]
    search_fields = ["title", "description"]
    date_hierarchy = "created_at"
    readonly_fields = [
        "created_at", "updated_at",
        "triaged_at", "resolved_at", "closed_at",
        "response_due_at", "resolution_due_at",
    ]
    filter_horizontal = ["labels"]


@admin.register(IncidentUpdate)
class IncidentUpdateAdmin(admin.ModelAdmin):
    list_display = ["incident", "author", "update_type", "created_at"]
    list_filter = ["update_type"]
    readonly_fields = ["created_at"]
