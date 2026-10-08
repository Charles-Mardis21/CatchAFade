from django.contrib import admin
from .models import Barber, Service, Availability, Appointment

# Register your models here.

@admin.register(Barber)
class BarberAdmin(admin.ModelAdmin):
    list_display = ("name", "active")
    list_filter = ("active",)
    search_fields = ("name",)

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "duration", "price", "active")
    list_filter = ("active",)

@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = (
        "barber",
        "day_of_week",
        "start_time",
        "end_time",
    )
    list_filter = ("barber", "day_of_week")

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "customer_name",
        "barber",
        "service",
        "start_time",
        "status",
    )
    list_filter = ("barber", "status", "start_time")
    search_fields = ("customer_name", "customer_phone")