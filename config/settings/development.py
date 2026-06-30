from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Use console backend so emails print to terminal during development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Run Celery tasks synchronously so you don't need a worker running locally
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Relax throttling during development
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
}

CORS_ALLOW_ALL_ORIGINS = True
