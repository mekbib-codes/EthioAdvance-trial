# templatetags/user_search.py
from django import template

register = template.Library()

@register.inclusion_tag('company/components/search_users.html')
def user_search(list_url_name, search_url_name):
    return {
        'user_list_url': list_url_name,
        'user_search_url': search_url_name
    }