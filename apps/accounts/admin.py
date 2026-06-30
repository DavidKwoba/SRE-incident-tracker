from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Team, User


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "email", "slack_channel", "created_at"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name", "email"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["username", "email", "first_name", "last_name", "is_staff", "is_active"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Profile", {"fields": ("teams", "slack_user_id", "phone")}),
    )
    filter_horizontal = ("teams", "groups", "user_permissions")
