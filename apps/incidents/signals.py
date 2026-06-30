from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Incident


@receiver(post_save, sender=Incident)
def on_incident_created(sender, instance, created, **kwargs):
    if created:
        from .tasks import send_incident_created_notification
        send_incident_created_notification.delay(instance.pk)
