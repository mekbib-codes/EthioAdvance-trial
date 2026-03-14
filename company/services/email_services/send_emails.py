from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

class EmailService:
    @staticmethod
    def send_email(
        subject,
        to_emails,
        template_name,
        context=None,
        from_email=None
    ):
        """
        Send styled HTML emails
        Args:
            subject: Email subject
            to_emails: List of recipient emails
            template_name: Template path without extension (e.g. 'emails/account_status')
            context: Dictionary with template variables
            from_email: Optional from address (defaults to settings.DEFAULT_FROM_EMAIL)
        """
        if context is None:
            context = {}
        if from_email is None:
            from_email = settings.DEFAULT_FROM_EMAIL

        # Render HTML content
        html_content = render_to_string(f"{template_name}.html", context)
        
        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=html_content,  # Fallback text content
            from_email=from_email,
            to=to_emails
        )
        email.attach_alternative(html_content, "text/html")
        
        try:
            email.send()
            return True
        except Exception as e:
            # Log error here
            print(f"Error sending email: {e}")
            return False