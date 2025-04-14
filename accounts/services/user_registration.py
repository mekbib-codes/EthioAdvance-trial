from django.utils.translation import gettext_lazy as _

from .send_email import SendEmailService

import logging

logger = logging.getLogger('app')

class UserRegistrationService:
    @staticmethod
    def create_user(form, request=None, **kwargs):
        """
        Generic user creation service that works with any form
        Args:
            form: The initialized and validated form instance
            request: Optional request object for context
            kwargs: Additional context needed for specific cases
        Returns: (user, error_message)
        """
        if not form.is_valid():
            error_msg = form.errors.as_text()
            return None, error_msg
        
        try:
            # Let the form handle all the saving logic
            user = form.save()
            return user, None
            
        except Exception as e:
            logger.error(f"Registration failed: {str(e)}", exc_info=True)
            error_msg = _("Registration failed due to system error. Please try again.")
            return None, error_msg
        
    @staticmethod
    def post_registration_tasks(request, user):
        """Generic post-registration tasks"""
        # Send welcome email
        if hasattr(user, 'email'):
            SendEmailService.send_welcome_message(request=request, user=user)
        
        # Clear sensitive session data
        for key in ['registration_data', 'register_url', 'success_redirect_name']:
            request.session.pop(key, None)
        request.session.save()