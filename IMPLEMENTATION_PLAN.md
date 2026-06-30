# Incident Tracker — Implementation Plan

**Team:** Platform  
**Author:** Platform Engineering  
**Date:** 2026-06-30  
**Status:** Draft

---

## 1. Overview

The Incident Tracker is an internal tool that gives every team in the company a structured, auditable channel for raising issues against the Platform team. It replaces ad-hoc Slack pings and email threads with a traceable lifecycle: creation → triage → investigation → resolution → post-mortem.

### Goals
- Any internal team can open an incident or a service request against Platform.
- Platform engineers can triage, assign, update, and resolve tickets.
- Stakeholders receive automated notifications at key lifecycle transitions.
- SLA timers enforce response and resolution windows per priority.
- A history of all incidents is queryable for reporting and post-mortems.

### Non-Goals (v1)
- Public-facing status page.
- Customer-initiated tickets.
- On-call scheduling / pager integration (can be added in v2).

---

## 2. System Architecture

```
                        ┌─────────────────────────────────┐
                        │          API Clients             │
                        │  (other teams / internal tools) │
                        └────────────┬────────────────────┘
                                     │ HTTPS
                        ┌────────────▼────────────────────┐
                        │      Django REST Framework       │
                        │   (Auth · Incidents · Teams ·   │
                        │    Comments · Notifications)     │
                        └──┬────────────────┬─────────────┘
                           │                │
              ┌────────────▼───┐    ┌───────▼────────────┐
              │   PostgreSQL   │    │   Redis / RabbitMQ  │
              │  (primary DB)  │    │  (Celery broker +   │
              └────────────────┘    │   result backend)   │
                                    └───────┬─────────────┘
                                            │
                               ┌────────────▼────────────┐
                               │      Celery Workers      │
                               │  · Email notifications   │
                               │  · Slack webhooks        │
                               │  · SLA breach checks     │
                               │  · Escalation timers     │
                               └─────────────────────────┘
```

### Component Responsibilities

| Component | Role |
|---|---|
| Django REST Framework | Business logic, validation, API surface |
| PostgreSQL | Persistent storage for all entities |
| Redis | Celery broker, result backend, optional caching layer |
| RabbitMQ | Alternative broker for higher-throughput deployments |
| Celery | Async task execution — notifications, SLA enforcement |
| Celery Beat | Periodic tasks — SLA sweep, daily digest, stale-ticket cleanup |

---

## 3. Data Models

### 3.1 Core Entities

#### `Team`
Represents any team in the company that can raise or own incidents.

```python
class Team(models.Model):
    name            = models.CharField(max_length=120, unique=True)
    slug            = models.SlugField(unique=True)
    email           = models.EmailField()          # team DL for notifications
    slack_channel   = models.CharField(max_length=80, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
```

#### `User`
Extends Django's `AbstractUser`. Associates users with one or more teams.

```python
class User(AbstractUser):
    teams           = models.ManyToManyField(Team, related_name='members')
    slack_user_id   = models.CharField(max_length=40, blank=True)
    phone           = models.CharField(max_length=20, blank=True)
```

#### `Incident`
The central entity. Tracks the full lifecycle of an issue.

