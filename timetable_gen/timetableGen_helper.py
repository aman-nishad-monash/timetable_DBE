import datetime, csv, re, io

class UniClass:
    def __init__(self, unit_name, class_type, day, start_time, duration, lecturer, unit_code, end_time):
        self.unit_name = unit_name
        self.class_type = class_type
        self.day = day
        self.day_off_feature_score = 1
        self.start_time = start_time
        self.start_time_feature_score = 1
        self.duration = duration
        self.lecturer = lecturer
        self.lecturer_feature_score = 1
        self.unit_code = unit_code
        self.score = 0
        self.ideality_status = None  # For status classification
        self.end_time = end_time
        self.end_time_feature_score = 1
        self.lecture_ideality = None  # For tracking preferred lecturers
        self.shortlisting_failed = None
        self.criticality_passed = True
        self.feature_scores = {}  
    
    def __repr__(self):
        return f'''{self.unit_code}: [{self.day} : {self.start_time} - {self.end_time}] , {self.lecturer}'''

    def load_read_csv(uploaded_file):
        """
        Process the uploaded CSV file (an in-memory file-like object)
        and return a list of UniClass instances.
        """

        def convert_duration_to_hours(duration_str):
            try:
                duration_time = datetime.datetime.strptime(duration_str, "%H:%M")
                return datetime.timedelta(hours=duration_time.hour, minutes=duration_time.minute)
            except ValueError:
                raise ValueError(f"Invalid duration format: {duration_str}")
        
        # Wrap the uploaded file with a text wrapper to decode it.
        text_file = io.TextIOWrapper(uploaded_file, encoding='utf-8-sig')
        timetable = csv.DictReader(text_file)
        classes = []
        global class_combos_available
        # Generate sorted list of unique unit-class type combinations
        class_combos = list({(cls.unit_code, cls.class_type) for cls in classes})
        class_combos_available = sorted(class_combos, key=lambda x: (x[0], x[1]))
        for row in timetable:
            match = re.search(r'\b(applied|workshop|seminar|laboratory|tutorial)\b', row['Class'], re.IGNORECASE)
            match1 = re.search(r"([A-Za-z]+\d+)", row['Class'])
            if match and match1:
                class_type = match.group().lower()
                unit_name = row['Unit Name']
                lecturer = row['Staff']
                start_time = datetime.datetime.strptime(row['Start Time'], "%I:%M%p")
                day = row['Day']
                duration = convert_duration_to_hours(row['Duration'])
                unit_code = match1.group()
                end_time = start_time + duration
                classes.append(UniClass(unit_name, class_type, day, start_time, duration, lecturer, unit_code, end_time))
        return classes

    def retreive_units_lecturers(classes):
        global available_lecturers
        unique_lecturers = {(cls.lecturer, cls.unit_code, cls.class_type[0].upper()+cls.class_type[1:]) for cls in classes}
        available_lecturers = sorted(unique_lecturers, key=lambda x: (x[1], x[2], x[0]))

        units = {(cls.unit_name, cls.unit_code) for cls in classes}
        units = sorted(units, key=lambda x: (x[1], x[0]))

        return available_lecturers, units

    def finalizing_ideal_lecturers(selected_lecturers):
        covered_combos = set()
        for lec_info in selected_lecturers:
            combo = (lec_info[1], lec_info[2])  # (unit_code, class_type)
            covered_combos.add(combo)
        # Check each combo in class_combos_available and add missing ones
        for combo in class_combos_available:
            if combo not in covered_combos:
                # Find all available lecturers for this combo
                lecturers_to_add = []
                for lec_info in available_lecturers:
                    if (lec_info[1], lec_info[2]) == combo:
                        lecturers_to_add.append(lec_info)
                selected_lecturers.extend(lecturers_to_add)
                # Notify user
                lecturer_names = [lec[0] for lec in lecturers_to_add]
                print(f"Note: No lecturers selected for {combo[0]} {combo[1]}. Automatically adding: {', '.join(lecturer_names)}.")
        # Deduplicate the lecturer names while preserving order
        seen_lecturers = set()
        ideal_lecturers = []
        for lec_info in selected_lecturers:
            lecturer = lec_info[0]
            if lecturer not in seen_lecturers:
                seen_lecturers.add(lecturer)
                ideal_lecturers.append(lecturer)
        
        return ideal_lecturers


#Scoring of classes according to preferences of user
## Subsidiary
def score_allocation(preference_order, critical_features):
    max_rank = max(preference_order.values())
    base_multiplier = 200
    
    scores_allocated = {
        feature: ((preference_order[feature]/max_rank) * base_multiplier) 
        for feature in preference_order.keys()
    }
    
    # Increase multiplier for critical features
    scores_allocated = {
        feature: score * 5.0 if critical_features[feature] else score 
        for feature, score in scores_allocated.items()
    }
    return scores_allocated
