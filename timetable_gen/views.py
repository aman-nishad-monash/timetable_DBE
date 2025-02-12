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
                preferred_start_time = datetime.datetime.strptime(
                    form.cleaned_data['preferred_start_time'], "%I:%M%p"
                )
                preferred_end_time = datetime.datetime.strptime(
                    form.cleaned_data['preferred_end_time'], "%I:%M%p"
                )
            except ValueError:
                preferred_start_time = None
                preferred_end_time = None

            # Process unit rankings from the dynamic fields.
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
                "Days Off": [day.strip().lower() for day in form.cleaned_data['days_off'].split(',')],
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
            saved_data = form.cleaned_data.copy()
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
    timetable_classes = (
        [UniClass.from_dict(data) for data in timetable_classes_serialized]
        if timetable_classes_serialized else None
    )
    return render(request, 'timetable_gen/timetableView.html', {
        'timetable_classes': timetable_classes,
    })

def reset_view(request):
    request.session.flush()
    return redirect('home')