```python
class Incident(models.Model):

    class Priority(models.TextChoices):
        CRITICAL = 'P1', 'Critical'   # < 15 min response, < 1 hr resolution
        HIGH     = 'P2', 'High'       # < 1 hr response, < 4 hr resolution
        MEDIUM   = 'P3', 'Medium'     # < 4 hr response, < 24 hr resolution
        LOW      = 'P4', 'Low'        # < 24 hr response, < 72 hr resolution

    class Status(models.TextChoices):
        OPEN        = 'open',        'Open'
        TRIAGED     = 'triaged',     'Triaged'
        IN_PROGRESS = 'in_progress', 'In Progress'
        RESOLVED    = 'resolved',    'Resolved'
        CLOSED      = 'closed',      'Closed'

    class Type(models.TextChoices):
        INCIDENT       = 'incident',        'Incident'
        SERVICE_REQUEST = 'service_request', 'Service Request'
        CHANGE_REQUEST  = 'change_request',  'Change Request'

    title           = models.CharField(max_length=255)
    description     = models.TextField()
    type            = models.CharField(max_length=30, choices=Type.choices, default=Type.INCIDENT)
    priority        = models.CharField(max_length=2, choices=Priority.choices, default=Priority.MEDIUM)
    status          = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    reporter        = models.ForeignKey(User, on_delete=models.PROTECT, related_name='reported_incidents')
    reporting_team  = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='raised_incidents')
    assignee        = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_incidents')

    labels          = models.ManyToManyField('Label', blank=True)
    affected_service = models.CharField(max_length=120, blank=True)
    external_ref    = models.CharField(max_length=120, blank=True)  # e.g. Jira ticket, Slack link

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    triaged_at      = models.DateTimeField(null=True, blank=True)
    resolved_at     = models.DateTimeField(null=True, blank=True)
    closed_at       = models.DateTimeField(null=True, blank=True)

    # SLA
    response_due_at    = models.DateTimeField(null=True, blank=True)  # set on creation
    resolution_due_at  = models.DateTimeField(null=True, blank=True)
    sla_breached       = models.BooleanField(default=False)
```

#### `IncidentUpdate`
Append-only log of status changes and comments. Provides full audit trail.

```python
class IncidentUpdate(models.Model):

    class UpdateType(models.TextChoices):
        COMMENT       = 'comment',        'Comment'
        STATUS_CHANGE = 'status_change',  'Status Change'
        ASSIGNMENT    = 'assignment',     'Assignment'
        PRIORITY_CHANGE = 'priority_change', 'Priority Change'

    incident        = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='updates')
    author          = models.ForeignKey(User, on_delete=models.PROTECT)
    update_type     = models.CharField(max_length=20, choices=UpdateType.choices)
    body            = models.TextField(blank=True)
    previous_value  = models.CharField(max_length=120, blank=True)
    new_value       = models.CharField(max_length=120, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
```

#### `Label`
Free-form tags for categorisation and filtering.

```python
class Label(models.Model):
    name    = models.CharField(max_length=60, unique=True)
    color   = models.CharField(max_length=7, default='#6B7280')  # hex
```

#### `NotificationLog`
Records every notification dispatched, so we can debug delivery failures and avoid duplicates.

```python
class NotificationLog(models.Model):

    class Channel(models.TextChoices):
        EMAIL = 'email', 'Email'
        SLACK = 'slack', 'Slack'

    class DeliveryStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT    = 'sent',    'Sent'
        FAILED  = 'failed',  'Failed'

    incident        = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='notifications')
    channel         = models.CharField(max_length=10, choices=Channel.choices)
    recipient       = models.CharField(max_length=255)   # email address or Slack user/channel ID
    event           = models.CharField(max_length=60)    # e.g. "incident_created", "sla_breach"
    status          = models.CharField(max_length=10, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING)
    celery_task_id  = models.CharField(max_length=50, blank=True)
    sent_at         = models.DateTimeField(null=True, blank=True)
    error           = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
```

---

## 4. API Design

Base URL: `/api/v1/`

### 4.1 Authentication

All endpoints require authentication. Use **JWT** via `djangorestframework-simplejwt`.

```
POST   /api/v1/auth/token/           # obtain access + refresh tokens
POST   /api/v1/auth/token/refresh/   # refresh access token
```

Service accounts (for programmatic access from other systems) use long-lived API keys stored as `Authorization: Api-Key <key>` headers, managed via `djangorestframework-api-key`.

### 4.2 Incidents

