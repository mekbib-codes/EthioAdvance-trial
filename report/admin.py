from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import (
    Report,
    Strength,
    Weakness,
    Goal,
    LearningMaterial,
    ChallengeEncountered,
    SuggestedSolution,
)

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    # Display fields in the list view
    list_display = (
        'id',
        'child_link',
        'tutor_link',
        'from_date',
        'to_date',
        'total_sessions_conducted',
        'average_duration_per_session',
        'completion_percentage',
        'created_at',
    )
    list_filter = ('created_at', 'updated_at', 'completion_percentage')
    search_fields = ('child__first_name', 'child__last_name', 'tutor__first_name', 'tutor__last_name')
    list_per_page = 25
    autocomplete_fields = ['child', 'tutor']

    # Group fields in the edit view
    fieldsets = (
        ('Report Details', {
            'fields': (
                ('child', 'tutor'),
                ('from_date', 'to_date'),
                'total_sessions_conducted',
                'average_duration_per_session',
                'completion_percentage',
                'completion_notes',
            )
        }),
        ('Session Insights', {
            'fields': (
                'strengths',
                'weaknesses',
                'goals_achieved',
                'learning_material_prepared',
                'child_participation',
            )
        }),
        ('Quiz & Exam Details', {
            'fields': (
                'number_of_quizzes_prepared',
                'average_quiz_score',
                'number_of_mock_exams_prepared',
                'mock_exam_result_overview',
                'mock_exam_strengths',
                'mock_exam_improvement_areas',
            )
        }),
        ('Feedback & Challenges', {
            'fields': (
                'feedback_from_parent',
                'feedback_from_child',
                'challenges_encountered',
                'suggested_solutions',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    # Make certain fields read-only
    readonly_fields = ('created_at', 'updated_at')

    # Custom link to the child in the admin
    def child_link(self, obj):
        if obj.child:
            app_label = obj.child._meta.app_label
            model_name = obj.child._meta.model_name
            url = reverse(f"admin:{app_label}_{model_name}_change", args=[obj.child.id])
            return format_html('<a href="{}">{}</a>', url, obj.child.get_full_name())
        return "-"
    child_link.short_description = 'Child'
    child_link.admin_order_field = 'child__first_name'

    # Custom link to the tutor in the admin
    def tutor_link(self, obj):
        if obj.tutor:
            app_label = obj.tutor._meta.app_label
            model_name = obj.tutor._meta.model_name
            url = reverse(f"admin:{app_label}_{model_name}_change", args=[obj.tutor.id])
            return format_html('<a href="{}">{}</a>', url, obj.tutor.get_full_name())
        return "-"
    tutor_link.short_description = 'Tutor'
    tutor_link.admin_order_field = 'tutor__first_name'


### **Admin Configuration for Related Models**

@admin.register(Strength)
class StrengthAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    list_per_page = 25


@admin.register(Weakness)
class WeaknessAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    list_per_page = 25


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    list_per_page = 25


@admin.register(LearningMaterial)
class LearningMaterialAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    list_per_page = 25


@admin.register(ChallengeEncountered)
class ChallengesEncounteredAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    list_per_page = 25


@admin.register(SuggestedSolution)
class SuggestedSolutionsAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    list_per_page = 25