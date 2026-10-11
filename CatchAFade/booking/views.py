from datetime import date, datetime, timedelta
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import Barber, Service, Appointment, Availability, TimeOff
from .services import get_available_slots
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.db import OperationalError
from .services import create_appointment
from django.urls import reverse
from .services import reschedule_existing_appointment
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from .forms import WorkingHoursForm, TimeOffForm
from django.db import transaction


def booking_page(request):
    barbers = Barber.objects.filter(active=True)
    services = Service.objects.filter(active=True)

    return render(request, "booking/booking.html", {
        "barbers": barbers,
        "services": services,
    })


def available_times(request):
    try:
        barber_id = request.GET.get("barber")
        service_id = request.GET.get("service")
        date_string = request.GET.get("date")

        selected_date = date.fromisoformat(date_string)

        barber = get_object_or_404(
            Barber, pk=barber_id, active=True
        )
        service = get_object_or_404(
            Service, pk=service_id, active=True
        )

        slots = get_available_slots(
            barber, service, selected_date
        )

        return JsonResponse({
            "slots": [
                {
                    "value": slot.isoformat(),
                    "label": timezone.localtime(
                        slot
                    ).strftime("%I:%M %p"),
                }
                for slot in slots
            ]
        })

    except (ValueError, TypeError):
        return JsonResponse(
            {"error": "Invalid booking selection."},
            status=400
        )



@require_POST
def confirm_booking(request):
    try:
        barber_id = int(request.POST.get("barber"))
        service_id = int(request.POST.get("service"))

        start_time = datetime.fromisoformat(
            request.POST.get("start_time")
        )

        if timezone.is_naive(start_time):
            raise ValueError("Timezone is required.")

        appointment = create_appointment(
            sms_consent=request.POST.get("sms_consent") == "on",
            barber_id=barber_id,
            service_id=service_id,
            start_time=start_time,
            customer_name=request.POST.get(
                "customer_name", ""
            ),
            customer_phone=request.POST.get(
                "customer_phone", ""
            ),
            customer_email=request.POST.get(
                "customer_email", ""
            )
        )

        return JsonResponse({
            "success": True,
            "appointment_id": appointment.id,
            "message": "Your appointment is confirmed!",
            "cancellation_url": reverse(
                "booking:cancel_appointment",
                kwargs={"token": appointment.cancellation_token}
            ),
            "reschedule_url": reverse(
                "booking:reschedule_appointment",
                kwargs={"token": appointment.cancellation_token}
            )
        })

    except (ValueError, TypeError):
        return JsonResponse(
            {"error": "Invalid booking information."},
            status=400
        )

    except (Barber.DoesNotExist, Service.DoesNotExist):
        return JsonResponse(
            {"error": "Barber or service unavailable."},
            status=400
        )

    except ValidationError as error:
        return JsonResponse(
            {"error": error.messages[0]},
            status=400
        )

    except OperationalError:
        return JsonResponse(
            {"error": "Booking is busy. Please try again."},
            status=503
        )

@require_http_methods(["GET", "POST"])
def cancel_appointment(request, token):
    appointment = get_object_or_404(
        Appointment.objects.select_related("barber", "service"),
        cancellation_token=token
    )

    if request.method == "POST":
        if (
            appointment.status in ["pending", "confirmed"]
            and appointment.start_time > timezone.now()
        ):
            appointment.status = "cancelled"
            appointment.save(update_fields=["status"])

        return render(request, "booking/cancel.html", {
            "appointment": appointment,
            "cancelled": True,
        })

    return render(request, "booking/cancel.html", {
        "appointment": appointment,
        "cancelled": False,
    })

@require_http_methods(["GET", "POST"])
def reschedule_appointment(request, token):
    appointment = get_object_or_404(
        Appointment.objects.select_related("barber", "service"),
        cancellation_token=token
    )

    error = None
    success = False

    if appointment.status not in ["pending", "confirmed"]:
        error = "This appointment can no longer be rescheduled."

    elif appointment.start_time <= timezone.now():
        error = "Past appointments cannot be rescheduled."

    elif request.method == "POST":
        try:
            new_start_time = datetime.fromisoformat(
                request.POST.get("start_time", "")
            )

            if timezone.is_naive(new_start_time):
                raise ValueError("Timezone is required.")

            appointment = reschedule_existing_appointment(
                token, new_start_time
            )
            success = True

        except (ValueError, TypeError):
            error = "Please select a valid appointment time."

        except ValidationError as exc:
            error = exc.messages[0]

    return render(request, "booking/reschedule.html", {
        "appointment": appointment,
        "error": error,
        "success": success
    })

