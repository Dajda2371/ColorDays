import sys
sys.path.append('backend')
from data_manager import students_data_store, load_students_data_from_db
from api.get.students.students import get_students
import json

class FakeRequest:
    @property
    def cookies(self):
        return {}

load_students_data_from_db()

res = get_students(FakeRequest(), ('Admin', 'Administrator'))
print(json.dumps(res, indent=2))
