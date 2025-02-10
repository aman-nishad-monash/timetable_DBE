from django import forms

class PreferencesForm(forms.Form):
    preferred_start_time = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'HH:MMam/pm (e.g., 09:00am)',
            'type': 'text'
        }),
        initial='08:00am'
    )
    preferred_end_time = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'HH:MMam/pm (e.g., 05:00pm)',
            'type': 'text'
        }),
        initial='10:00pm'
    )
    days_off = forms.CharField(
        required=False,
        label='Days off',
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Monday, Tuesday'}),
        initial=''
    )
    busy_sched = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(),
        initial=False
    )
    
    # Critical features fields
    critical_ideal_lecturers = forms.BooleanField(required=False,label= 'Ideal Lecturers')
    critical_unit_importance = forms.BooleanField(required=False, label= 'Unit Importance')
    critical_days_off = forms.BooleanField(required=False, label= 'Days off')
    critical_preferred_start_time = forms.BooleanField(required=False, label= 'Start time')
    critical_preferred_end_time = forms.BooleanField(required=False, label= 'End time')
    critical_busyness_level = forms.BooleanField(required=False, label= 'Schedule Tightness')
    
    # Preference order fields
    preference_order_ideal_lecturers = forms.IntegerField(label= 'Ideal Lecturers', min_value=1, max_value=6)
    preference_order_unit_importance = forms.IntegerField(min_value=1, max_value=6, label= 'Unit Importance')
    preference_order_days_off = forms.IntegerField(min_value=1, max_value=6, label= 'Days off')
    preference_order_preferred_start_time = forms.IntegerField(min_value=1, max_value=6, label= 'Start time')
    preference_order_preferred_end_time = forms.IntegerField(min_value=1, max_value=6, label= 'End time')
    preference_order_busyness_level = forms.IntegerField(min_value=1, max_value=6, label= 'Schedule Tightness')