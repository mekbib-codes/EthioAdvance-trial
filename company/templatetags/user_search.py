# templatetags/user_search.py
from django import template

register = template.Library()

# company/templatetags/user_search.py
from django import template

register = template.Library()

@register.inclusion_tag('company/components/search_users.html', takes_context=True)
def user_search(context, list_url_name, search_url_name):
    return {
        'user_list_url': list_url_name,
        'user_search_url': search_url_name,
        'is_search': context.get('is_search', False),
        'search_query': context.get('search_query', '')
    }