def update_class_status(cls):
    if cls.score >= 600:
        cls.ideality_status = "Highly Desirable"
    elif cls.score >= 500:
        cls.ideality_status = "Good"
    elif cls.score >= 400:
        cls.ideality_status = "Acceptable"
    elif cls.score >= 300:
        cls.ideality_status = "Marginal"
    else:
        cls.ideality_status = "Undesirable"
def score_calculation(cls, class_feature_score, feature_rank, critical_features, feature, passed):
    feature_score = getattr(cls, class_feature_score)  # Get the current feature score
    if passed:
        feature_score *= feature_rank[feature]
        if critical_features[feature]:
            cls.criticality_passed = True
            feature_score *= 10
    else:
        if critical_features[feature]:
            cls.criticality_passed = False
        feature_score -= 1
    setattr(cls, class_feature_score, feature_score)
## Main
def class_scoring(classes, all_preferences):
    scores = score_allocation(all_preferences["Preference Order"], all_preferences["Critical Features"])
    
    for cls in classes:
        cls.feature_scores = {feature: 0 for feature in scores.keys()}  # Initialize
        
        # Reset base score
        cls.score = 0
        
        # Set lecture ideality based on preferred lecturers
        cls.lecture_ideality = cls.lecturer in all_preferences["Ideal Lecturers"]
        
        # Score each feature
        for feature, feature_weight in scores.items():
            contribution = 0
            penalty = 0
            
            if feature == "Ideal Lecturers":
                if cls.lecture_ideality:
                    contribution = feature_weight
                else:
                    penalty = 3000 if all_preferences["Critical Features"][feature] else 100
                    
            elif feature == "Unit Importance":
                contribution = feature_weight + (all_preferences["Unit Ranks"][cls.unit_name] * 1.5)
                
            elif feature == "Days Off":
                if cls.day not in all_preferences["Days Off"]:
                    contribution = feature_weight
                else:
                    penalty = 3000 if all_preferences["Critical Features"][feature] else 100
                    
            elif feature == "Preferred Start Time":
                if cls.start_time >= all_preferences["Preferred Start Time"]:
                    contribution = feature_weight
                else:
                    penalty = 3000 if all_preferences["Critical Features"][feature] else 100
                    
            elif feature == "Preferred End Time":
                if cls.end_time <= all_preferences["Preferred End Time"]:
                    contribution = feature_weight
                else:
                    penalty = 3000 if all_preferences["Critical Features"][feature] else 100

            # Apply calculated values
            cls.feature_scores[feature] = contribution - penalty
            cls.score += contribution - penalty
        
        update_class_status(cls)
    
    classes.sort(key=lambda x: x.score, reverse=True)


#Organizing classes for shortlisting
def class_organizing(classes):

    organized_classes = {}
    for unit_code, class_type in class_combos_available:
        if unit_code not in organized_classes:
            organized_classes[unit_code] = {}
        organized_classes[unit_code][class_type] = [
            cls for cls in classes 
            if cls.unit_code == unit_code and cls.class_type == class_type
        ]
    
    for cls in classes:
        if cls.criticality_passed:
            organized_classes[cls.unit_code][cls.class_type].append(cls)
    
    for unit_code, class_types in organized_classes.items():
        for class_type, clss in class_types.items():
            if not clss:
                print("Change preferences: Current choices conflict with timetable")
                exit()
    
    return organized_classes


#Shortlisting classes for generation of timetable
def has_conflict(cls1, cls2):
    if cls1.day != cls2.day:
        return False
    return (cls1.start_time < cls2.end_time) and (cls2.start_time < cls1.end_time)
