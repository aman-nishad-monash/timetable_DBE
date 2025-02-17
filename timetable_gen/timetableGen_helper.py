import datetime, csv, re, io, time
from scipy.optimize import linear_sum_assignment
import numpy as np

class UniClass:
    def __init__(self, unit_name, class_type, day, start_time, duration, lecturer, unit_code, end_time, location):
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
        self.location = location
    
    def __repr__(self):
        return f'''{self.unit_code}: \n\t[{self.day} : {self.start_time} - {self.end_time}] , {self.lecturer}\n\t Criticality status: {self.criticality_passed}\n'''

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
                location = row['Location']
                end_time = start_time + duration
                classes.append(UniClass(unit_name, class_type, day, start_time, duration, lecturer, unit_code, end_time, location))
        return classes

    def retreive_units_lecturers(classes):
        unique_lecturers = {(cls.lecturer, cls.unit_code, cls.class_type[0].upper()+cls.class_type[1:]) for cls in classes}
        available_lecturers = sorted(unique_lecturers, key=lambda x: (x[1], x[2], x[0]))

        units = {(cls.unit_name, cls.unit_code) for cls in classes}
        units = sorted(units, key=lambda x: (x[1], x[0]))

        return available_lecturers, units

    def finalizing_ideal_lecturers(selected_lecturers_pre, classes, available_lecturers):
        class_combos = list(set((cls.unit_code, cls.class_type) for cls in classes))
        class_combos_available = sorted(class_combos, key=lambda x: (x[0], x[1]))
        covered_combos = set()
        print(f"Class combos: {class_combos_available}")
        selected_lecturers = []
        for selected_index in selected_lecturers_pre:
            selected_lecturers.append(available_lecturers[int(selected_index)])
        for lec_info in selected_lecturers:
            combo = (lec_info[1], lec_info[2].lower())  # (unit_code, class_type)
            covered_combos.add(combo)
        
        print("Covered combos: ", covered_combos)
        # Check each combo in class_combos_available and add missing ones
        for combo in class_combos_available:
            if combo not in covered_combos:
                # Find all available lecturers for this combo
                lecturers_to_add = []
                for lec_info in available_lecturers:
                    if (lec_info[1], lec_info[2].lower()) == combo:
                        lecturers_to_add.append(lec_info)
                        selected_lecturers.append(lec_info)
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

        print("Ideal Lecturers: ", ideal_lecturers)
        return ideal_lecturers

    def to_dict(self):
        """
        Returns a dictionary representation of this UniClass instance,
        converting non-serializable objects to serializable formats.
        """
        return {
            "unit_name": self.unit_name,
            "class_type": self.class_type,
            "day": self.day,
            "day_off_feature_score": self.day_off_feature_score,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "start_time_feature_score": self.start_time_feature_score,
            # You can convert the duration to total seconds or use str(self.duration)
            "duration": self.duration.total_seconds() if self.duration else None,
            "lecturer": self.lecturer,
            "lecturer_feature_score": self.lecturer_feature_score,
            "unit_code": self.unit_code,
            "score": self.score,
            "ideality_status": self.ideality_status,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "end_time_feature_score": self.end_time_feature_score,
            "lecture_ideality": self.lecture_ideality,
            "shortlisting_failed": self.shortlisting_failed,
            "criticality_passed": self.criticality_passed,
            "feature_scores": self.feature_scores,
            "location": self.location
        }

    @classmethod
    def from_dict(cls, data):
        """
        Returns a new UniClass instance from a dictionary (typically one
        generated by the to_dict() method). Converts string representations
        back into datetime and timedelta objects.
        """
        # Convert ISO-formatted strings back to datetime objects (if present)
        start_time = datetime.datetime.fromisoformat(data['start_time']) if data.get('start_time') else None
        end_time = datetime.datetime.fromisoformat(data['end_time']) if data.get('end_time') else None
        
        # Convert duration from total seconds back to a timedelta (if present)
        duration = datetime.timedelta(seconds=data['duration']) if data.get('duration') is not None else None
        
        # Create a new instance. Note that start_time, duration, and end_time are now converted.
        instance = cls(
            unit_name=data['unit_name'],
            class_type=data['class_type'],
            day=data['day'],
            start_time=start_time,
            duration=duration,
            lecturer=data['lecturer'],
            unit_code=data['unit_code'],
            end_time=end_time,
            location=data.get('location')
        )
        # Set any additional attributes
        instance.day_off_feature_score = data.get('day_off_feature_score', 1)
        instance.start_time_feature_score = data.get('start_time_feature_score', 1)
        instance.lecturer_feature_score = data.get('lecturer_feature_score', 1)
        instance.score = data.get('score', 0)
        instance.ideality_status = data.get('ideality_status')
        instance.end_time_feature_score = data.get('end_time_feature_score', 1)
        instance.lecture_ideality = data.get('lecture_ideality')
        instance.shortlisting_failed = data.get('shortlisting_failed')
        instance.criticality_passed = data.get('criticality_passed', True)
        instance.feature_scores = data.get('feature_scores', {})
        return instance

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
## Main
def class_scoring(classes, all_preferences):
    scores = score_allocation(all_preferences["Preference Order"], all_preferences["Critical Features"])
    print(scores    )
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
                    if all_preferences["Critical Features"][feature]:
                        penalty = 3000
                        if cls.criticality_passed:
                            cls.criticality_passed = False
                    else:
                        penalty = 100
                    
            elif feature == "Unit Importance":
                contribution = feature_weight + (all_preferences["Unit Ranks"][cls.unit_name] * 10)
                
            elif feature == "Days Off":
                if cls.day.lower() not in all_preferences["Days Off"]:
                    print("%"*70,f'Class day: {cls.day}, Days off: {all_preferences["Days Off"]}',"%"*70)
                    contribution = feature_weight
                else:
                    if all_preferences["Critical Features"][feature]:
                        penalty = 3000
                        if cls.criticality_passed:
                            cls.criticality_passed = False
                    else:
                        penalty = 100
                    
            elif feature == "Preferred Start Time":
                if cls.start_time >= all_preferences["Preferred Start Time"]:
                    contribution = feature_weight
                else:
                    if all_preferences["Critical Features"][feature]:
                        penalty = 3000
                        if cls.criticality_passed:
                            cls.criticality_passed = False
                    else:
                        penalty = 100
                    
            elif feature == "Preferred End Time":
                if cls.end_time <= all_preferences["Preferred End Time"]:
                    contribution = feature_weight
                else:
                    if all_preferences["Critical Features"][feature]:
                        penalty = 3000
                        if cls.criticality_passed:
                            cls.criticality_passed = False
                    else:
                        penalty = 100

            # Apply calculated values
            cls.feature_scores[feature] = contribution - penalty
            cls.score += contribution - penalty
        
        update_class_status(cls)
    
    classes.sort(key=lambda x: x.score, reverse=True)

