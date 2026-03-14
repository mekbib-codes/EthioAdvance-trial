from django.views.generic import CreateView, View, FormView
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum

import uuid

from accounts.mixins import CompanyRequiredMixin
from payment.utils import calculate_total_payment
from payment.models import Payment, TutorPayments
from child.models import Child
from company.forms.manual_payments import ManualPaymentForm
from actions.models import Notification
from actions.utils import create_notification, create_activity_log
from session.models import Session

class CreateManualPaymentView(CompanyRequiredMixin):
    model = None # Must be overriden by ParentManualPayment and TutorManualPayment
    form_class = ManualPaymentForm
    template_name = None # Must be overridden by ParentManualPayment and TutorManualPayment

    def create_notifications_and_logs(self, payment, user, child, verb, action):
        # Notification for company
        create_notification(
            actor=self.request.user,  # Company admin making the manual entry
            verb=verb,
            content_object=payment,
            child=child,
            recipients=[user],  # Notify user
            extra_data={
                f'{user.role.lower()}_link': f'{user.role.lower()}:payment_dashboard',
            },
            notification_type=Notification.NotificationTypes.SUCCESS
        )
        
        # Activity log
        create_activity_log(
            user=user,
            action=action,
            related_object=payment,
            link=f'{user.role.lower()}:payment_dashboard',
        )
    
    def form_invalid(self, form):
        print(form.errors)
        print("Form data:", form.cleaned_data)

        messages.error(self.request, "Manual payment recording failed")
        return super().form_invalid(form)

class ManualParentPayment(CreateManualPaymentView, CreateView):
    model = Payment
    template_name = 'company/parent/manual_payment.html'

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
        
        self.create_notifications_and_logs(payment, parent, child,
                                           verb=f"recorded manual payment of ${payment.amount} for {child.get_full_name()}",
                                           action=f"Made a manual payment of {payment.amount} ETB for {child.first_name}")
        
        messages.success(
            self.request, 
            f"✅ Manual payment of {payment.amount} ETB recorded for {child.get_full_name()}"
        )
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        return reverse('company:parent_detail', kwargs={'parent_id': self.kwargs['parent_id']})

class ManualTutorPayment(CreateManualPaymentView, FormView):
    model = TutorPayments
    template_name = 'company/tutor/manual_payment.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tutor'] = self.get_tutor()
        return kwargs
    
    def get_tutor(self):
        return get_object_or_404(
            get_user_model(), 
            pk=self.kwargs['tutor_id'],
            role='TUTOR',
            tutor_profile__company = self.request.user
        )
    
    def get_context_data(self, **kwargs):
        
        tutor = self.get_tutor()

        students = tutor.students.all()

        return {
            'tutor': tutor,
            'students': students,
            'active_section': 'tutors',
        }
    
    @transaction.atomic
    def form_valid(self, form):
        tutor = self.get_tutor()
        child = form.cleaned_data['child']
        
        # Verify child belongs to tutor
        if child.tutor != tutor:
            form.add_error('child', "Selected child doesn't belong to this tutor")
            return self.form_invalid(form)
        
        # Update status and tx-ref of tutor payment records
        requested_payment = TutorPayments.objects.prefetch_related('sessions').get(tutor=tutor, child=child, status=TutorPayments.STATUS.PENDING)
        requested_payment.status = TutorPayments.STATUS.SUCCESS
        requested_payment.tx_ref = f"MANUAL-{uuid.uuid4()}-{timezone.now().strftime('%Y%m%d')}"
        requested_payment.save()

        # Associate and mark sessions as paid
        sessions = requested_payment.sessions.all()
        sessions.update(paid_to_tutor=True)

        
        amount = requested_payment.amount

        self.create_notifications_and_logs(requested_payment, tutor, child,
                                           verb=f"recorded manual payment of ${amount} for sessions with {child.get_full_name()}",
                                           action=f"You are paid {amount} ETB for sessions with {child.get_full_name()}")
        
        messages.success(
            self.request, 
            f"✅ Tutor payment of {amount} ETB recorded for {tutor.get_full_name()}"
        )
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        return reverse('company:tutor_detail', kwargs={'tutor_id': self.kwargs['tutor_id']})

class UnpaidChildSessionsApIView(View):
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
    

class UnpaidTutorSessionsAPIView(View):
    """API endpoint to fetch requested tutor payments"""

    def get(self, request, child_id, *args, **kwargs):
        child = Child.objects.get(id=child_id)

        # Prefetch sessions to avoid N+1 queries
        requested_payment = TutorPayments.objects.prefetch_related('sessions').get(child=child, status=TutorPayments.STATUS.PENDING)

        # Aggregate all related sessions from the payments
        sessions = requested_payment.sessions.all()

        # Aggregate total amount
        amount = requested_payment.amount

        # Build sessions data
        sessions_data = []
        for session in sessions:
            sessions_data.append({
                'id': session.id,
                'text': f"{session.session_subject} ({session.formatted_duration()}) - {session.created_at.strftime('%b %d')}",
                'parent_name': session.child.parent.get_full_name(),
                'duration': session.formatted_duration(),
                'date': session.created_at.strftime('%Y-%m-%d')
            })

        return JsonResponse({'sessions': sessions_data, 'amount': amount}, safe=False)
