# views.py
from django.shortcuts import render, redirect
from datetime import datetime
from .timetableGen_helper import *
from .forms import PreferencesForm

def home(request):
    classes = None
    # Retrieve any saved preferences from the session.
    saved_preferences = request.session.get("user_preferences", {})
    # Get dynamic options (if already uploaded) from the session:
    session_available_lecturers = request.session.get('available_lecturers')
    session_units = request.session.get('units')
    
    # Pass these into the form’s constructor:
    form = PreferencesForm(initial=saved_preferences,
                           available_lecturers=session_available_lecturers,
                           units=session_units)
    
    # Handle CSV file upload
    if request.method == "POST" and request.FILES.get("file"):
        request.session.flush()
        csv_file = request.FILES["file"]
        classes = UniClass.load_read_csv(csv_file)
        available_lecturers, units = list(UniClass.retreive_units_lecturers(classes))
        # Save to session
        request.session['classes'] = [cls.to_dict() for cls in classes]
        request.session['available_lecturers'] = available_lecturers
        request.session['units'] = units  # e.g., list of (unit_name, unit_code)
        request.session.set_expiry(300)  # 5-minute expiry
        return redirect('home')

    # Handle preferences form submission
    if request.method == "POST" and request.POST.get("action") == "save_preferences":
        classes_serialized = request.session.get('classes')
        available_lecturers = request.session.get('available_lecturers')
        units = request.session.get('units')

        if classes_serialized:
            classes = [UniClass.from_dict(data) for data in classes_serialized]
        else:
            classes = None

        if not units:
            return render(request, 'timetable_gen/home.html', {
                'error': "Please upload a CSV file before setting preferences.",
                'form': form,
            })

        # Note: Pass in the dynamic options again when binding POST data.
        form = PreferencesForm(request.POST,
                               available_lecturers=available_lecturers,
                               units=units)
        if form.is_valid():
            try:
                preferred_start_time = datetime.datetime.combine(datetime.date(1900, 1, 1), form.cleaned_data['preferred_start_time'])
                preferred_end_time = datetime.datetime.combine(datetime.date(1900, 1, 1), form.cleaned_data['preferred_end_time'])
            except ValueError:
                preferred_start_time = None
                preferred_end_time = None

            # Process unit rankings...
            unit_ranks = {}
            for unit_name, unit_code in units:
                key = f'unit_rank_{unit_code}'
                rank = form.cleaned_data.get(key)
                if rank:
                    unit_ranks[unit_name] = int(rank)
            unit_ranks = dict(sorted(unit_ranks.items(), key=lambda item: item[1], reverse=True))
            all_preferences = {
                "Ideal Lecturers": UniClass.finalizing_ideal_lecturers(
                    form.cleaned_data.get('lecturers', []), classes, available_lecturers
                ),
                "Unit Ranks": unit_ranks,
                "Days Off": form.cleaned_data.get('days_off'),
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
            
            # Convert the time objects in cleaned_data to strings before saving in session
            saved_data = form.cleaned_data.copy()
            if saved_data.get('preferred_start_time'):
                # Format as "HH:MM"
                saved_data['preferred_start_time'] = saved_data['preferred_start_time'].strftime("%H:%M")
            if saved_data.get('preferred_end_time'):
                saved_data['preferred_end_time'] = saved_data['preferred_end_time'].strftime("%H:%M")
            
            request.session["user_preferences"] = saved_data
            request.session.set_expiry(300)
            
            # Generate timetable based on classes and preferences
            timetable_classes = timetable_generator(classes, all_preferences)
            request.session['timetable_classes'] = [cls.to_dict() for cls in timetable_classes]
            return redirect('timetable_view')

        else:
            print("Form errors:", form.errors)

    # Render the home page
    context = {
        'classes': request.session.get('classes'),
        'form': form,
    }
    return render(request, 'timetable_gen/home.html', context)

def timetable_view(request):
    timetable_classes_serialized = request.session.get('timetable_classes')
    daysOfWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    timetable = {day: [] for day in daysOfWeek}
    if timetable_classes_serialized:
        timetable_classes = (
            [UniClass.from_dict(data) for data in timetable_classes_serialized]
            if timetable_classes_serialized else None
        )
        for cls in timetable_classes:
            timetable[cls.day].append(cls)
        
        # 2. Sort the classes in each day's list by the original datetime start_time
        for day in timetable:
            timetable[day].sort(key=lambda cls: cls.start_time)
        
        # 3. Format class attributes after sorting
        for day in timetable:
            for cls in timetable[day]:
                # Capitalize the class_type (assuming it is at least 1 char long)
                cls.class_type = cls.class_type[0].upper() + cls.class_type[1:]
                # Format start_time and end_time as desired
                cls.start_time = cls.start_time.strftime("%I:%M %p").lstrip("0").lower()
                cls.end_time = cls.end_time.strftime("%I:%M %p").lstrip("0").lower()

    return render(request, 'timetable_gen/timetableView.html', {
        'timetable_classes': timetable,
    })

def reset_view(request):
    request.session.flush()
    return redirect('home')
