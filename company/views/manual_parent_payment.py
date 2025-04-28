from django.views.generic import CreateView, View
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction

import uuid

from payment.utils import calculate_total_payment
from payment.models import Payment
from child.models import Child
from company.forms.manual_parent_payment import ManualPaymentForm
from actions.models import Notification
from actions.utils import create_notification, create_activity_log
from accounts.models import User


class CreateManualPaymentView(CreateView):
    model = Payment
    form_class = ManualPaymentForm
    template_name = 'company/parent/manual_payment.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Verify company admin permissions
        if not request.user.role == User.Role.COMPANY:
            messages.error(request, "You don't have permission to record payments")
            return redirect('company:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['parent'] = self.get_parent()
        return kwargs
    
    def get_parent(self):
        return get_object_or_404(
            get_user_model(), 
            pk=self.kwargs['parent_id'],
            role='PARENT',
            parent_profile__company = self.request.user
        )
    
    def get_context_data(self, **kwargs):
        
        parent = self.get_parent()

        children = parent.children.all()

        return {
            'parent': parent,
            'children': children,
            'active_section': 'parents',
        }
    
    @transaction.atomic
    def form_valid(self, form):
        parent = self.get_parent()
        child = form.cleaned_data['child']
        
        # Verify child belongs to parent
        if child.parent != parent:
            form.add_error('child', "Selected child doesn't belong to this parent")
            return self.form_invalid(form)
        
        # Create payment record
        payment = form.save(commit=False)
        payment.parent = parent
        payment.child = child
        payment.status = Payment.STATUS.SUCCESS

        amount, unpaid_sessions = calculate_total_payment(child=child)

        payment.amount = amount
        payment.tx_ref = f"MANUAL-{uuid.uuid4()}-{timezone.now().strftime('%Y%m%d')}"
        payment.save()
        
        # Associate and mark sessions as paid
        if unpaid_sessions.exists():
            payment.sessions.set(unpaid_sessions)
            unpaid_sessions.update(is_paid=True)
        
        self.create_notifications_and_logs(payment, parent, child)
        
        messages.success(
            self.request, 
            f"✅ Manual payment of {payment.amount} ETB recorded for {child.get_full_name()}"
        )
        return redirect(self.get_success_url())
    
    def create_notifications_and_logs(self, payment, parent, child):
        # Notification for company
        create_notification(
            actor=self.request.user,  # Company admin making the manual entry
            verb=f"recorded manual payment of ${payment.amount} for {child.get_full_name()}",
            content_object=payment,
            child=child,
            recipients=[parent],  # Notify parent
            extra_data={
                'parent_link': 'parent:payment_dashboard',
            },
            notification_type=Notification.NotificationTypes.SUCCESS
        )
        
        # Activity log
        create_activity_log(
            user=parent,
            action=f"Made a manual payment of {payment.amount} ETB for {child.first_name}",
            related_object=payment,
            link='parent:payment_dashboard',
        )

    def get_success_url(self):
        return reverse('company:parent_detail', kwargs={'parent_id': self.kwargs['parent_id']})
    
    def form_invalid(self, form):
        print(form.errors)
        print("Form data:", form.cleaned_data)

        messages.error(self.request, "Manual payment recording failed")
        return super().form_invalid(form)
    
class UnpaidSessionsAPIView(View):
    """API endpoint to fetch unpaid sessions for a child"""
    def get(self, request, child_id, *args, **kwargs):

        child = Child.objects.get(id=child_id)
        amount, unpaid_sessions = calculate_total_payment(child=child)
        
        sessions_data = []
        for session in unpaid_sessions:
            sessions_data.append({
                'id': session.id,
                'text': f"{session.session_subject} ({session.formatted_duration()}) - {session.created_at.strftime('%b %d')}",
                'tutor_name': session.tutor.get_full_name(),
                'duration': session.formatted_duration(),
                'date': session.created_at.strftime('%Y-%m-%d')
            })
        
        return JsonResponse({'sessions': sessions_data, 'amount': amount}, safe=False)