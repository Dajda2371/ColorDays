import sys
import json
sys.path.append('backend')
from data_manager import students_data_store, class_data_store, load_students_data_from_db, load_class_data_from_db
from api.get.students.student_counting_details import get_student_counting_details

class FakeRequest:
    @property
    def cookies(self):
        return {}

load_students_data_from_db()
load_class_data_from_db()

res = get_student_counting_details('GBvYS', '1', ('Admin', 'administrator'))
print(json.dumps(res, indent=2))
