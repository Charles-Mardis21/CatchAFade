from django import forms
from .models import Availability


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