```
GET    /api/v1/incidents/                  # list (filterable, paginated)
POST   /api/v1/incidents/                  # create new incident
GET    /api/v1/incidents/{id}/             # retrieve single incident
PATCH  /api/v1/incidents/{id}/             # update (partial — status, assignee, priority)
DELETE /api/v1/incidents/{id}/             # soft-delete (Platform admin only)

POST   /api/v1/incidents/{id}/triage/      # move to TRIAGED, set assignee
POST   /api/v1/incidents/{id}/resolve/     # move to RESOLVED, capture resolution notes
POST   /api/v1/incidents/{id}/close/       # move to CLOSED, require resolution summary
POST   /api/v1/incidents/{id}/reopen/      # reopen a resolved/closed incident

GET    /api/v1/incidents/{id}/updates/     # list all updates / comments
POST   /api/v1/incidents/{id}/updates/     # add comment or note
```

#### Filtering Parameters (GET /incidents/)
| Param | Example | Notes |
|---|---|---|
| `status` | `?status=open,triaged` | comma-separated |
| `priority` | `?priority=P1,P2` | |
| `type` | `?type=incident` | |
| `assignee` | `?assignee=42` | user id |
| `reporting_team` | `?reporting_team=3` | team id |
| `label` | `?label=database` | |
| `sla_breached` | `?sla_breached=true` | |
| `created_after` | `?created_after=2026-06-01` | ISO 8601 |
| `search` | `?search=postgres` | full-text on title + description |

### 4.3 Teams

```
GET    /api/v1/teams/
POST   /api/v1/teams/
GET    /api/v1/teams/{id}/
PATCH  /api/v1/teams/{id}/
GET    /api/v1/teams/{id}/incidents/    # incidents raised by this team
```

### 4.4 Users

```
GET    /api/v1/users/me/               # current user profile
PATCH  /api/v1/users/me/
GET    /api/v1/users/                  # list (Platform admin only)
```

### 4.5 Labels

```
GET    /api/v1/labels/
POST   /api/v1/labels/
DELETE /api/v1/labels/{id}/
```

### 4.6 Metrics / Reporting

```
GET    /api/v1/metrics/summary/         # counts by status, priority, team
GET    /api/v1/metrics/sla/             # SLA breach rate by priority
GET    /api/v1/metrics/mttr/            # mean time to resolve by priority
```

---

## 5. Permission Model

| Role | Can do |
|---|---|
| **Reporter** | Create incidents on behalf of their team; comment on their own team's incidents; read all incidents |
| **Platform Engineer** | Triage, assign, update, resolve any incident; manage labels |
| **Platform Admin** | All of the above + delete incidents, manage teams, manage users, view metrics |

Roles are implemented via **Django Groups**. Assign `reporter`, `platform_engineer`, or `platform_admin` group to each user. Use DRF permissions classes (`IsReporter`, `IsPlatformEngineer`, `IsPlatformAdmin`) backed by group membership checks.

---

## 6. SLA Configuration

SLA windows are configurable per priority. Store them in a `SLAPolicy` model or a settings file to allow adjustment without code changes.

| Priority | Response SLA | Resolution SLA |
|---|---|---|
| P1 — Critical | 15 minutes | 1 hour |
| P2 — High | 1 hour | 4 hours |
| P3 — Medium | 4 hours | 24 hours |
| P4 — Low | 24 hours | 72 hours |

On `Incident` creation, `response_due_at` and `resolution_due_at` are calculated and stored. A Celery Beat periodic task (every 5 minutes) sweeps for incidents where:
- `status` is not `resolved`/`closed` AND
- `resolution_due_at < now()`

These are flagged `sla_breached = True` and trigger an escalation notification.

---

## 7. Async Task Design (Celery)

### 7.1 Broker

Use **Redis** as the default broker (simpler ops). Switch to **RabbitMQ** if throughput requires durable queues with message persistence. Both are configured via `CELERY_BROKER_URL` in settings.

```python
# settings.py
CELERY_BROKER_URL       = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND   = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/1')
CELERY_TASK_SERIALIZER  = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT   = ['json']
CELERY_TIMEZONE         = 'Africa/Nairobi'
```

