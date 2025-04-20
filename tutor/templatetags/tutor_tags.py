from django import template
from payment.utils import calculate_tutor_payment
from payment.models import TutorPayments
from tutor.models import Tutor
from django.db.models import Sum, Count, Q
from session.models import Session

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

@register.inclusion_tag('tutor/payment/payment_info.html', takes_context=True)
def tutor_payment_info(context, child):
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