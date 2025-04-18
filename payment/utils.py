from datetime import timedelta
from .models import SessionRate
from session.models import Session

def calculate_total_payment(child):
    sessions = child.sessions.filter(status=Session.Status.APPROVED, is_paid=False)
    total_duration = sum([s.duration for s in sessions if s.duration], start=timedelta())
    total_hours = total_duration.total_seconds() / 3600
    rate = SessionRate.objects.latest("updated_at").current_hourly_rate
    return round(total_hours * float(rate), 2), sessions