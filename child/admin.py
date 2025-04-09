from django.contrib import admin
from .models import Child, ChildProfile
from accounts.models import User

@admin.register(ChildProfile)
class ChildProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'parent', 'tutor', 'grade_level')
    search_fields = ('user__email', 'parent__user__email', 'school')
    list_filter = ('grade_level', 'school')
    raw_id_fields = ('user', 'parent', 'tutor')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'parent', 'tutor')

class ChildProfileInline(admin.StackedInline):
    model = ChildProfile
    fk_name = 'user'
    extra = 0
    min_num = 1
    raw_id_fields = ('parent', 'tutor')
    verbose_name = 'Child Profile'
    verbose_name_plural = 'Child Profile'

@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ('email', 'get_full_name', 'date_of_birth')
    search_fields = ('email', 'first_name', 'last_name')
    inlines = [ChildProfileInline]
    readonly_fields = ('slug', 'created_at', 'updated_at')

    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Full Name'