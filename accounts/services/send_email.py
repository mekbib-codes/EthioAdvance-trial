from django.contrib.sites.models import Site
from django.urls import reverse

from django.template.loader import render_to_string
from django.conf import settings
from django.core.mail import send_mail
import logging

logger = logging.getLogger('app')

class SendEmailService:

    @classmethod
    def send_welcome_message(cls, request, user):

        try:
            current_site = Site.objects.get_current()
            context = {
                'user': user,
                'site_name': current_site.name,
                "login_url": request.build_absolute_uri(reverse('accounts:login')),
            }
            subject = f"Welcome aboard, {user.first_name}! 🎉 Let’s get started with {current_site}."
            message = render_to_string('accounts/emails/welcome_message.txt', context)
            html_message = render_to_string('accounts/emails/welcome_message.html', context)

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
                html_message=html_message
            )
            logger.info(f"Welcome message sent to {user.email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send Welcome to {user.email}: {str(e)}", exc_info=True)
            return False