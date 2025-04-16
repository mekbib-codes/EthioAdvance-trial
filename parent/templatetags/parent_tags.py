from django import template
from django.db.models import Count, Q
from session.models import Session

register = template.Library()

@register.inclusion_tag('parent/general_info.html', takes_context=True)
def parent_general_info(context):
    request = context['request']
    parent = request.user

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
        pending_sessions=Count('sessions', filter=Q(sessions__status=Session.Status.PENDING)),
        approved_sessions=Count('sessions', filter=Q(sessions__status=Session.Status.APPROVED)),
        rejected_sessions=Count('sessions', filter=Q(sessions__status=Session.Status.REJECTED)),
    )

    return {
        'parent': parent,
        'total_children': total_children,
        'total_sessions': totals['total_sessions'],
        'pending_sessions': totals['pending_sessions'],
        'approved_sessions': totals['approved_sessions'],
        'rejected_sessions': totals['rejected_sessions'],
    }