### 7.2 Task Inventory

| Task | Trigger | Queue |
|---|---|---|
| `send_incident_created_notification` | POST /incidents/ | `notifications` |
| `send_status_change_notification` | PATCH /incidents/{id}/ | `notifications` |
| `send_comment_notification` | POST /incidents/{id}/updates/ | `notifications` |
| `send_sla_breach_notification` | SLA sweep (Beat) | `notifications` |
| `check_sla_breaches` | Every 5 min (Beat) | `periodic` |
| `send_daily_digest` | 08:00 EAT daily (Beat) | `periodic` |
| `close_stale_incidents` | Every 24 hr (Beat) | `periodic` |

### 7.3 Notification Channels

**Email** — via Django's `EmailMultiAlternatives` (SMTP or SES). Template per event type.

**Slack** — via outgoing webhooks to the reporting team's `#slack_channel` and optionally to a central `#platform-incidents` channel. Use `requests` with retry logic or the `slack_sdk` package.

Each task:
1. Creates a `NotificationLog` record with `status=pending`.
2. Attempts delivery.
3. Updates `status` to `sent` or `failed` + captures any error.
4. On failure, Celery retries up to 3 times with exponential back-off.

### 7.4 Celery Beat Schedule

```python
CELERY_BEAT_SCHEDULE = {
    'check-sla-breaches': {
        'task': 'incidents.tasks.check_sla_breaches',
        'schedule': crontab(minute='*/5'),
    },
    'send-daily-digest': {
        'task': 'incidents.tasks.send_daily_digest',
        'schedule': crontab(hour=8, minute=0),
    },
    'close-stale-incidents': {
        'task': 'incidents.tasks.close_stale_incidents',
        'schedule': crontab(hour=0, minute=0),   # midnight
    },
}
```

---

## 8. Project Structure

```
incident-tracker/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
├── apps/
│   ├── accounts/          # User, Team models + auth endpoints
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── permissions.py
│   ├── incidents/         # Incident, IncidentUpdate, Label models + endpoints
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── filters.py
│   │   ├── tasks.py       # all Celery tasks
│   │   ├── signals.py     # post_save → enqueue tasks
│   │   └── sla.py         # SLA calculation helpers
│   ├── notifications/     # NotificationLog model + delivery utilities
│   │   ├── models.py
│   │   ├── email.py
│   │   └── slack.py
│   └── metrics/           # read-only reporting views
│       ├── views.py
│       └── serializers.py
├── templates/
│   └── emails/
│       ├── incident_created.html
│       ├── status_changed.html
│       ├── sla_breach.html
│       └── daily_digest.html
├── tests/
│   ├── accounts/
│   ├── incidents/
│   └── notifications/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── requirements/
│   ├── base.txt
│   └── development.txt
├── .env.example
└── manage.py
```

---

## 9. Key Dependencies

```
# requirements/base.txt
Django>=4.2,<5.0
djangorestframework>=3.15
djangorestframework-simplejwt>=5.3
djangorestframework-api-key>=3.0
django-filter>=24.0
django-environ>=0.11
psycopg2-binary>=2.9
celery[redis]>=5.4
redis>=5.0
kombu>=5.3              # RabbitMQ support (already bundled with Celery)
slack-sdk>=3.27
django-cors-headers>=4.3
whitenoise>=6.7         # static files in production
sentry-sdk>=2.0         # error tracking
```

---

## 10. Docker Compose (Local Development)

```yaml
# docker/docker-compose.yml
version: '3.9'
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: incident_tracker
      POSTGRES_USER: platform
      POSTGRES_PASSWORD: platform
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - ..:/app
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    env_file: ../.env

  worker:
    build: .
    command: celery -A config worker -Q notifications,periodic -l info
    volumes:
      - ..:/app
    depends_on:
      - db
      - redis
    env_file: ../.env

  beat:
    build: .
    command: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    volumes:
      - ..:/app
    depends_on:
      - db
      - redis
    env_file: ../.env

volumes:
  postgres_data:
```

