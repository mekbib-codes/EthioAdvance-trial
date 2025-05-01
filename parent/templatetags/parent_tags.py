from django import template
from django.db.models import Count, Q, Sum
from session.models import Session
from session.utils import calculate_session_data
from parent.models import Parent
from payment.utils import calculate_total_payment
from payment.models import SessionRate, Payment

import logging
logger = logging.getLogger('app')

register = template.Library()

@register.inclusion_tag('parent/general_info.html', takes_context=True)
def parent_general_info(context):
    request = context['request']
    parent = Parent.objects.get(id=request.user.id)


    # Fetch all children and annotate session counts
    children = parent.children.annotate(
        total_sessions=Count('sessions'),
        pending_sessions=Count('sessions', filter=Q(sessions__status=Session.Status.PENDING)),
        approved_sessions=Count('sessions', filter=Q(sessions__status=Session.Status.APPROVED)),
        rejected_sessions=Count('sessions', filter=Q(sessions__status=Session.Status.REJECTED)),
    )
    
    total_children = children.count()
    # Aggregate totals across all children
    totals = children.aggregate(
        total_sessions=Count('sessions'),
        # pending_sessions=Count('sessions', filter=Q(sessions__status=Session.Status.PENDING)),
        # approved_sessions=Count('sessions', filter=Q(sessions__status=Session.Status.APPROVED)),
        # rejected_sessions=Count('sessions', filter=Q(sessions__status=Session.Status.REJECTED)),
    )
    try:
        profile_image = parent.profile.avatar.url
    except:
        profile_image = None

    return {
        'parent': parent,
        'total_children': total_children,
        'total_sessions': totals['total_sessions'],
        # 'pending_sessions': totals['pending_sessions'],
        # 'approved_sessions': totals['approved_sessions'],
        # 'rejected_sessions': totals['rejected_sessions'],
        'profile_image': profile_image,
    }

@register.inclusion_tag('parent/payment/pay_now_button.html', takes_context=True)
def pay_now_button(context, child):

    # Calculate total payment due using the utility function
    total_due, unpaid_sessions = calculate_total_payment(child)

    return {
        'child': child,
        'total_due': total_due,
        'unpaid_sessions': unpaid_sessions,
    }

@register.inclusion_tag('parent/payment/payment_info.html', takes_context=True) 
def parent_payment_info(context, parent_id: int):
    request = context['request']

    parent = Parent.objects.get(id=parent_id)

    # Get payment info
    success_payments = parent.payments.filter(status=Payment.STATUS.SUCCESS)
    total_paid = success_payments.aggregate(total=Sum('amount'))['total'] or 0

    # Get paid and unpaid approved sessions and corresponding durations
    approved_sessions = Session.objects.filter(child__parent=parent, status=Session.Status.APPROVED)
    
    paid_sessions = approved_sessions.filter(is_paid=True)
    unpaid_sessions = approved_sessions.filter(is_paid=False)

    # Duration calculations
    paid_sessions_duration = paid_sessions.aggregate(total=Sum('duration'))['total'] or 0
    unpaid_sessions_duration = unpaid_sessions.aggregate(total=Sum('duration'))['total'] or 0

    # Calculate total_due from unpiad sessions duration

    # 1- First Calculate current hourly rate
    try:
        rate = SessionRate.objects.latest("updated_at").current_hourly_rate
    except SessionRate.DoesNotExist:
        rate = 0
        logger.warning("No SessionRate found")
    
    if unpaid_sessions_duration != 0:
                # Convert duration to hours
                total_unpaid_hours = unpaid_sessions_duration.total_seconds() / 3600
                total_due = round(total_unpaid_hours * float(rate), 2)
    else:
        total_due = 0

    # Collect data
    payment_data = {
                'total_paid': total_paid,
                'total_due': total_due,
                'paid_sessions': paid_sessions.count(),
                'unpaid_sessions': unpaid_sessions.count(),
                'paid_sessions_duration': paid_sessions_duration,
                'unpaid_sessions_duration': unpaid_sessions_duration,
                'hourly_rate': rate  # Include for transparency
            }
    
    return {'request': request, 'payment_data': payment_data}

@register.inclusion_tag('parent/sessions/session_info.html', takes_context=True)
def parent_session_info(context, parent_id:int):
     
    #  Get all sessions for the parent
    parent = Parent.objects.get(id=parent_id)
    sessions = Session.objects.filter(child__parent=parent)

    session_data = calculate_session_data(sessions=sessions)
    

    return{'session_data': session_data}