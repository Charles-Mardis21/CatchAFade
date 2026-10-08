from django.conf import settings
from twilio.rest import Client
from django.utils import timezone


def send_booking_confirmation(appointment):
    local_time = timezone.localtime(appointment.start_time)
    message = (
        f"Catch A Fade: Your appointment with "
        f"{appointment.barber.name} is confirmed "
        f"for {local_time:%B %d at %I:%M %p}."
    )

    # Safe development mode: no real text is sent.
    if settings.DEBUG:
        print(f"[TEST SMS] To: {appointment.customer_phone}")
        print(f"[TEST SMS] Message: {message}")
        return {"simulated": True}

    raise RuntimeError(
        "Production SMS is not configured yet."
    )

def send_appointment_reminder(appointment):
    local_time = timezone.localtime(appointment.start_time)

    message = (
        f"Catch A Fade reminder: You have an appointment "
        f"with {appointment.barber.name} tomorrow "
        f"at {local_time:%I:%M %p}. "
        f"We look forward to seeing you!"
    )

    if settings.DEBUG:
        print(f"[TEST REMINDER] To: {appointment.customer_phone}")
        print(f"[TEST REMINDER] Message: {message}")
        return {"simulated": True}

    raise RuntimeError("Production SMS is not configured yet.")