from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.utils.text import slugify
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings

from datetime import timedelta
import uuid

import logging
logger = logging.getLogger('app')

class UserManager(BaseUserManager):
    """Custom manager where email is the unique identifier instead of username"""
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a User with the given email and password"""
        try:
            if not email:
                logger.error("User creation attempted without email.")
                raise ValueError('The Email must be set')
            
            logger.info(f"Creating a user with email {email}")
            email = self.normalize_email(email)
            user = self.model(email=email, **extra_fields)
            user.set_password(password)
            user.save()
            return user
        except Exception as e:
            logger.critical(f"User creation failed for {email}: {str(e)}")
            raise

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)
    
class User(AbstractUser):
    class Gender(models.TextChoices):
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"

    class Role(models.TextChoices):
        PARENT = "PARENT", "Parent"
        TUTOR = "TUTOR", "Tutor"
        COMPANY = "COMPANY", "Company"

    # Role field was missing in your original
    role = models.CharField(max_length=20, choices=Role.choices)
    
    # Personal Info
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    date_of_birth = models.DateField(
        validators=[
            MaxValueValidator(limit_value=timezone.now().date()),
            MinValueValidator(limit_value=timezone.now().date() - timedelta(days=150*365))  # ~150 years max age
        ]
    )
    gender = models.CharField(
        max_length=20, 
        choices=Gender.choices,
        blank=True,
    )

    # Contact Info
    email = models.EmailField(unique=True)  # Make email required and unique
    phone_number = models.CharField(
        max_length=15, 
        unique=True, 
        blank=True, 
        null=True,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')]  # Basic phone validation
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Remove username if using email as identifier
    username = None
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'date_of_birth']

    # Assign the custom manager
    objects = UserManager()

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User'
        verbose_name_plural = 'Users'

class OTP(models.Model):
    class Purpose(models.TextChoices):
        REGISTRATION = "REGISTRATION", "Registration"
        PASSWORD_RESET = "PASSWORD_RESET", "Password Reset"
        EMAIL_CHANGE = "EMAIL_CHANGE", "Email Change"
    
    email = models.EmailField(db_index=True)
    otp_code = models.CharField(max_length=settings.OTP_LENGTH, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(editable=False, null=True, blank=True)
    is_used = models.BooleanField(default=False)
    purpose = models.CharField(
        max_length=20,
        choices=Purpose.choices,
        default=Purpose.REGISTRATION
    )
    
    class Meta:
        verbose_name = "OTP Code"
        verbose_name_plural = "OTP Codes"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'purpose']),
        ]
    
    def __str__(self):
        return f"OTP for {self.email} ({self.purpose})"
    
    def save(self, *args, **kwargs):
        if not self.pk:  # Only set expiration on creation
            self.expires_at = timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
        super().save(*args, **kwargs)
    
    def is_still_valid(self):
        """
        Check if OTP is still valid (not expired and not used)
        """
        now = timezone.now()
        
        if self.is_used:
            logger.debug(f"OTP {self.id} already used")
            return False
            
        if self.expires_at is None:
            logger.warning(f"OTP {self.id} has no expiration date - marking as invalid")
            return False
            
        if now > self.expires_at:
            logger.debug(f"OTP {self.id} expired at {self.expires_at}")
            return False
            
        return True
    
    def mark_as_used(self):
        """
        Mark OTP as used to prevent reuse
        """
        self.is_used = True
        self.save()
        logger.info(f"OTP {self.id} marked as used")
        return True
    
    @classmethod
    def purge_expired_otps(cls):
        """
        Clean up expired OTPs from database
        Returns count of deleted OTPs
        """
        now = timezone.now()
        expired = cls.objects.filter(expires_at__lt=now)
        count = expired.count()  # Get count before deletion
        expired.delete()
        logger.info(f"Purged {count} expired OTPs")
        return count
    
    def __repr__(self):
        return f"<OTP {self.otp_code} for {self.email} ({self.purpose})>"