---

## 11. Implementation Phases

### Phase 1 — Core API (Week 1–2)
- [ ] Django project scaffold with `config/settings/` split
- [ ] PostgreSQL connection + `accounts` app (User, Team models)
- [ ] JWT auth endpoints
- [ ] `incidents` app — Incident, IncidentUpdate, Label models + migrations
- [ ] Full CRUD + lifecycle endpoints (triage, resolve, close, reopen)
- [ ] Filtering, ordering, pagination
- [ ] Permission classes (Reporter, PlatformEngineer, PlatformAdmin)
- [ ] Unit tests for all endpoints

### Phase 2 — SLA + Async Notifications (Week 3)
- [ ] Celery + Redis setup (Docker Compose)
- [ ] SLA calculation on incident creation
- [ ] `check_sla_breaches` Beat task
- [ ] Email notification tasks (incident created, status changed, SLA breach)
- [ ] `NotificationLog` model + delivery logging
- [ ] Unit tests for tasks (mock delivery)

### Phase 3 — Slack Integration (Week 4)
- [ ] Slack webhook delivery via `slack_sdk`
- [ ] Per-team `slack_channel` configuration
- [ ] Central `#platform-incidents` channel summary post
- [ ] Daily digest Beat task
- [ ] Integration tests against a test Slack workspace

### Phase 4 — Metrics & Hardening (Week 5)
- [ ] `/api/v1/metrics/` endpoints (summary, SLA, MTTR)
- [ ] API key auth for service accounts
- [ ] Rate limiting (`djangorestframework` throttling)
- [ ] Sentry integration for error tracking
- [ ] Production settings + environment variable audit
- [ ] Load test key endpoints with `locust`

### Phase 5 — Deployment (Week 6)
- [ ] Dockerfile + multi-stage build
- [ ] Kubernetes manifests (or Helm chart) for api / worker / beat
- [ ] CI pipeline (lint → test → build → push)
- [ ] Database backup strategy (pg_dump to S3 / GCS)
- [ ] Runbook + API documentation (Swagger via `drf-spectacular`)

---

## 12. Environment Variables

```dotenv
# .env.example
SECRET_KEY=change-me
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

DATABASE_URL=postgres://platform:platform@db:5432/incident_tracker
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=incidents@example.com
EMAIL_HOST_PASSWORD=secret
DEFAULT_FROM_EMAIL=Platform Incident Tracker <incidents@example.com>

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_PLATFORM_INCIDENTS_CHANNEL=#platform-incidents

# Sentry
SENTRY_DSN=https://...@sentry.io/...
```

---

## 13. Open Questions / Decisions Needed

| # | Question | Options | Recommendation |
|---|---|---|---|
| 1 | **Broker: Redis vs RabbitMQ?** | Redis (simpler); RabbitMQ (durable, fine-grained routing) | Start with Redis; migrate to RabbitMQ if queue reliability becomes a concern |
| 2 | **Email provider** | SMTP relay, AWS SES, SendGrid | SES if already in AWS ecosystem, otherwise SendGrid |
| 3 | **API Key management for service accounts** | `djangorestframework-api-key`, custom model | `djangorestframework-api-key` — no re-invention |
| 4 | **Real-time updates** | Polling, WebSockets via `django-channels` | Polling for v1 (simpler); channels in v2 if live dashboards are needed |
| 5 | **Escalation chain** | Notify assignee only → team lead → platform-admin | Define in a follow-up discussion with the team |
| 6 | **Business hours SLA** | Clock-based vs business-hours-only | Clarify with leadership before implementing SLA timers |

---

## 14. Out-of-Scope for v1 (Future Enhancements)

- Public-facing status page
- PagerDuty / OpsGenie integration
- On-call rotation scheduling
- GitHub/Jira auto-linking on incident creation
- Mobile push notifications
- AI-assisted triage / duplicate detection
- Audit log export (CSV / PDF)
