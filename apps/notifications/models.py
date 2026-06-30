from django.db import models


class NotificationLog(models.Model):
    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        SLACK = "slack", "Slack"

    class DeliveryStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    incident = models.ForeignKey(
        "incidents.Incident",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    channel = models.CharField(max_length=10, choices=Channel.choices)
    recipient = models.CharField(max_length=255)
    event = models.CharField(max_length=60)
    status = models.CharField(
        max_length=10,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
    )
    celery_task_id = models.CharField(max_length=50, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["incident", "channel"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.channel} → {self.recipient} [{self.status}]"
