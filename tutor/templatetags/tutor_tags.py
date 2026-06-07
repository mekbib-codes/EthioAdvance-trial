from django import template
from payment.utils import calculate_tutor_payment
from payment.models import TutorPayments, TutorPayRate
from tutor.models import Tutor
from django.db.models import Sum, Count, Q
from session.models import Session
from session.utils import calculate_session_data

import logging
logger = logging.getLogger('app')

register = template.Library()

@register.inclusion_tag('tutor/general_info.html', takes_context=True)
def tutor_general_info(context):
    request = context['request']
    tutor = Tutor.objects.get(id=request.user.id)

    # Fetch general information about the tutor
    total_students = tutor.students.count()

    # # Aggregate session counts by status in a single query
    session_totals = Session.objects.filter(tutor=tutor).aggregate(
        total_sessions=Count('id'),
        # pending_sessions=Count('id', filter=Q(status=Session.Status.PENDING)),
        # approved_sessions=Count('id', filter=Q(status=Session.Status.APPROVED)),
        # rejected_sessions=Count('id', filter=Q(status=Session.Status.REJECTED)),
    )

    try:
        profile_image = tutor.profile.avatar.url
    except:
        profile_image = None

    return {
        'tutor': tutor,
        'total_students': total_students,
        'profile_image': profile_image,
        'total_sessions': session_totals['total_sessions'],
        # 'pending_sessions': session_totals['pending_sessions'],
        # 'approved_sessions': session_totals['approved_sessions'],
        # 'rejected_sessions': session_totals['rejected_sessions'],
    }

@register.inclusion_tag('tutor/payment/payment_card.html', takes_context=True)
def tutor_payment_card(context, child):
    payout, unpaid_sessions = calculate_tutor_payment(child=child)

    total_earned = TutorPayments.objects.filter(
        child=child,
        status=TutorPayments.STATUS.SUCCESS  # Only include successful payments
    ).aggregate(total_paid=Sum('amount'))['total_paid'] or 0  # Default to 0 if no payments

    # Check if there is a pending payment request for the same child
    pending_payment = TutorPayments.objects.filter(
        child=child,
        tutor=context['request'].user,
        status=TutorPayments.STATUS.PENDING
    ).first()

    requested_amount = pending_payment.amount if pending_payment else 0


    return {
        'child': child,
        'payout': payout,
        'total_earned': total_earned,
        'unpaid_sessions': unpaid_sessions,
        'pending_payment': pending_payment,
        'requested_amount': requested_amount,
    }

@register.inclusion_tag('tutor/payment/payment_info.html', takes_context=True)
def tutor_payment_info(context, tutor_id: int):

    tutor = Tutor.objects.get(id=tutor_id
                              )
    # Get payment info
    success_payments = tutor.tutor_payments.filter(status=TutorPayments.STATUS.SUCCESS)
    total_earned = success_payments.aggregate(total=Sum('amount'))['total'] or 0

    requested_payments = tutor.tutor_payments.filter(status=TutorPayments.STATUS.PENDING)
    total_requested = requested_payments.aggregate(total=Sum('amount'))['total'] or 0

    approved_sessions = Session.objects.filter(tutor=tutor, status=Session.Status.APPROVED)
    paid_sessions = approved_sessions.filter(paid_to_tutor=True)
    unpaid_sessions = approved_sessions.filter(paid_to_tutor=False)

    # Duration calculations
    paid_sessions_duration = paid_sessions.aggregate(total=Sum('duration'))['total'] or 0
    unpaid_sessions_duration = unpaid_sessions.aggregate(total=Sum('duration'))['total'] or 0

    # Calculate amount unpaid
    rate_table = TutorPayRate.objects.latest("updated_at")
    total_unpaid = 0

    for session in unpaid_sessions:
        if not session.duration:
            continue

        rate = rate_table.get_current_hourly_rate(session.child)
        hours = session.duration.total_seconds() / 3600
        total_unpaid += round(hours * float(rate), 2)

    payment_data = {'total_earned': total_earned,
                    'total_requested': total_requested,
                    'total_unpiad': total_unpaid,
                    'paid_sessions': paid_sessions.count(),
                    'unpaid_sessions': unpaid_sessions.count(),
                    'paid_sessions_duration': paid_sessions_duration,
                    'unpaid_sessions_duration': unpaid_sessions_duration,
                    'hourly_rate': rate  # Include for transparency
            }
    
    return {'payment_data': payment_data}

@register.inclusion_tag('parent/sessions/session_info.html', takes_context=True)
def tutor_session_info(context, tutor_id:int):
     
    #  Get all sessions for the parent
    tutor = Tutor.objects.get(id=tutor_id)
    sessions = Session.objects.filter(tutor=tutor)

    session_data = calculate_session_data(sessions=sessions)
    

    return{'session_data': session_data}