@login_required
def barber_dashboard(request):
    try:
        barber = request.user.barber_profile
    except Barber.DoesNotExist:
        raise PermissionDenied("No barber profile is linked to this account.")

    if not barber.active:
        raise PermissionDenied("This barber account is inactive.")

    now = timezone.localtime()
    today = now.date()

    appointments = Appointment.objects.filter(
        barber=barber
    ).exclude(
        status="cancelled"
    ).select_related(
        "service"
    ).order_by("start_time")

    todays_appointments = appointments.filter(
        start_time__date=today
    )

    upcoming_appointments = appointments.filter(
        start_time__gte=timezone.now()
    )

    context = {
        "barber": barber,
        "todays_appointments": todays_appointments,
        "upcoming_appointments": upcoming_appointments[:10],
        "today_count": todays_appointments.count(),
        "upcoming_count": upcoming_appointments.count(),
        "completed_count": todays_appointments.filter(
            status="completed"
        ).count(),
        "now": timezone.now(),
    }

    return render(
        
        request,
        "booking/dashboard.html",
        context
    )

@login_required
@require_POST
def complete_appointment(request, appointment_id):

    barber = get_object_or_404(
        Barber,
        user=request.user,
        active=True
    )

    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        barber=barber,
        status="confirmed"
    )

    if appointment.start_time > timezone.now():
        messages.error(
            request,
            "You cannot complete a future appointment."
        )
        return redirect("booking:dashboard")

    appointment.status = "completed"
    appointment.save(update_fields=["status"])

    messages.success(
        request,
        "Appointment marked as completed."
    )

    return redirect("booking:dashboard")

@login_required
def working_hours(request):
    barber = get_object_or_404(
        Barber,
        user=request.user,
        active=True
    )

    availability = Availability.objects.filter(
        barber=barber
    ).order_by("day_of_week", "start_time")

    context = {
        "barber": barber,
        "availability": availability,
    }

    return render(
        request,
        "booking/working_hours.html",
        context
    )

@login_required
@require_POST
def add_working_hours(request):

    barber = get_object_or_404(
        Barber,
        user=request.user,
        active=True
    )

    form = WorkingHoursForm(request.POST)

    if form.is_valid():

        availability = form.save(commit=False)

        availability.barber = barber

        overlapping = Availability.objects.filter(
            barber=barber,
            day_of_week=availability.day_of_week,
            start_time__lt=availability.end_time,
            end_time__gt=availability.start_time,
        ).exists()

        if overlapping:
            messages.error(
                request,
                "These working hours overlap an existing shift."
            )
        else:
            availability.save()

            messages.success(
                request,
                "Working hours added successfully."
            )

    else:
        messages.error(
            request,
            "Invalid working hours. Check your times and try again."
        )

    return redirect("booking:working_hours")

@login_required
@require_POST
def edit_working_hours(request, availability_id):
    barber = get_object_or_404(
        Barber,
        user=request.user,
        active=True
    )

    with transaction.atomic():
        # Lock this barber's record during the update.
        Barber.objects.select_for_update().get(pk=barber.pk)

        shift = get_object_or_404(
            Availability.objects.select_for_update(),
            id=availability_id,
            barber=barber
        )

        # Preserve the original values before editing.
        old_day = shift.day_of_week
        old_start = shift.start_time
        old_end = shift.end_time

        form = WorkingHoursForm(request.POST, instance=shift)

        if not form.is_valid():
            messages.error(request, "Invalid working hours.")
            return redirect("booking:working_hours")

        updated_shift = form.save(commit=False)
        # Keep the original weekday, regardless of submitted form data.
        updated_shift.day_of_week = old_day

        overlapping = Availability.objects.filter(
            barber=barber,
            day_of_week=updated_shift.day_of_week,
            start_time__lt=updated_shift.end_time,
            end_time__gt=updated_shift.start_time,
        ).exclude(id=shift.id).exists()

        if overlapping:
            messages.error(
                request,
                "These hours overlap another existing shift."
            )
            return redirect("booking:working_hours")

        # Check upcoming bookings affected by the old schedule.
        appointments = Appointment.objects.filter(
            barber=barber,
            status__in=["confirmed", "pending"],
            start_time__gte=timezone.now(),
        )

        other_shifts = Availability.objects.filter(
            barber=barber
        ).exclude(id=shift.id)

        for appointment in appointments:
            local_start = timezone.localtime(appointment.start_time)
            local_end = timezone.localtime(appointment.end_time)

            # Only appointments on the original weekday can lose coverage.
            if local_start.weekday() != old_day:
                continue

            start = local_start.time()
            end = local_end.time()

            # Only check appointments previously covered by this shift.
            if not (old_start <= start and end <= old_end):
                continue

            new_shift_covers = (
                updated_shift.day_of_week == old_day
                and updated_shift.start_time <= start
                and end <= updated_shift.end_time
            )

            another_shift_covers = any(
                other.day_of_week == old_day
                and other.start_time <= start
                and end <= other.end_time
                for other in other_shifts
            )

            if not (new_shift_covers or another_shift_covers):
                messages.error(
                    request,
                    "You have upcoming appointments during those hours. "
                    "Please reschedule them before changing this shift."
                )
                return redirect("booking:working_hours")

        updated_shift.save()

    messages.success(
        request,
        "Working hours updated successfully."
    )

    return redirect("booking:working_hours")

