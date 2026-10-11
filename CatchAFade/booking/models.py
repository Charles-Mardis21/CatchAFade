from django.db import models
from django.core.exceptions import ValidationError
from datetime import timedelta
import uuid
from django.conf import settings

# Create your models here.

class Barber(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="barber_profile"
    )

    name = models.CharField(max_length=100)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    
class Service(models.Model):
    name = models.CharField(max_length=100)
    duration = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class Availability(models.Model):
    barber = models.ForeignKey(
        Barber,
        on_delete=models.CASCADE,
        related_name="availability"
    )

    day_of_week = models.IntegerField(
        choices=[
            (0, "Monday"),
            (1, "Tuesday"),
            (2, "Wednesday"),
            (3, "Thursday"),
            (4, "Friday"),
            (5, "Saturday"),
            (6, "Sunday"),
        ]
    )

    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.barber.name} - {self.get_day_of_week_display()}"
    
    def clean(self):
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError(
                    "End time must be after start time."
                )
            
class Appointment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    ]

    barber = models.ForeignKey(
        Barber,
        on_delete=models.PROTECT,
        related_name="appointments"
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name="appointments"
    )

    cancellation_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=20)
    customer_email = models.EmailField(blank=True)

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="confirmed"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    sms_consent = models.BooleanField(default=False)

    confirmation_sent_at = models.DateTimeField(
        null=True,
        blank=True
    )

    reminder_sent_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.customer_name} - {self.barber.name}"
    
    def save(self, *args, **kwargs):
        if self.service_id and self.start_time:
            self.end_time = (
                self.start_time
                + timedelta(minutes=self.service.duration)
            )

        super().save(*args, **kwargs)


class TimeOff(models.Model):
    barber = models.ForeignKey(
        Barber,
        on_delete=models.CASCADE,
        related_name="time_off"
    )

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    reason = models.CharField(
        max_length=200,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["start_time"]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValidationError(
                    "Time off must end after it starts."
                )

    def __str__(self):
        return (
            f"{self.barber.name}: "
            f"{self.start_time:%b %d, %Y %I:%M %p} - "
            f"{self.end_time:%b %d, %Y %I:%M %p}"
        )
