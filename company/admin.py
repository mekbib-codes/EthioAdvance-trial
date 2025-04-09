from django.contrib import admin
from .models import Company, CompanyProfile
from accounts.models import User

@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'tax_id', 'address', 'company_size')
    list_editable = ('company_size',)
    search_fields = ('company_name', 'tax_id', 'address')
    list_filter = ('company_size', )

class CompanyProfileInline(admin.StackedInline):
    model = CompanyProfile
    extra = 0
    min_num = 1

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('email', 'phone_number', 'get_company_name')
    search_fields = ('email', 'company_profile__company_name')
    inlines = [CompanyProfileInline]
    readonly_fields = ('slug', 'created_at', 'updated_at')
    
    def get_company_name(self, obj):
        return obj.profile.company_name
    get_company_name.short_description = 'Company Name'
