from django.contrib import admin
from .models import Child, Status
from django.urls import reverse
from django.utils.html import format_html

@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    # Display fields in list view
    list_display = ('get_full_name', 'age', 'parent_link', 'tutor_link', 'grade_level', 'is_active')
    list_filter = ('grade_level', 'school', 'is_active', 'gender')
    search_fields = ('first_name', 'last_name', 'parent__first_name', 'parent__last_name', 'tutor__first_name', 'tutor__last_name')
    list_editable = ('is_active',)
    list_per_page = 25
    raw_id_fields = ('parent', 'tutor')  # Better for performance with many users
    autocomplete_fields = ['parent', 'tutor']
    
    # Group fields in edit view
    fieldsets = (
        ('Basic Information', {
            'fields': (
                ('first_name', 'last_name'),
                ('date_of_birth', 'gender'),
                ('parent', 'tutor'),
            )
        }),
        ('Education Information', {
            'fields': (
                ('grade_level', 'school'),
                'special_needs',
                'academic_interests'
            )
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )
    
    def parent_link(self, obj):
        if obj.parent:
            app_label = obj.parent._meta.app_label
            model_name = obj.parent._meta.model_name
            url = reverse(f"admin:{app_label}_{model_name}_change", args=[obj.parent.id])
            return format_html('<a href="{}">{}</a>', url, obj.parent.get_full_name())
        return "-"
    parent_link.short_description = 'Parent'
    parent_link.admin_order_field = 'parent__first_name'
    
    def tutor_link(self, obj):
        if obj.tutor:
            app_label = obj.tutor._meta.app_label
            model_name = obj.tutor._meta.model_name
            url = reverse(f"admin:{app_label}_{model_name}_change", args=[obj.tutor.id])
            return format_html('<a href="{}">{}</a>', url, obj.tutor.get_full_name())
        return "-"
        return "-"
    tutor_link.short_description = 'Tutor'
    tutor_link.admin_order_field = 'tutor__first_name'
    
    # Add age to the model's fields when editing
    readonly_fields = ('age',)
    
    def age(self, obj):
        return obj.age()
    age.short_description = 'Age'
    
    # Customize the add/edit form to show help texts
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['parent'].help_text = "Select the parent this child belongs to"
        form.base_fields['tutor'].help_text = "Optional - assign a tutor to this child"
        form.base_fields['date_of_birth'].help_text = "Format: YYYY-MM-DD"
        return form
    
    # Set the admin site title
    def get_model_perms(self, request):
        return {
            'add': request.user.has_perm('accounts.add_child'),
            'change': request.user.has_perm('accounts.change_child'),
            'delete': request.user.has_perm('accounts.delete_child'),
            'view': request.user.has_perm('accounts.view_child'),
        }

@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    # Display fields in list view
    list_display = ('child_link', 'attendance_rate', 'updated_at', 'sessions_summary_short')
    list_filter = ('updated_at',)
    search_fields = ('child__first_name', 'child__last_name', 'child__parent__first_name', 'child__parent__last_name')
    readonly_fields = ('updated_at',)

    # Group fields in edit view
    fieldsets = (
        ('Child Information', {
            'fields': ('child',)
        }),
        ('Performance Details', {
            'fields': (
                'attendance_rate',
                'sessions_summary',
                'strengths',
                'weaknesses',
                'improvement_notes',
                'mock_exam_graph',
            )
        }),
        ('Timestamps', {
            'fields': ('updated_at',)
        }),
    )

    def child_link(self, obj):
        if obj.child:
            app_label = obj.child._meta.app_label
            model_name = obj.child._meta.model_name
            url = reverse(f"admin:{app_label}_{model_name}_change", args=[obj.child.id])
            return format_html('<a href="{}">{}</a>', url, obj.child.get_full_name())
        return "-"
    child_link.short_description = 'Child'
    child_link.admin_order_field = 'child__first_name'

    def sessions_summary_short(self, obj):
        if obj.sessions_summary:
            return obj.sessions_summary[:50] + "..." if len(obj.sessions_summary) > 50 else obj.sessions_summary
        return "-"
    sessions_summary_short.short_description = 'Sessions Summary'

    # Customize the add/edit form to show help texts
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['child'].help_text = "Select the child this status belongs to"
        form.base_fields['attendance_rate'].help_text = "Enter the attendance rate as a percentage (0-100)"
        form.base_fields['mock_exam_graph'].help_text = "Upload an optional graph showing mock exam performance"
        return form