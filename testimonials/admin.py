from django.contrib import admin
from .models import Testimonial
from django.urls import reverse
from django.utils.html import format_html

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):

    list_display = ['id', 'parent', 'show_testimonial', 'is_featured', 'formatted_rating']
    list_filter = ['show_testimonial', 'rating', 'is_featured']
    search_fields = ['parent__first_name', 'parent__last_name']
    list_editable = ['show_testimonial', 'is_featured']
    list_per_page = 25

    def formatted_rating(self, obj):
        if obj.rating is None:
            return format_html('<span style="color: #999;">No Rating</span>')
        elif obj.rating >= 4:
            return format_html('<span style="color: green; font-weight: bold;">★ {}</span>', obj.rating)
        elif obj.rating <= 2:
            return format_html('<span style="color: red; font-weight: bold;">★ {}</span>', obj.rating)
        else:
            return format_html('<span style="color: orange;">★ {}</span>', obj.rating)
        
    # Group fields in the edit view
    fieldsets = (
        ('Testimonial', {
            'fields': (
                'parent',
                'text',
                'rating',
            )
        }),
        ('Filters', {
            'fields': (
                'show_testimonial',
                'is_featured',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at',),
        }),
    )

    # Make certain fields read-only
    readonly_fields = ('created_at', )

    # Custom link to the tutor in the admin
    def parent_link(self, obj):
        if obj.parent:
            app_label = obj.parent._meta.app_label
            model_name = obj.parent._meta.model_name
            url = reverse(f"admin:{app_label}_{model_name}_change", args=[obj.parent.id])
            return format_html('<a href="{}">{}</a>', url, obj.parent.get_full_name())
        return "-"
    parent_link.short_description = 'parent'
    parent_link.admin_order_field = 'parent__first_name'
