from django.contrib import admin
from .models import Parent, ParentProfile
from accounts.models import User

@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'occupation', 'emergency_contact')
    list_select_related = ('user', 'company')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'company__company_name')
    list_filter = ('company', 'preferred_communication')
    raw_id_fields = ('user', 'company')
    autocomplete_fields = ['company']


class ParentProfileInline(admin.StackedInline):
    model = ParentProfile
    fk_name = 'user'  # Specifies which ForeignKey to use
    extra = 0
    min_num = 1
    raw_id_fields = ('company',)

@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('email', 'get_full_name', 'date_of_birth', 'phone_number', 'profile')
    search_fields = ('email', 'first_name', 'last_name')
    list_filter = ('gender', 'date_of_birth')
    inlines = [ParentProfileInline]
    readonly_fields = ('created_at', 'updated_at')
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Full Name'