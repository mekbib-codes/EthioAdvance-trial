from django.contrib import admin
from .models import Tutor, TutorProfile
from accounts.models import User

@admin.register(TutorProfile)
class TutorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'company',"address", 'years_of_experience', 'is_verified')
    list_editable = ('is_verified',)
    list_select_related = ('user', 'company')
    search_fields = ('user__email', 'qualification', 'company__company_name')
    list_filter = ('company', 'qualification', 'is_verified')
    raw_id_fields = ('user', 'company')


class TutorProfileInline(admin.StackedInline):
    model = TutorProfile
    fk_name = 'user'  # Specifies which ForeignKey to use
    extra = 0
    min_num = 1
    raw_id_fields = ('company',)

@admin.register(Tutor)
class TutorAdmin(admin.ModelAdmin):
    list_display = ('email', 'get_full_name', 'phone_number', 'date_of_birth')
    search_fields = ('email', 'first_name', 'last_name')
    list_filter = ('gender',)
    inlines = [TutorProfileInline]
    readonly_fields = ('slug', 'created_at', 'updated_at')
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Full Name'