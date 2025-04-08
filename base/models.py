from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.utils import timezone

from datetime import timedelta

import logging
logger = logging.getLogger(__name__)

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
        CHILD = "CHILD", "Child"
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

    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
            logger.info(f"User {obj.email} { 'updated' if change else 'created'} by {request.user.email}")
        except Exception as e:
            logger.error(f"Admin user save failed: {str(e)}")
            raise

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User'
        verbose_name_plural = 'Users'