@login_required
@require_POST
def delete_working_hours(request, availability_id):
    barber = get_object_or_404(
        Barber,
        user=request.user,
        active=True
    )

    with transaction.atomic():
        # Coordinate schedule changes for this barber.
        Barber.objects.select_for_update().get(pk=barber.pk)

        shift = get_object_or_404(
            Availability.objects.select_for_update(),
            id=availability_id,
            barber=barber
        )

        # Find the barber's upcoming active appointments.
        appointments = Appointment.objects.filter(
            barber=barber,
            status__in=["confirmed", "pending"],
            start_time__gte=timezone.now()
        )

        # Other shifts that would remain after deletion.
        other_shifts = list(
            Availability.objects.filter(
                barber=barber
            ).exclude(id=shift.id)
        )

        for appointment in appointments:
            local_start = timezone.localtime(appointment.start_time)
            local_end = timezone.localtime(appointment.end_time)

            # Ignore appointments on other weekdays.
            if local_start.weekday() != shift.day_of_week:
                continue

            start = local_start.time()
            end = local_end.time()

            # Check whether another shift still covers the booking.
            still_covered = any(
                other.day_of_week == shift.day_of_week
                and other.start_time <= start
                and end <= other.end_time
                for other in other_shifts
            )

            if not still_covered:
                messages.error(
                    request,
                    "This shift has upcoming appointments. "
                    "Reschedule them before deleting it."
                )
                return redirect("booking:working_hours")

        shift.delete()

    messages.success(
        request,
        "Working hours deleted successfully."
    )

    return redirect("booking:working_hours")


@login_required
def manage_time_off(request):
    barber = get_object_or_404(
        Barber,
        user=request.user,
        active=True
    )

    time_off = TimeOff.objects.filter(
        barber=barber,
        end_time__gte=timezone.now()
    ).order_by("start_time")

    form = TimeOffForm()

    return render(request, "booking/time_off.html", {
        "barber": barber,
        "time_off": time_off,
        "form": form,
    })


@login_required
@require_POST
def add_time_off(request):
    barber = get_object_or_404(
        Barber,
        user=request.user,
        active=True
    )

    form = TimeOffForm(request.POST)

    if form.is_valid():
        new_time_off = form.save(commit=False)
        new_time_off.barber = barber

        if new_time_off.start_time < timezone.now():
            messages.error(
                request,
                "Time off cannot start in the past."
            )
        elif TimeOff.objects.filter(
            barber=barber,
            start_time__lt=new_time_off.end_time,
            end_time__gt=new_time_off.start_time
        ).exists():
            messages.error(
                request,
                "This time off overlaps an existing entry."
            )
        elif Appointment.objects.filter(
            barber=barber,
            status__in=["pending", "confirmed"],
            start_time__lt=new_time_off.end_time,
            end_time__gt=new_time_off.start_time
        ).exists():
            messages.error(
                request,
                "You have existing appointments during this period."
            )
        else:
            new_time_off.save()
            messages.success(request, "Time off added successfully!")
    else:
        messages.error(
            request,
            "Invalid time off. Check your dates and times."
        )

    return redirect("manage_time_off")



@login_required
@require_POST
def delete_time_off(request, time_off_id):
    barber = get_object_or_404(
        Barber,
        user=request.user,
        active=True
    )

    entry = get_object_or_404(
        TimeOff,
        pk=time_off_id,
        barber=barber
    )

    entry.delete()

    messages.success(
        request,
        "Time off removed successfully!"
    )

    return redirect("booking:manage_time_off")


