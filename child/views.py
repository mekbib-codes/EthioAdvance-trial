from django.views.generic import ListView, DetailView
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.views import View
from django.utils.translation import gettext as _
from django.db.models import OuterRef, Subquery, Prefetch


from accounts.decorators import parent_required
from .models import Child
from .forms import ChildRegistrationForm
from session.models import  Session

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
    
    def form_invalid(self, form):
        for field, errors in form.errors.items():
            for error in errors:
                if field == '__all__':
                    logger.warning(f"Form error: {error}")
                    messages.error(
                        self.request,
                        _(f"{error}"),
                        extra_tags='alert-danger'
                    )
                else:
                    logger.warning(f"Field error - {field}: {error}")
                    label = form.fields[field].label
                    messages.error(
                        self.request,
                        _(f"{label}: {error}"),
                        extra_tags='alert-danger'
                    )
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['existing_children'] = Child.objects.filter(parent=self.request.user)
        return context

class ChildrenDashboardView(ParentRequiredMixin, ListView):
    model = Child
    template_name = 'child/children_dashboard.html'
    context_object_name = 'children'
    paginate_by = 2

    def get_queryset(self):
        latest_session_id = Session.objects.filter(
            child=OuterRef('pk')
        ).order_by('-created_at').values('id')[:1]

        queryset = Child.objects.filter(
            parent=self.request.user
        ).annotate(
            latest_session_id=Subquery(latest_session_id)
        ).select_related('parent')

        session_ids = [child.latest_session_id for child in queryset if child.latest_session_id]

        sessions = Session.objects.filter(
            id__in=session_ids
        ).select_related('child')

        queryset = queryset.prefetch_related(
            Prefetch('sessions', queryset=sessions, to_attr='latest_sessions')
        )

        return queryset

    
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
        context['active_section'] = 'child_dashboard' 
        return context
