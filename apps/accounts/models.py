from django.contrib.auth.models import AbstractUser
from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(unique=True)
    email = models.EmailField()
    slack_channel = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class User(AbstractUser):
    teams = models.ManyToManyField(Team, related_name="members", blank=True)
    slack_user_id = models.CharField(max_length=40, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return self.get_full_name() or self.username
