from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, OTP

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Display fields in list view
    list_display = ('id', 'email', 'get_full_name', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    list_editable = ['role']
    ordering = ('-created_at',)
    
    # Fields in edit view (grouped logically)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'date_of_birth', 'gender')}),
        ('Role', {'fields': ('role',)}),
        ('Contact Info', {'fields': ('phone_number',)}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important Dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    
    # Fields when adding new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 
                      'first_name', 'last_name', 'date_of_birth', 'role'),
        }),
    )
    
    # Make dates read-only
    readonly_fields = ('created_at', 'updated_at')
    
    # Enable search by email and names
    search_fields = ('email', 'first_name', 'last_name')

@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ['email', 'otp_code', 'purpose', 'expires_at', 'is_used']
    list_filter = ('purpose', 'is_used')
    ordering = ('-created_at',)