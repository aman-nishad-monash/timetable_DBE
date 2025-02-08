from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from .timetableGen_helper import *
from .forms import *


def home(request):
    classes = None
    preferences = None
    available_lecturers = None
    units = None


    if request.method == "POST":
        # Process file upload if provided.
        if request.FILES.get("file"):
            csv_file = request.FILES["file"]
            classes = UniClass.load_read_csv(csv_file)
            available_lecturers, units = list(UniClass.retreive_units_lecturers(classes))

            all_features = [
                "Ideal Lecturers", 
                "Unit Importance", 
                "Days Off", 
                "Preferred Start Time", 
                "Preferred End Time", 
                "Busyness Level"
                ]

        elif request.POST.get("action") == "save_preferences":
            # Get selected lecturers from form
            selected_lecturers = [tuple(lecturer.split(',')) for lecturer in request.POST.getlist("lecturers")]
            ideal_lecturers = UniClass.finalizing_ideal_lecturers(selected_lecturers)

            # Get preferences of start and end time
            preferred_start_time = datetime.strptime(request.POST.get(), "%H:%M").time() 
            preferred_end_time = datetime.strptime(request.POST.get(), "%H:%M").time() 

            # Get preferences for busyness
            busy_sched = request.POST.get()
            busy_sched = busy_sched == 'y'

            # Get unit rankings
            unit_ranks = request.POST.get()

            # Get preference for days off
            days_off = request.POST.get()
            critical_features = {feature: None for feature in all_features}
            preference_order = {feature: None for feature in all_features}
            critical_features = request.POST.get()
            preference_order = request.POST.get()
            
            all_preferences = {
                "Ideal Lecturers": ideal_lecturers, 
                "Unit Ranks": unit_ranks, 
                "Days Off": days_off, 
                "Preferred Start Time": preferred_start_time, 
                "Preferred End Time": preferred_end_time, 
                "Busyness Schedule": busy_sched, 
                "Critical Features": critical_features, 
                "Preference Order": preference_order
                }
    
            timetable_generator(classes, all_preferences)



            
    return render(request, 'timetable_gen/base.html', {
        'classes': classes,
        'available_lecturers': available_lecturers,
        'units': units
    })
