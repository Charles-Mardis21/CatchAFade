from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = "booking"

urlpatterns = [
    path(
        "", 
        views.booking_page, 
        name="book"
    ),
    path(
        "available-times/",
        views.available_times,
        name="available_times"
    ),
    path(
        "confirm/",
        views.confirm_booking,
        name="confirm_booking"
    ),
    path(
        "cancel/<uuid:token>/",
        views.cancel_appointment,
        name="cancel_appointment"
    ),
    path(
        "reschedule/<uuid:token>/",
        views.reschedule_appointment,
        name="reschedule_appointment"
    ),
    path(
        "dashboard/",
        views.barber_dashboard,
        name="dashboard"
    ),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="booking/login.html"
        ),
        name="login"
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout"
    ),
    path(
        "complete/<int:appointment_id>/",
        views.complete_appointment,
        name="complete_appointment"
    ),
    path(
        "working-hours/",
        views.working_hours,
        name="working_hours"
    ),
    path(
        "working-hours/add/",
        views.add_working_hours,
        name="add_working_hours"
    ),
    path(
        "working-hours/edit/<int:availability_id>/",
        views.edit_working_hours,
        name="edit_working_hours"
    ),
    path(
        "working-hours/delete/<int:availability_id>/",
        views.delete_working_hours,
        name="delete_working_hours"
    ),
]
