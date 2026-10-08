from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from booking.models import Appointment
from booking.sms import send_appointment_reminder


class Command(BaseCommand):
    help = "Send reminders for upcoming appointments"

    def handle(self, *args, **options):
        now = timezone.now()

        # Appointments approximately 24 hours away.
        target = now + timedelta(hours=24)

        # A one-hour window supports hourly execution.
        window_end = target + timedelta(hours=1)

        appointments = Appointment.objects.filter(
            status="confirmed",
            start_time__gte=target,
            start_time__lt=window_end,
            reminder_sent_at__isnull=True,
            sms_consent=True,
        )

        count = 0

        for appointment in appointments:
            result = send_appointment_reminder(appointment)

            # Simulation is not actual SMS delivery.
            if result.get("simulated"):
                self.stdout.write(
                    f"Simulated reminder for appointment {appointment.id}"
                )
                count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Finished. {count} reminder(s) simulated."
            )
        )
