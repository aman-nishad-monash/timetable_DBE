from django.shortcuts import render
from datetime import datetime
# Create your views here.
from django.shortcuts import render, redirect
from .timetableGen_helper import *
from .forms import *


def home(request):
    classes = None
    preferences = None
    available_lecturers = None
    units = None
    form = PreferencesForm() 


    if request.method == "POST" and request.FILES.get("file"):
        # Process file upload if provided.
        csv_file = request.FILES["file"]
        classes = UniClass.load_read_csv(csv_file)
        available_lecturers, units = list(UniClass.retreive_units_lecturers(classes))
        request.session['classes'] = [cls.to_dict() for cls in classes]      # Note: Ensure classes is serializable or store what you need
        request.session['available_lecturers'] = available_lecturers
        request.session['units'] = units
        # Redirect to the same page so that the preferences form will have the CSV data available  # CHANGED: Line 21
        return redirect('home')  # Assumes your URL pattern is named 'home'   

    if request.method == "POST" and request.POST.get("action") == "save_preferences":
        classes_serialized = request.session.get('classes')
        available_lecturers = request.session.get('available_lecturers')
        units = request.session.get('units')
        
        if classes_serialized:
          classes = [UniClass.from_dict(data) for data in classes_serialized]
        else:
            classes = None 
        
        if not units:
            return render(request, 'timetable_gen/base.html', {
                'error': "Please upload a CSV file before setting preferences.",
                'form': form,
            })
        
        form = PreferencesForm(request.POST)
        if form.is_valid():
            # Process times
            try:
                preferred_start_time = datetime.datetime.strptime(
                    form.cleaned_data['preferred_start_time'], "%I:%M%p"
                )
                preferred_end_time = datetime.datetime.strptime(
                    form.cleaned_data['preferred_end_time'], "%I:%M%p"
                )
            except ValueError:
                # Handle time format error
                pass

            # Process unit ranks
            unit_ranks = {}
            for unit_name, unit_code in units:
                rank = request.POST.get(f'unit_rank_{unit_code}')
                if rank:
                    unit_ranks[unit_name] = int(rank)
            unit_ranks = dict(sorted(unit_ranks.items(), 
                                key=lambda item: item[1], reverse=True))

            # Build preferences dictionary
            all_preferences = {
                "Ideal Lecturers": UniClass.finalizing_ideal_lecturers((request.POST.getlist('lecturers')), classes, available_lecturers),
                "Unit Ranks": unit_ranks,
                "Days Off": [day.strip().lower() 
                        for day in form.cleaned_data['days_off'].split(',')],
                "Preferred Start Time": preferred_start_time,
                "Preferred End Time": preferred_end_time,
                "Busyness Schedule": form.cleaned_data['busy_sched'],
                 "Critical Features": {
            "Ideal Lecturers": form.cleaned_data['critical_ideal_lecturers'],
            "Unit Importance": form.cleaned_data['critical_unit_importance'],
            "Days Off": form.cleaned_data['critical_days_off'],
            "Preferred Start Time": form.cleaned_data['critical_preferred_start_time'],
            "Preferred End Time": form.cleaned_data['critical_preferred_end_time'],
            "Busyness Level": form.cleaned_data['critical_busyness_level']
        },
                "Preference Order": {
         "Ideal Lecturers": form.cleaned_data['preference_order_ideal_lecturers'],
         "Unit Importance": form.cleaned_data['preference_order_unit_importance'],
         "Days Off": form.cleaned_data['preference_order_days_off'],
         "Preferred Start Time": form.cleaned_data['preference_order_preferred_start_time'],
         "Preferred End Time": form.cleaned_data['preference_order_preferred_end_time'],
         "Busyness Level": form.cleaned_data['preference_order_busyness_level']
    }
}
            # Generate timetable
            timetable_classes = timetable_generator(classes, all_preferences)
    else:
        print("Form errors:", form.errors)

            
    return render(request, 'timetable_gen/base.html', {
            'classes': request.session.get('classes'),                    
            'available_lecturers': request.session.get('available_lecturers'),  
            'units': request.session.get('units'),                        
            'form': form,                                                 
     })
