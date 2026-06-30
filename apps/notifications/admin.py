from django.contrib import admin

from .models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ["incident", "channel", "recipient", "event", "status", "sent_at", "created_at"]
    list_filter = ["channel", "status", "event"]
    search_fields = ["recipient", "event"]
    readonly_fields = ["created_at", "sent_at"]
