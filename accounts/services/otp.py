from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.contrib.sites.models import Site
import logging
import random
import string
from datetime import timedelta     

from accounts.models import OTP

logger = logging.getLogger('app')

class OTPService:
    @staticmethod
    def generate_otp_code(length=settings.OTP_LENGTH):
        """Generate a random OTP code"""
        return ''.join(random.choices(string.digits, k=length))
    
    @classmethod
    def generate_otp(cls, email, purpose):
        """Generate, save and send OTP to user's email"""
        try:
            # First invalidate any existing OTPs for this email/purpose
            OTP.objects.filter(
                email=email,
                purpose=purpose,
                is_used=False
            ).update(is_used=True)
            
            otp_code = cls.generate_otp_code()
            expires_at = timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
            
            otp = OTP.objects.create(
                email=email,
                otp_code=otp_code,
                purpose=purpose,
                expires_at=expires_at  # Explicitly set expiration
            )
            
            cls.send_otp_email(email, otp_code, purpose, expires_at)
            logger.info(f"OTP generated for {email} (purpose: {purpose})")
            return otp
            
        except Exception as e:
            logger.error(f"Failed to generate OTP for {email}: {str(e)}", exc_info=True)
            return None
        
    @staticmethod
    def send_otp_email(email, otp_code, purpose, expires_at):
        """Send OTP code to user's email"""
        try:
            context = {
                'otp_code': otp_code,
                'purpose': purpose,
                'expiry_minutes': settings.OTP_EXPIRY_MINUTES,
                'expires_at': expires_at,
                'site_name': "EthioAdvance",
            }

            subject = f"Your OTP for {purpose}"
            message = render_to_string('accounts/emails/otp_email.txt', context)
            html_message = render_to_string('accounts/emails/otp_email.html', context)
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
                html_message=html_message
            )
            logger.info(f"OTP email sent to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send OTP email to {email}: {str(e)}", exc_info=True)
            return False
    
    @classmethod
    def verify_otp(cls, email, otp_code, purpose):
        """
        Verify if OTP is valid for the given email and purpose
        Returns tuple: (is_valid, otp_object)
        """
        try:
            otp = OTP.objects.filter(
                email=email,
                otp_code=otp_code,
                purpose=purpose
            ).order_by('-created_at').first()
            
            if not otp:
                logger.warning(f"No OTP found for {email} with code {otp_code}")
                return False, None
                
            if not otp.is_still_valid():
                logger.warning(f"Invalid OTP attempt for {email}: expired or used")
                return False, None
                
            otp.mark_as_used()
            logger.info(f"OTP verified successfully for {email}")
            return True, otp
            
        except Exception as e:
            logger.error(f"OTP verification failed for {email}: {str(e)}", exc_info=True)
            return False, None



