# forms.py
from django import forms

class CsvUploadForm(forms.Form):
    file = forms.FileField(
        label='CSV File',
        help_text='📁 Drop CSV file here or click to upload',
        widget=forms.ClearableFileInput(attrs={'accept': '.csv'})
    )

class LecturerSelectionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        available_lecturers = kwargs.pop('available_lecturers', [])
        super().__init__(*args, **kwargs)
        
        # Create choices in format: (value, display)
        choices = [
            (f"{lec[0]}||{lec[1]}||{lec[2]}", 
             f"{lec[0]} (Unit: {lec[1]}, Type: {lec[2]})")
            for lec in available_lecturers
        ]
        
        self.fields['lecturers'] = forms.MultipleChoiceField(
            choices=choices,
            widget=forms.CheckboxSelectMultiple,
            required=False,
            label="Select Preferred Lecturers"
        )