def shortlister(classes, organized_classes, all_preferences):
    selected_classes = []
    unit_ranks = all_preferences["Unit Ranks"]
    busy_sched = all_preferences["Busyness Schedule"]
    
    # Penalty/bonus values for spread/cluster preferences
    SPREAD_PENALTY = 25  # Per existing class on day
    CLUSTER_BONUS = 30   # Per existing class on day
    
    # Create a list of units sorted by their rank (descending order)
    units = list(organized_classes.keys())
    unit_code_to_name = {cls.unit_code: cls.unit_name for cls in classes}
    
    # Sort units by their rank in Unit Ranks (higher rank first)
    sorted_units = sorted(units, key=lambda uc: unit_ranks.get(unit_code_to_name[uc], 0), reverse=True)
    
    for unit_code in sorted_units:
        class_types = organized_classes[unit_code]
        # Process class types in alphabetical order
        for class_type in sorted(class_types.keys()):
            classes_for_type = class_types[class_type]
            
            # Split classes into critical-compliant and others
            critical_compliant = [cls for cls in classes_for_type if cls.criticality_passed]
            fallback_candidates = [cls for cls in classes_for_type if not cls.criticality_passed]
            
            # Select candidate source (priority to critical-compliant)
            candidate_source = critical_compliant if critical_compliant else fallback_candidates
            
            # Find non-conflicting candidates and calculate adjusted scores
            candidates = []
            for cls in candidate_source:
                conflict = any(has_conflict(cls, selected_cls) for selected_cls in selected_classes)
                if not conflict:
                    # Calculate busyness adjustment
                    day_count = sum(c.day == cls.day for c in selected_classes)
                    adjusted_score = cls.score
                    
                    if busy_sched:  # Cluster preference
                        adjusted_score += day_count * CLUSTER_BONUS
                    else:           # Spread preference
                        adjusted_score -= day_count * SPREAD_PENALTY
                    
                    candidates.append((cls, adjusted_score))
            
            # If no candidates, use highest-scored (even with conflict)
            if not candidates:
                print(f"Warning: No conflict-free option for {unit_code} {class_type}. Selecting highest-scored.")
                best_candidate = max(candidate_source, key=lambda x: x.score)
                selected_classes.append(best_candidate)
                continue
            
            # Sort candidates by adjusted score
            candidates.sort(key=lambda x: x[1], reverse=True)
            
            # Select top candidate
            selected_cls = candidates[0][0]
            selected_classes.append(selected_cls)
    
    return selected_classes


#Printing Timetable using tabulate module
def display_timetable(selected_classes):
    from tabulate import tabulate

    # Define the order of days for sorting
    days_order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    # Sort classes by day and start time
    sorted_classes = sorted(
        selected_classes,
        key=lambda cls: (days_order.index(cls.day), cls.start_time)
    )
    
    # Prepare table data
    table_data = []
    for cls in sorted_classes:
        # Format day with capital letter
        day = cls.day.capitalize()
        
        # Format start and end times (strip leading zeros from hours)
        start_time = cls.start_time.strftime("%I:%M%p").lstrip('0').replace(' 0', ' ')
        end_time = cls.end_time.strftime("%I:%M%p").lstrip('0').replace(' 0', ' ')
        
        # Calculate duration string (e.g., "1h30m")
        total_seconds = cls.duration.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        duration_str = f"{hours}h{minutes:02d}m"
        
        # Append row data
        table_data.append([
            day,
            start_time,
            end_time,
            cls.unit_code,
            cls.class_type.capitalize(),
            cls.lecturer,
            duration_str
        ])
    
    # Define headers
    headers = ["Day", "Start", "End", "Unit Code", "Type", "Lecturer", "Duration"]

    score_timtable = 0
    for cls in selected_classes:
        score_timtable += cls.score
    
    # Calculate total score and feature contributions
    total_score = sum(cls.score for cls in selected_classes)
    feature_contributions = {
        feature: sum(cls.feature_scores.get(feature, 0) for cls in selected_classes)
        for feature in selected_classes[0].feature_scores.keys()
    }
    
    print(f"\nTotal Timetable Score: {total_score}")
    
    # Diagnostic message
    if total_score < 9500:
        print("\nDiagnostic Report: Score below 9500")
        print("Consider adjusting these aspects:")
        
        # Identify underperforming features
        avg_contribution = total_score / len(feature_contributions)
        for feature, score in sorted(feature_contributions.items(), key=lambda x: x[1]):
            if score < avg_contribution * 0.6:  # Features contributing <60% of average
                print(f"- {feature}: Current contribution {score:.1f}")
                if feature == "Ideal Lecturers":
                    print("  → Expand preferred lecturer selections")
                elif feature == "Unit Importance":
                    print("  → Re-evaluate unit priority rankings")
                elif "Time" in feature:
                    print(f"  → Consider widening preferred time window")
                elif feature == "Days Off":
                    print("  → Reduce number of requested days off")
                elif feature == "Busyness Level":
                    print("  → Try different clustering/spreading preference")


    # Print the formatted table
    print(f"\nYour Ideal Timetable: Score ({score_timtable})")
    print(tabulate(table_data, headers=headers, tablefmt="grid", stralign="center"))


#Fascilitator function
def timetable_generator(all_classes,prefs):

    classes = all_classes
    all_preferences = prefs
    #Classes are scored through the filter and organized in descending order of scores with the following function
    class_scoring(classes, all_preferences)
    
    #Classes organized unit and type wise
    organized_classes = class_organizing(classes)
    #{'FIT1055': {'workshop': [Classes organized by descending order of score], 'applied': []}, 'MAT1841': {'applied': [], 'workshop': []}, 'FIT1008': {'applied': [], 'workshop': []}, 'FIT1043': {'applied': [], 'workshop': []}}
    
    #Classes are shortlisted as neccesary according to preferences
    shortlisted_classes = shortlister(classes, organized_classes, all_preferences)

    #Printing timetable generated
    display_timetable(shortlisted_classes)
