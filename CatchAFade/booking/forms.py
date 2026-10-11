from django import forms
from .models import Availability, TimeOff


class WorkingHoursForm(forms.ModelForm):

    class Meta:
        model = Availability

        fields = [
            "day_of_week",
            "start_time",
            "end_time",
        ]

        widgets = {
            "day_of_week": forms.Select(
                attrs={"class": "form-input"}
            ),

            "start_time": forms.TimeInput(
                attrs={
                    "type": "time",
                    "class": "form-input",
                },
                format="%H:%M",
            ),

            "end_time": forms.TimeInput(
                attrs={
                    "type": "time",
                    "class": "form-input",
                },
                format="%H:%M",
            ),
        }


class TimeOffForm(forms.ModelForm):
    class Meta:
        model = TimeOff
        fields = ["start_time", "end_time", "reason"]
        widgets = {
            "start_time": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-input"},
                format="%Y-%m-%dT%H:%M",
            ),
            "end_time": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-input"},
                format="%Y-%m-%dT%H:%M",
            ),
            "reason": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Optional reason for time off",
                }
            ),
        }
