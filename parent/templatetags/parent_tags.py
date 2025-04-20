from django import template
from django.db.models import Count, Q
from session.models import Session
from parent.models import Parent
from payment.utils import calculate_total_payment

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