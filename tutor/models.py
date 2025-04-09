from django.db import models
from accounts.models import User

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class TutorManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(role=User.Role.TUTOR)

class Tutor(User):

    objects = TutorManager()
    
    class Meta:
        proxy = True
        verbose_name = 'Tutor'
        verbose_name_plural = 'Tutors'

    def get_queryset(self):
        return super().get_queryset().filter(role=User.Role.TUTOR)

    @property
    def profile(self):
        return TutorProfile.objects.get_or_create(user=self)[0]

class TutorProfile(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name='tutor_profile'
    )
    company = models.ForeignKey(
        'company.Company',
        on_delete=models.PROTECT,
        related_name='tutors'
    )
    qualification = models.CharField(max_length=100)
    years_of_experience = models.PositiveIntegerField()
    bio = models.TextField()
    address = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.get_full_name()}'s Profile"
    
    def clean(self):
        # Check if the user has the correct role
        if self.user.role != User.Role.TUTOR:
            raise ValidationError(
                _('User must have the role of "Tutor" to create a Tutor Profile.'),
                code='invalid_role'
            )