@login_required
@require_POST
@transaction.atomic
def add_time_off(request):
    barber = get_object_or_404(
        Barber.objects.select_for_update(),
        user=request.user,
        active=True
    )

    form = TimeOffForm(request.POST)

    if not form.is_valid():
        messages.error(
            request,
            "Invalid time off. Check your start and end times."
        )
        return redirect("booking:manage_time_off")

    new_time_off = form.save(commit=False)
    new_time_off.barber = barber

    if new_time_off.start_time < timezone.now():
        messages.error(
            request,
            "Time off cannot start in the past."
        )
    elif TimeOff.objects.filter(
        barber=barber,
        start_time__lt=new_time_off.end_time,
        end_time__gt=new_time_off.start_time
    ).exists():
        messages.error(
            request,
            "This time off overlaps an existing entry."
        )
    elif Appointment.objects.filter(
        barber=barber,
        status__in=["pending", "confirmed"],
        start_time__lt=new_time_off.end_time,
        end_time__gt=new_time_off.start_time
    ).exists():
        messages.error(
            request,
            "You already have appointments during this period."
        )
    else:
        new_time_off.save()
        messages.success(
            request,
            "Time off added successfully!"
        )

    return redirect("booking:manage_time_off")


@login_required
def barber_edit_appointment(request, appointment_id):
    barber = get_object_or_404(
        Barber,
        user=request.user,
        active=True
    )

    appointment = get_object_or_404(
        Appointment,
        pk=appointment_id,
        barber=barber
    )

    if appointment.status not in ["pending", "confirmed"]:
        messages.error(request, "This appointment cannot be edited.")
        return redirect("booking:dashboard")

    if request.method == "POST":
        date_str = request.POST.get("date")
        time_str = request.POST.get("time")

        try:
            new_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            new_time = datetime.strptime(time_str, "%H:%M").time()

            new_start = timezone.make_aware(
                datetime.combine(new_date, new_time)
            )

            with transaction.atomic():
                locked_barber = Barber.objects.select_for_update().get(
                    pk=barber.pk
                )

                locked_appointment = Appointment.objects.select_for_update().get(
                    pk=appointment.pk,
                    barber=locked_barber
                )

                if locked_appointment.status not in ["pending", "confirmed"]:
                    raise ValidationError("This appointment can no longer be edited.")

                if locked_appointment.start_time <= timezone.now():
                    raise ValidationError("Past appointments cannot be edited.")

                available_slots = get_available_slots(
                    locked_barber,
                    locked_appointment.service,
                    new_date,
                    exclude_appointment_id=locked_appointment.pk
                )

                if new_start not in available_slots:
                    raise ValidationError(
                        "That time is unavailable. Please choose another."
                    )

                locked_appointment.start_time = new_start
                locked_appointment.save(
                    update_fields=["start_time", "end_time"]
                )

            messages.success(request, "Appointment rescheduled!")
            return redirect("booking:dashboard")

        except (ValueError, TypeError, ValidationError) as error:
            messages.error(request, f"Unable to reschedule: {error}")

    return render(request, "booking/barber_edit_appointment.html", {
        "appointment": appointment,
        "barber": barber,
    })


@login_required
@require_POST
def barber_cancel_appointment(request, appointment_id):
    barber = get_object_or_404(
        Barber,
        user=request.user,
        active=True
    )

    with transaction.atomic():
        appointment = get_object_or_404(
            Appointment.objects.select_for_update(),
            pk=appointment_id,
            barber=barber
        )

        if appointment.status not in ["pending", "confirmed"]:
            messages.error(
                request,
                "This appointment can no longer be cancelled."
            )
        elif appointment.start_time <= timezone.now():
            messages.error(
                request,
                "Past appointments cannot be cancelled."
            )
        else:
            appointment.status = "cancelled"
            appointment.save(update_fields=["status"])
            messages.success(
                request,
                "Appointment cancelled. The time slot is available again."
            )

    return redirect("booking:dashboard")

@login_required
def barber_available_times(request, appointment_id):
    barber = get_object_or_404(
        Barber,
        user=request.user
    )

    appointment = get_object_or_404(
        Appointment,
        pk=appointment_id,
        barber=barber,
        status__in=["pending", "confirmed"]
    )

    try:
        date_string = request.GET.get("date")
        selected_date = date.fromisoformat(date_string)

        slots = get_available_slots(
            barber,
            appointment.service,
            selected_date,
            exclude_appointment_id=appointment.pk
        )

        return JsonResponse({
            "slots": [
                {
                    "value": slot.isoformat(),
                    "label": timezone.localtime(slot).strftime("%I:%M %p"),
                }
                for slot in slots
            ]
        })

    except (ValueError, TypeError):
        return JsonResponse(
            {"error": "Invalid date."},
            status=400
        )