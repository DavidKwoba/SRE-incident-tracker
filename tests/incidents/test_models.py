import pytest
from datetime import timedelta

from django.utils import timezone

from apps.incidents.sla import SLA_WINDOWS, calculate_sla_deadlines


class TestSLACalculation:
    def test_deadlines_are_set_relative_to_now(self):
        now = timezone.now()
        result = calculate_sla_deadlines("P1", created_at=now)
        assert result["response_due_at"] == now + SLA_WINDOWS["P1"]["response"]
        assert result["resolution_due_at"] == now + SLA_WINDOWS["P1"]["resolution"]

    def test_p1_response_is_15_minutes(self):
        now = timezone.now()
        result = calculate_sla_deadlines("P1", created_at=now)
        delta = result["response_due_at"] - now
        assert delta == timedelta(minutes=15)

    def test_p4_resolution_is_72_hours(self):
        now = timezone.now()
        result = calculate_sla_deadlines("P4", created_at=now)
        delta = result["resolution_due_at"] - now
        assert delta == timedelta(hours=72)

    def test_unknown_priority_falls_back_to_p3(self):
        now = timezone.now()
        result = calculate_sla_deadlines("P9", created_at=now)
        assert result["resolution_due_at"] == now + SLA_WINDOWS["P3"]["resolution"]
