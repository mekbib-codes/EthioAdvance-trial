from django.db import models
from django.contrib.auth.models import BaseUserManager
from accounts.models import User

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class CompanyManager(BaseUserManager):
    def get_queryset(self):
        return super().get_queryset().filter(role=User.Role.COMPANY)
    
class Company(User):

    objects = CompanyManager()

    class Meta:
        proxy = True
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'

    def get_queryset(self):
        return super().get_queryset().filter(role=User.Role.COMPANY)

    @property
    def profile(self):
        return CompanyProfile.objects.get_or_create(user=self)[0]

class CompanyProfile(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name='company_profile'
    )
    company_name = models.CharField(max_length=100)
    tax_id = models.CharField(max_length=50, blank=True)
    address = models.TextField()
    company_size = models.CharField(
        max_length=20,
        choices=[
            ('SMALL', '1-10 employees'),
            ('MEDIUM', '11-50 employees'),
            ('LARGE', '51-200 employees'),
            ('XLARGE', '200+ employees')
        ]
    )

    def __str__(self):
        return self.company_name
    
    def clean(self):
        # Check if the user has the correct role
        if self.user.role != User.Role.COMPANY:
            raise ValidationError(
                _('User must have the role of "Company" to create a Company Profile.'),
                code='invalid_role'
            )