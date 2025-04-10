from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from .models import User
import logging

logger = logging.getLogger('app')

def role_required(*allowed_roles):
    """Generalized decorator for all role checks"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                logger.warning(f"Unauthenticated access attempt to {view_func.__name__}")
                return redirect('accounts:login')
                
            if request.user.role not in allowed_roles:
                logger.warning(
                    f"Role violation: User {request.user.email} ({request.user.role}) "
                    f"attempted to access {view_func.__name__} "
                    f"(required: {allowed_roles})"
                )
                return HttpResponseForbidden()
                
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

# Specific convenience decorators
parent_required = role_required(User.Role.PARENT)
tutor_required = role_required(User.Role.TUTOR)
child_required = role_required(User.Role.CHILD)
company_required = role_required(User.Role.COMPANY)