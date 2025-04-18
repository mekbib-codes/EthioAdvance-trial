from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from payment.models import TutorPayments
from tutor.models import Tutor


class Command(BaseCommand):
    help = "Marks a specific tutor's pending payments as successful and updates linked sessions as paid."

    def add_arguments(self, parser):
        parser.add_argument(
            '--tutor',
            type=int,
            required=True,
            help='ID of the tutor whose pending payments should be marked as successful.'
        )

    def handle(self, *args, **options):
        tutor_id = options['tutor']

        try:
            tutor = Tutor.objects.get(id=tutor_id)
        except Tutor.DoesNotExist:
            raise CommandError(f"Tutor with ID {tutor_id} does not exist.")

        self.stdout.write(f"Processing payments for Tutor: {tutor} (ID: {tutor_id})...")

        pending_payments = TutorPayments.objects.filter(
            status=TutorPayments.STATUS.PENDING,
            tutor=tutor,
            sessions__isnull=False
        ).distinct()

        if not pending_payments.exists():
            self.stdout.write(self.style.WARNING(f"No pending payments found for Tutor {tutor}."))
            return

        for payment in pending_payments:
            with transaction.atomic():
                payment.status = TutorPayments.STATUS.SUCCESS
                payment.save()

                linked_sessions = payment.sessions.all()
                linked_sessions.update(paid_to_tutor=True)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Payment {payment.tx_ref} marked SUCCESS, {linked_sessions.count()} sessions updated."
                    )
                )

        self.stdout.write(self.style.SUCCESS(
            f"All pending payments for Tutor {tutor} have been marked as successful!"
        ))
