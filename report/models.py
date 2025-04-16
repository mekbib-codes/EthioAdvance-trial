from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

class Strength(models.Model):
    name = models.CharField(max_length=500, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Strength"
        verbose_name_plural = "Strengths"

class Weakness(models.Model):
    name = models.CharField(max_length=500, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Weakness"
        verbose_name_plural = "Weaknesses"

class Goal(models.Model):
    name = models.CharField(max_length=500, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Goal"
        verbose_name_plural = "Goals"

class LearningMaterial(models.Model):
    name = models.CharField(max_length=500, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Learning Material"
        verbose_name_plural = "Learning Materials"

class ChallengeEncountered(models.Model):
    name = models.CharField(max_length=500, unique=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Challenge Encountered"
        verbose_name_plural = "Challenges Encountered"

class SuggestedSolution(models.Model):
    name = models.CharField(max_length=500, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Suggested Solution"
        verbose_name_plural = "Suggested Solutions"

class Report(models.Model):
    tutor = models.ForeignKey(
        "tutor.Tutor", on_delete=models.SET_NULL, null=True, blank=True, related_name="reports", db_index=True
    )
    child = models.ForeignKey(
        "child.Child", on_delete=models.SET_NULL, null=True, blank=True, related_name="report", db_index=True
    )
    from_date = models.DateTimeField()
    to_date = models.DateTimeField()
    total_sessions_conducted = models.PositiveIntegerField()
    average_duration_per_session = models.DurationField()

    strengths = models.ManyToManyField(Strength, blank=True)
    weaknesses = models.ManyToManyField(Weakness, blank=True)
    goals_achieved = models.ManyToManyField(Goal, blank=True)

    learning_material_prepared = models.ManyToManyField(LearningMaterial, blank=True)

    number_of_quizzes_prepared = models.PositiveIntegerField(blank=True, null=True)
    average_quiz_score = models.PositiveIntegerField(
        blank=True, null=True, validators=[MaxValueValidator(100)]
    )

    number_of_mock_exams_prepared = models.PositiveIntegerField()
    mock_exam_result_overview = models.TextField()
    mock_exam_strengths = models.TextField()
    mock_exam_improvement_areas = models.TextField()

    child_participation = models.TextField()

    completion_percentage = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)], blank=True, null=True
    )
    completion_notes = models.TextField(blank=True, null=True)

    feedback_from_parent = models.TextField(blank=True, null=True)
    feedback_from_child = models.TextField(blank=True, null=True)

    challenges_encountered = models.ManyToManyField(ChallengeEncountered, blank=True)
    suggested_solutions = models.ManyToManyField(SuggestedSolution, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    @property
    def total_session_duration(self):
        """Calculate total session duration as total_sessions_conducted * average_duration_per_session"""
        if self.total_sessions_conducted and self.average_duration_per_session:
            return self.average_duration_per_session * self.total_sessions_conducted
        return None

    def clean(self):
        """Custom validation for logical consistency."""
        if self.to_date and self.from_date and self.to_date <= self.from_date:
            raise ValidationError(_("The 'to_date' must be after 'from_date'."))
        if self.completion_percentage and self.completion_percentage > 100:
            raise ValidationError(_("Completion percentage cannot exceed 100."))

    def __str__(self):
        return f"Report for {self.child} by {self.tutor} ({self.from_date.date()} - {self.to_date.date()})"

    class Meta:
        verbose_name = "Report"
        verbose_name_plural = "Reports"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["tutor"]),
            models.Index(fields=["child"]),
        ]
