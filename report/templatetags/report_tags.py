from django import template

register = template.Library()

@register.filter
def humanize_duration(value):
    if not value:
        return "0h 0m"
    total_seconds = int(value.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours}h {minutes}m"
