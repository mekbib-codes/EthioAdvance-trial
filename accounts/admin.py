from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Display fields in list view
    list_display = ('email', 'get_full_name', 'role', 'is_active', 'is_staff', "slug")
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
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
        ('Slug', {'fields': ('slug',)}),
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