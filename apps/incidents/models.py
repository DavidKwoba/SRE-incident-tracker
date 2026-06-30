from django.db import models


class Label(models.Model):
    name = models.CharField(max_length=60, unique=True)
    color = models.CharField(max_length=7, default="#6B7280")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Incident(models.Model):
    class Priority(models.TextChoices):
        CRITICAL = "P1", "Critical"
        HIGH = "P2", "High"
        MEDIUM = "P3", "Medium"
        LOW = "P4", "Low"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        TRIAGED = "triaged", "Triaged"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    class IncidentType(models.TextChoices):
        INCIDENT = "incident", "Incident"
        SERVICE_REQUEST = "service_request", "Service Request"
        CHANGE_REQUEST = "change_request", "Change Request"

    title = models.CharField(max_length=255)
    description = models.TextField()
    type = models.CharField(
        max_length=30, choices=IncidentType.choices, default=IncidentType.INCIDENT
    )
    priority = models.CharField(
        max_length=2, choices=Priority.choices, default=Priority.MEDIUM
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )

    reporter = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="reported_incidents"
    )
    reporting_team = models.ForeignKey(
        "accounts.Team", on_delete=models.PROTECT, related_name="raised_incidents"
    )
    assignee = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_incidents",
    )

    labels = models.ManyToManyField(Label, blank=True)
    affected_service = models.CharField(max_length=120, blank=True)
    external_ref = models.CharField(max_length=120, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    triaged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    response_due_at = models.DateTimeField(null=True, blank=True)
    resolution_due_at = models.DateTimeField(null=True, blank=True)
    sla_breached = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["reporting_team"]),
            models.Index(fields=["assignee"]),
            models.Index(fields=["sla_breached"]),
            models.Index(fields=["resolution_due_at"]),
        ]

    def __str__(self):
        return f"[{self.priority}] {self.title}"


class IncidentUpdate(models.Model):
    class UpdateType(models.TextChoices):
        COMMENT = "comment", "Comment"
        STATUS_CHANGE = "status_change", "Status Change"
        ASSIGNMENT = "assignment", "Assignment"
        PRIORITY_CHANGE = "priority_change", "Priority Change"

    incident = models.ForeignKey(
        Incident, on_delete=models.CASCADE, related_name="updates"
    )
    author = models.ForeignKey("accounts.User", on_delete=models.PROTECT)
    update_type = models.CharField(max_length=20, choices=UpdateType.choices)
    body = models.TextField(blank=True)
    previous_value = models.CharField(max_length=120, blank=True)
    new_value = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.incident} — {self.update_type} by {self.author}"
