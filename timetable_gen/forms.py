# forms.py
from django import forms
import datetime

class PreferencesForm(forms.Form):
    preferred_start_time = forms.TimeField(
        widget=forms.TimeInput(
            format="%H:%M",  # 24-hour format
            attrs={
                'placeholder': '09:00',  # Placeholder in 24-hour format
                'type': 'time'
            }
        ),
        input_formats=["%H:%M"],  # Accept only 24-hour formatted times
        initial="08:00"  # Make sure the initial value is in 24-hour format
    )
    preferred_end_time = forms.TimeField(
        widget=forms.TimeInput(
            format="%H:%M",
            attrs={
                'placeholder': '17:00',
                'type': 'time'
            }
        ),
        input_formats=["%H:%M"],
        initial="22:00"
    )
    days_off = forms.MultipleChoiceField(
        required=False,
        label='Days off',
        choices=[
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday')
    ],
        initial=None,
        widget=forms.CheckboxSelectMultiple
    )
    busy_sched = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(),
        initial=False
    )
    
    # Critical features fields
    critical_ideal_lecturers = forms.BooleanField(required=False, label='Ideal Lecturers')
    critical_unit_importance = forms.BooleanField(required=False, label='Unit Importance')
    critical_days_off = forms.BooleanField(required=False, label='Days off')
    critical_preferred_start_time = forms.BooleanField(required=False, label='Start time')
    critical_preferred_end_time = forms.BooleanField(required=False, label='End time')
    critical_busyness_level = forms.BooleanField(required=False, label='Schedule Tightness')
    
    # Preference order fields
    preference_order_ideal_lecturers = forms.IntegerField(label='Ideal Lecturers', min_value=1, max_value=6)
    preference_order_unit_importance = forms.IntegerField(min_value=1, max_value=6, label='Unit Importance')
    preference_order_days_off = forms.IntegerField(min_value=1, max_value=6, label='Days off')
    preference_order_preferred_start_time = forms.IntegerField(min_value=1, max_value=6, label='Start time')
    preference_order_preferred_end_time = forms.IntegerField(min_value=1, max_value=6, label='End time')
    preference_order_busyness_level = forms.IntegerField(min_value=1, max_value=6, label='Schedule Tightness')

    def __init__(self, *args, **kwargs):
        available_lecturers = kwargs.pop('available_lecturers', None)
        units = kwargs.pop('units', None)
        super(PreferencesForm, self).__init__(*args, **kwargs)

        # Dynamic field for lecturers.
        if available_lecturers:
            choices = [
                (i, f"{lec[0]} - {lec[1]} ({lec[2]})")
                for i, lec in enumerate(available_lecturers)
            ]
            self.fields['lecturers'] = forms.MultipleChoiceField(
                choices=choices,
                widget=forms.CheckboxSelectMultiple,
                required=False,
                label="Select Lecturers"
            )
        
        # Dynamic fields for unit rankings.
        if units:
            for unit_name, unit_code in units:
                field_name = f"unit_rank_{unit_code}"
                self.fields[field_name] = forms.IntegerField(
                    min_value=1,
                    max_value=4,
                    required=True,
                    label=f"{unit_name} ({unit_code}) Ranking"
                )
