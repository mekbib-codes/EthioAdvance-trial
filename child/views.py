from django.views.generic import ListView, DetailView
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.views import View
from django.utils.translation import gettext as _


from accounts.decorators import parent_required
from .models import Child
from .forms import ChildRegistrationForm

import logging
logger = logging.getLogger('app')

@method_decorator(parent_required, name='dispatch')
class ParentRequiredMixin(View):
    pass

class ChildRegistrationView(ParentRequiredMixin, CreateView):
    model = Child
    form_class = ChildRegistrationForm
    template_name = 'registration/child_register_form.html'
    success_url = reverse_lazy('parent:dashboard')
    
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['parent'] = self.request.user  # Assuming parent_profile is the OneToOne field
        return kwargs

    def form_valid(self, form):
        logger.info(f"Parent {self.request.user} is registering a child.")
        response = super().form_valid(form)
        messages.success(
        self.request,
        _("Successfully registered %(child_name)s!") % {'child_name': form.instance.get_full_name()}
    )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['existing_children'] = Child.objects.filter(parent=self.request.user)
        return context

class ChildrenDashboardView(ParentRequiredMixin, ListView):
    model = Child
    template_name = 'child/children_dashboard.html'
    context_object_name = 'children'
    paginate_by = 6

    def get_queryset(self):
        # Only show children belonging to the logged-in parent
        return Child.objects.select_related('parent').filter(parent=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent'] = self.request.user
        context['active_section'] = 'my_children'
        return context

class ChildDashboardView(ParentRequiredMixin, DetailView):
    model = Child
    template_name = 'child/child_dashboard.html'
    context_object_name = 'child'
    pk_url_kwarg = 'child_id'  # Use ID instead of slug

    def get_object(self, queryset=None):
        child = super().get_object(queryset)
        if child.parent != self.request.user:
            logger.warning(f"Permission denied for user {self.request.user} to access child {child.id}.")
            raise PermissionDenied("You don't have permission to view this child")
        return child

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent'] = self.request.user
        # Add any additional context you need
        context['active_section'] = 'dashboard'  # Example for tabbed interface
        return context
