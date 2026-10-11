from datetime import datetime, timedelta

from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import (
    Availability,
    Appointment,
    TimeOff,
    Barber,
    Service,
)
from .sms import send_booking_confirmation


def get_available_slots(barber, service, selected_date, exclude_appointment_id=None):
    if not barber.active or not service.active:
        return []

    shifts = Availability.objects.filter(
        barber=barber,
        day_of_week=selected_date.weekday()
    ).order_by("start_time")

    duration = timedelta(minutes=service.duration)
    interval = timedelta(minutes=15)
    now = timezone.now()

    slots = []

    for shift in shifts:
        start = timezone.make_aware(
            datetime.combine(selected_date, shift.start_time)
        )
        end = timezone.make_aware(
            datetime.combine(selected_date, shift.end_time)
        )

        if end <= start:
            continue

        current = start

        while current + duration <= end:
            proposed_end = current + duration

            booked_appointments = Appointment.objects.filter(
                barber=barber,
                status__in=["pending", "confirmed"],
                start_time__lt=proposed_end,
                end_time__gt=current,
            )

            if exclude_appointment_id is not None:
                booked_appointments = booked_appointments.exclude(
                    pk=exclude_appointment_id
                )

            conflict = booked_appointments.exists()

            time_off_conflict = overlaps_time_off(
                barber,
                current,
                proposed_end
            )

            if current > now and not conflict and not time_off_conflict:
                slots.append(current)
            
            current += interval

    return sorted(set(slots))


@transaction.atomic
def create_appointment(
    barber_id,
    service_id,
    start_time,
    customer_name,
    customer_phone,
    customer_email="",
    sms_consent=False
):
    # Lock the barber row while checking and saving.
    barber = Barber.objects.select_for_update().get(
        pk=barber_id,
        active=True
    )

    service = Service.objects.get(
        pk=service_id,
        active=True
    )

    # Always calculate the end time on the server.
    end_time = start_time + timedelta(
        minutes=service.duration
    )

    if not customer_name.strip() or not customer_phone.strip():
        raise ValidationError(
            "Name and phone number are required."
        )

    if start_time <= timezone.now():
        raise ValidationError(
            "Appointments must be in the future."
        )

    # Reuse the scheduling engine to verify this slot.
    available_slots = get_available_slots(
        barber,
        service,
        timezone.localtime(start_time).date()
    )

    if start_time not in available_slots:
        raise ValidationError(
            "This appointment time is no longer available."
        )

    appointment = Appointment.objects.create(
        sms_consent=False,
        barber=barber,
        service=service,
        customer_name=customer_name.strip(),
        customer_phone=customer_phone.strip(),
        customer_email=customer_email.strip(),
        start_time=start_time,
        end_time=end_time,
        status="confirmed"
    )

    ### if appointment.sms_consent:
    ###    transaction.on_commit(
    ###        lambda: send_booking_confirmation(appointment)
    ###)

    return appointment


@transaction.atomic
def reschedule_existing_appointment(token, new_start_time):
    appointment = get_object_or_404(
        Appointment.objects.select_for_update().select_related(
            "barber", "service"
        ),
        cancellation_token=token
    )

    if appointment.status not in ["pending", "confirmed"]:
        raise ValidationError("This appointment cannot be rescheduled.")

    if appointment.start_time <= timezone.now():
        raise ValidationError("Past appointments cannot be rescheduled.")

    if new_start_time <= timezone.now():
        raise ValidationError("Please choose a future appointment time.")

    # Lock the barber row to coordinate scheduling changes.
    barber = Barber.objects.select_for_update().get(
        pk=appointment.barber_id
    )

    # Temporarily exclude this appointment from conflict checks.
    available_slots = get_available_slots(
        barber,
        appointment.service,
        timezone.localtime(new_start_time).date(),
        exclude_appointment_id=appointment.pk
    )

    if new_start_time not in available_slots:
        raise ValidationError(
            "That time is no longer available. Please choose another."
        )

    appointment.start_time = new_start_time
    appointment.save(update_fields=["start_time", "end_time"])

    return appointment



def overlaps_time_off(barber, start_time, end_time):
    """
    Returns True if an appointment overlaps
    the barber's scheduled time off.
    """
    return TimeOff.objects.filter(
        barber=barber,
        start_time__lt=end_time,
        end_time__gt=start_time
    ).exists()