#Organizing classes for shortlisting
def class_organizing(classes):
    class_combos = list({(cls.unit_code, cls.class_type) for cls in classes})
    class_combos_available = sorted(class_combos, key=lambda x: (x[0], x[1]))
    organized_classes = {}
    for unit_code, class_type in class_combos_available:
        if unit_code not in organized_classes:
            organized_classes[unit_code] = {}
        organized_classes[unit_code][class_type] = [
            cls for cls in classes 
            if cls.unit_code == unit_code and cls.class_type == class_type
        ]
    
    for cls in classes:
        organized_classes[cls.unit_code][cls.class_type].append(cls)
    
    for unit_code, class_types in organized_classes.items():
        for class_type, clss in class_types.items():
            if not clss:
                print("Change preferences: Current choices conflict with timetable")
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
    
    sorted_units = sorted(units, key=lambda uc: unit_ranks.get(unit_code_to_name[uc], 0), reverse=True)
    
    for unit_code in sorted_units:
        class_types = organized_classes[unit_code]
        # Process class types in alphabetical order
        for class_type in sorted(class_types.keys()):
            classes_for_type = class_types[class_type]
            
            # Split into critical-compliant and fallback candidates
            critical_compliant = [cls for cls in classes_for_type if cls.criticality_passed]
            fallback_candidates = [cls for cls in classes_for_type if not cls.criticality_passed]
            
            # Candidate source: use critical ones if available
            candidate_source = critical_compliant if critical_compliant else fallback_candidates
            
            # For each candidate in the group, compute the cost:
            #   - If the candidate conflicts with any already selected class, assign a high cost.
            #   - Otherwise, adjust its score by busyness (using a bonus or penalty for each class already
            #     on the same day) and set cost = - (adjusted score) so that maximizing score is equivalent to minimizing cost.
            costs = []
            for cls in candidate_source:
                conflict = any(has_conflict(cls, sel_cls) for sel_cls in selected_classes)
                # Count how many classes on the same day are already scheduled
                day_count = sum(1 for sel in selected_classes if sel.day == cls.day)
                adjusted_score = cls.score + (day_count * CLUSTER_BONUS if busy_sched else - day_count * SPREAD_PENALTY)
                if conflict:
                    cost = 99999  # A very high cost to (ideally) avoid conflict
                else:
                    cost = -adjusted_score
                costs.append(cost)
                print(f"  [DEBUG] {unit_code} {class_type} candidate {cls.unit_code}: "
                      f"base score={cls.score}, day_count={day_count}, "
                      f"adjusted_score={adjusted_score}, cost={cost}, conflict={conflict}")
            
            # If every candidate is in conflict, warn and pick the highest-scored candidate (ignoring conflict)
            if all(c == 99999 for c in costs):
                print(f"Warning: No conflict-free option for {unit_code} {class_type}. "
                      f"Selecting highest-scored candidate from fallback list.")
                best_candidate = max(candidate_source, key=lambda x: x.score)
                selected_classes.append(best_candidate)
                print(f"  [DEBUG] Fallback selected for {unit_code} {class_type}: {best_candidate.unit_code} (Score: {best_candidate.score})")
            else:
                # Build a cost matrix (a 1 x n array) and run the Hungarian algorithm.
                cost_matrix = np.array([costs])
                row_ind, col_ind = linear_sum_assignment(cost_matrix)
                selected_idx = col_ind[0]  # only one row in this cost matrix
                selected_cls = candidate_source[selected_idx]
                selected_classes.append(selected_cls)
                print(f"  [DEBUG] Hungarian selected for {unit_code} {class_type}: {selected_cls.unit_code} "
                      f"with cost {costs[selected_idx]}")
    
    print("\n[DEBUG] Final Selected Classes:")
    for cls in selected_classes:
        print(f"  🎯 {cls.unit_code}: {cls.class_type} on {cls.day} "
              f"({cls.start_time.strftime('%I:%M %p')} - {cls.end_time.strftime('%I:%M %p')}) | Score: {cls.score}")
    
    return selected_classes


#Printing Timetable using tabulate module
def display_timetable(selected_classes):
    from tabulate import tabulate

    # Define the order of days for sorting
    days_order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    # Sort classes by day and start time
    sorted_classes = sorted(
        selected_classes,
        key=lambda cls: (days_order.index(cls.day.lower()), cls.start_time)
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
        print("\nDiagnostic Report: Timetable Score below average")
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
                    print(f"  → Change day(s) off")
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

    return shortlisted_classes
