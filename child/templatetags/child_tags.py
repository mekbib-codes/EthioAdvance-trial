from django import template
from django.db.models import Count, Q, Sum
from session.models import Session
from payment.utils import calculate_total_payment
from payment.models import Payment

from datetime import timedelta

register = template.Library()

@register.inclusion_tag('child/components/session_info.html', takes_context=True)
def child_session_info(context, child):
    """
    Returns session-related information for a specific child, including total duration for each status.
    """
    # Annotate session counts and total durations for the child
    session_data = child.sessions.aggregate(
        total_sessions=Count('id', filter=Q(is_paid=False, overdue=False)),
        pending_sessions=Count('id', filter=Q(status=Session.Status.PENDING, is_paid=False, overdue=False)),
        approved_sessions=Count('id', filter=Q(status=Session.Status.APPROVED, is_paid=False, overdue=False)),
        rejected_sessions=Count('id', filter=Q(status=Session.Status.REJECTED, is_paid=False, overdue=False)),
        total_pending_duration=Sum('duration', filter=Q(status=Session.Status.PENDING, is_paid=False, overdue=False)),
        total_approved_duration=Sum('duration', filter=Q(status=Session.Status.APPROVED, is_paid=False, overdue=False)),
        total_rejected_duration=Sum('duration', filter=Q(status=Session.Status.REJECTED, is_paid=False, overdue=False)),
       
    )

    total_duration = sum(
    [
        session_data['total_pending_duration'] or timedelta(0),
        session_data['total_approved_duration'] or timedelta(0),
        session_data['total_rejected_duration'] or timedelta(0),
    ],
    timedelta(0)  # Initial value for the sum
)

    # Format durations for display
    def format_duration(duration):
        if not duration:
            return "0 min"
        total_minutes = int(duration.total_seconds() / 60)
        hours, minutes = divmod(total_minutes, 60)
        if hours and minutes:
            return f"{hours} hr{'s' if hours > 1 else ''} {minutes} min{'s' if minutes > 1 else ''}"
        elif hours:
            return f"{hours} hr{'s' if hours > 1 else ''}"
        else:
            return f"{minutes} min{'s' if minutes > 1 else ''}"

    return {
        'child': child,
        'total_sessions': session_data['total_sessions'],
        'pending_sessions': session_data['pending_sessions'],
        'approved_sessions': session_data['approved_sessions'],
        'rejected_sessions': session_data['rejected_sessions'],
        'total_duration': format_duration(total_duration),
        'total_pending_duration': format_duration(session_data['total_pending_duration']),
        'total_approved_duration': format_duration(session_data['total_approved_duration']),
        'total_rejected_duration': format_duration(session_data['total_rejected_duration']),
    }

@register.inclusion_tag('child/components/payment_info.html', takes_context=True)
def child_payment_info(context, child):
    """
    Returns payment-related information for a specific child.
    """
    # Calculate total payment due using the utility function
    total_due, unpaid_sessions = calculate_total_payment(child)

    # Calculate total paid for the child
    total_paid = Payment.objects.filter(
        child=child,
        status=Payment.STATUS.SUCCESS  # Only include successful payments
    ).aggregate(total_paid=Sum('amount'))['total_paid'] or 0  # Default to 0 if no payments

    return {
        'child': child,
        'total_due': total_due,
        'total_paid': total_paid,
        'unpaid_sessions': unpaid_sessions,
    }