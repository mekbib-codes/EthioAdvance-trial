from django.views import View
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from .models import Payment
from child.models import Child
from .utils import calculate_total_payment
import uuid
import requests
import logging
import json

from actions.models import Notification
from actions.utils import create_notification, create_activity_log

logger = logging.getLogger(__name__)

logger = logging.getLogger('app')

class InitializePaymentView(View):
    def post(self, request, child_id, *args, **kwargs):
        # Fetch the child object
        child = get_object_or_404(Child, id=child_id)
        amount, sessions = calculate_total_payment(child)

        if not sessions:
            return JsonResponse({"error": "No unpaid sessions."}, status=400)

        # Generate a unique transaction reference
        tx_ref = str(uuid.uuid4())

        # Create the Payment record
        payment = Payment.objects.create(
            tx_ref=tx_ref,
            child=child,
            parent=child.parent,
            amount=amount,
            status="pending",
        )
        payment.sessions.set(sessions)  # Link sessions to this payment

        # Prepare the payload for Chapa
        payload = {
            "amount": str(amount),
            "currency": "ETB",
            "email": child.parent.email,
            "first_name": child.parent.first_name,
            "last_name": child.parent.last_name,
            "tx_ref": tx_ref,
            "callback_url": settings.CALL_BACK_URL,
            "return_url": settings.CALL_BACK_URL,
            "customization": {
                "title": "Tutoring Payment",
                "description": f"Payment for sessions of {child.first_name} {child.last_name}"
            },
            "custom_fields": [{"child_id": str(child.id)}]
        }

        headers = {
            "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"
        }

        try:
            # Send the request to Chapa
            response = requests.post(f"{settings.CHAPA_BASE_URL}/transaction/initialize", json=payload, headers=headers)
            response.raise_for_status()  # Raise an exception for HTTP errors
            data = response.json()

            if data.get("status") == "success":
                logger.info(f"Payment initialized successfully for child {child.id} with tx_ref {tx_ref}")
                return redirect(data["data"]["checkout_url"])
            else:
                logger.error(f"Failed to initialize payment for child {child.id}: {data}")
                payment.status = "failed"
                payment.save()
                return JsonResponse({"error": "Failed to initialize payment."}, status=400)

        except requests.RequestException as e:
            logger.error(f"Error initializing payment for child {child.id}: {str(e)}")
            payment.status = "failed"
            payment.save()
            return JsonResponse({"error": "An error occurred while initializing payment."}, status=500)

@method_decorator(csrf_exempt, name='dispatch')  # Exempt CSRF for webhook
class ChapaWebhookView(View):
    def post(self, request, *args, **kwargs):
        """
        Handle webhook requests from Chapa to verify payment status.
        """
        try:
            # Parse the JSON payload
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON payload received in webhook.")
            return HttpResponseBadRequest("Invalid JSON")

        # Extract the transaction reference (tx_ref)
        tx_ref = payload.get("tx_ref")
        if not tx_ref:
            logger.error("Missing tx_ref in webhook payload.")
            return HttpResponseForbidden("Missing tx_ref")

        # Find the Payment object
        try:
            payment = Payment.objects.get(tx_ref=tx_ref)
        except Payment.DoesNotExist:
            logger.error(f"Payment with tx_ref {tx_ref} does not exist.")
            return HttpResponseForbidden("Invalid tx_ref")

        # Verify the payment with Chapa
        headers = {"Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"}
        verify_url = f"{settings.CHAPA_BASE_URL}/transaction/verify/{tx_ref}"

        try:
            verify_response = requests.get(verify_url, headers=headers)
            verify_response.raise_for_status()  # Raise an exception for HTTP errors
            verify_data = verify_response.json()
        except requests.RequestException as e:
            logger.error(f"Error verifying payment with tx_ref {tx_ref}: {str(e)}")
            return HttpResponseBadRequest("Error verifying payment.")

        # Check the verification response
        if verify_data.get("status") == "success" and verify_data["data"]["status"] == "success":
            if payment.status != "success":
                # Update payment status
                payment.status = "success"
                payment.save()

                # Mark sessions as paid
                payment.sessions.update(is_paid=True)
                
                # Notify the company
                parent, child = payment.parent, payment.child
                company = parent.profile.company
                create_notification(
                    actor=parent,
                    verb=f"made a payment of ${payment.amount} for {child.get_full_name()}.",
                    content_object=payment,
                    child=child,
                    recipients=[company],  # Notify only the company
                    extra_data={
                        "payment_reference": payment.tx_ref,
                    },
                    notification_type=Notification.NotificationTypes.SUCCESS
                )

                create_activity_log(
                    user=parent,
                    action=f"Made a payment of { payment.amount } ETB for { child.first_name }",
                    related_object=payment,
                    link='parent:payment_dashboard',
                )

                logger.info(f"Payment with tx_ref {tx_ref} verified successfully.")
            return JsonResponse({"message": "Payment verified and sessions marked as paid."})
        else:
            # Update payment status to failed (optional)
            payment.status = "failed"
            payment.save()

            logger.warning(f"Payment verification failed for tx_ref {tx_ref}.")
            return HttpResponseForbidden("Verification failed.")