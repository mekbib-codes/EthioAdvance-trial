from django.db.models import Sum

from .models import Session

def calculate_session_data(sessions: list) -> dict:
    total_sessions = sessions.count()
    pending_sessions = sessions.filter(status=Session.Status.PENDING)
    approved_sessions = sessions.filter(status=Session.Status.APPROVED)
    rejected_sessions = sessions.filter(status=Session.Status.REJECTED)
    
    session_data = {
        'total_sessions': total_sessions,
        'total_duration': sessions.aggregate(total=Sum('duration'))['total'] or 0,
        
        'pending_sessions': pending_sessions.count(),
        'pending_duration': pending_sessions.aggregate(total=Sum('duration'))['total'] or 0,
        
        'approved_sessions': approved_sessions.count(),
        'approved_duration': approved_sessions.aggregate(total=Sum('duration'))['total'] or 0,
        
        'rejected_sessions': rejected_sessions.count(),
        'rejected_duration': rejected_sessions.aggregate(total=Sum('duration'))['total'] or 0,
        
        # If I need the actual session objects in the future
        # 'all_sessions': sessions.order_by('-created_at')[:10]
    }

    # Calculate percentages
    total = session_data['total_sessions'] or 1  # avoid division by zero
    session_data['approved_percentage'] = round((session_data['approved_sessions'] / total) * 100)
    session_data['pending_percentage'] = round((session_data['pending_sessions'] / total) * 100)
    session_data['rejected_percentage'] = round((session_data['rejected_sessions'] / total) * 100)

    return session_data