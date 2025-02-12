from django.shortcuts import render, redirect
from datetime import datetime  # You can now use datetime.strptime directly
from .timetableGen_helper import *
from .forms import PreferencesForm

def home(request):
    classes = None
    available_lecturers = None
    units = None
    saved_preferences = request.session.get("user_preferences", {})
    form = PreferencesForm(initial=saved_preferences)
    # Handle CSV file upload
    if request.method == "POST" and request.FILES.get("file"):
        csv_file = request.FILES["file"]
        classes = UniClass.load_read_csv(csv_file)
        available_lecturers, units = list(UniClass.retreive_units_lecturers(classes))
        # Store serializable versions in the session
        request.session['classes'] = [cls.to_dict() for cls in classes]
        request.session['available_lecturers'] = available_lecturers
        request.session['units'] = units  # List of (unit_name, unit_code)
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
            # If no CSV data is available, show an error on the home page.
            return render(request, 'timetable_gen/home.html', {
                'error': "Please upload a CSV file before setting preferences.",
                'form': form,
            })

        form = PreferencesForm(request.POST)
        if form.is_valid():
            try:
                preferred_start_time = datetime.datetime.strptime(
                    form.cleaned_data['preferred_start_time'], "%I:%M%p"
                )
                preferred_end_time = datetime.datetime.strptime(
                    form.cleaned_data['preferred_end_time'], "%I:%M%p"
                )
            except ValueError:
                # You might want to return an error message here
                preferred_start_time = None
                preferred_end_time = None

            # Process unit rankings (assumes units is a list of tuples like (unit_name, unit_code))
            unit_ranks = {}
            for unit_name, unit_code in units:
                rank = request.POST.get(f'unit_rank_{unit_code}')
                if rank:
                    unit_ranks[unit_name] = int(rank)
            # Optional: sort unit_ranks if needed
            unit_ranks = dict(sorted(unit_ranks.items(), key=lambda item: item[1], reverse=True))

            all_preferences = {
                "Ideal Lecturers": UniClass.finalizing_ideal_lecturers(
                    request.POST.getlist('lecturers'), classes, available_lecturers
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
            saved_data['lecturers'] = request.POST.getlist('lecturers')
            request.session["user_preferences"] = saved_data
            request.session.set_expiry(300)
            
            # Generate timetable based on classes and preferences
            timetable_classes = timetable_generator(classes, all_preferences)
            request.session['timetable_classes'] = [cls.to_dict() for cls in timetable_classes]
            return redirect('timetable_view')
        else:
            print("Form errors:", form.errors)

    # Render the home page with data from session (if any)
    context = {
        'classes': request.session.get('classes'),
        'available_lecturers': request.session.get('available_lecturers'),
        'units': request.session.get('units'),
        'form': form,
    }
    return render(request, 'timetable_gen/home.html', context)

def timetable_view(request):
    timetable_classes_serialized = request.session.get('timetable_classes')
    timetable_classes = [UniClass.from_dict(data) for data in timetable_classes_serialized] if timetable_classes_serialized else None

    return render(request, 'timetable_gen/timetableView.html', {
        'timetable_classes': timetable_classes,
    })

def reset_view(request):
    request.session.flush()
    return redirect('home')