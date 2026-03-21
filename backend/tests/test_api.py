import sqlite3
import json

conn = sqlite3.connect("backend/data/2026.db")
c = conn.cursor()

c.execute("SELECT * FROM students")
students_data_store = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]

c.execute("SELECT * FROM classes")
class_data_store = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]

code = "GBvYS"
day = "1"

target_student_config = None
for s_config in students_data_store:
    if s_config.get('code') == code:
        target_student_config = s_config
        break

if not target_student_config:
    print("Not found")

student_main_class_name = target_student_config.get('class')
is_counted_by_field = f"iscountedby{day}"
response_payload = []

target_student_personal_counts_str = target_student_config.get('counts_classes', '[]')
student_personal_counts_set = set()
try:
    parsed = json.loads(target_student_personal_counts_str)
    if isinstance(parsed, list):
        student_personal_counts_set = {str(c) for c in parsed}
except Exception as e:
    print("Error parsing target", e)

for class_being_evaluated in class_data_store:
    if class_being_evaluated.get(is_counted_by_field) == student_main_class_name:
        class_to_display_name = class_being_evaluated['class']
        student_is_counting_this_class = class_to_display_name in student_personal_counts_set
        also_counted_by_notes = []
        for other_student_config in students_data_store:
            if other_student_config.get('code') == code:
                continue
            other_student_counts_classes_str = other_student_config.get('counts_classes', '[]')
            try:
                other_parsed = json.loads(other_student_counts_classes_str)
                if isinstance(other_parsed, list):
                    if class_to_display_name in {str(c) for c in other_parsed}:
                        also_counted_by_notes.append(other_student_config.get('note', 'Unknown Note'))
            except Exception as e:
                print("Error parsing other", e)

        response_payload.append({
            "class_name": class_to_display_name,
            "is_counted_by_current_student": student_is_counting_this_class,
            "also_counted_by_notes": sorted(list(set(also_counted_by_notes)))
        })

print(json.dumps(sorted(response_payload, key=lambda x: x['class_name']), indent=2))
