from django import template
from django.db.models import Count, Q
from session.models import Session

register = template.Library()

@register.inclusion_tag('tutor/general_info.html', takes_context=True)
def tutor_general_info(context):
    request = context['request']
    tutor = request.user

    # Fetch general information about the tutor
    total_students = tutor.students.count()

    # Aggregate session counts by status in a single query
    session_totals = Session.objects.filter(tutor=tutor).aggregate(
        total_sessions=Count('id'),
        pending_sessions=Count('id', filter=Q(status=Session.Status.PENDING)),
        approved_sessions=Count('id', filter=Q(status=Session.Status.APPROVED)),
        rejected_sessions=Count('id', filter=Q(status=Session.Status.REJECTED)),
    )

    return {
        'tutor': tutor,
        'total_students': total_students,
        'total_sessions': session_totals['total_sessions'],
        'pending_sessions': session_totals['pending_sessions'],
        'approved_sessions': session_totals['approved_sessions'],
        'rejected_sessions': session_totals['rejected_sessions'],
    }