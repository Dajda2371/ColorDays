import webbrowser
import os
import json
from http.server import SimpleHTTPRequestHandler, HTTPServer

DATA_PATH = './backend/data/tables.sql'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, '../frontend')
SQL_FILE = os.path.join(BASE_DIR, 'data', 'tables.sql')

os.makedirs(os.path.dirname(SQL_FILE), exist_ok=True)

def generate_sql(student_counts, teacher_counts):
    values = []
    for points, count in enumerate(student_counts):
        values.append(f"('student', {points}, {count})")
    for points, count in enumerate(teacher_counts):
        values.append(f"('teacher', {points}, {count})")
    return "INSERT INTO counts (type, points, count) VALUES\n" + ",\n".join(values) + ";\n"

def parse_sql():
    if not os.path.exists(SQL_FILE):
        return [0]*7, [0]*7

    student = [0]*7
    teacher = [0]*7

    with open(SQL_FILE, 'r') as f:
        lines = f.readlines()

    for line in lines:
        if line.strip().startswith("('"):
            parts = line.strip().strip(",").strip("();").split(",")
            typ = parts[0].strip(" '")
            points = int(parts[1])
            count = int(parts[2])
            if typ == "student":
                student[points] = count
            elif typ == "teacher":
                teacher[points] = count

    return student, teacher

class MyHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/save-sql':
            length = int(self.headers.get('Content-Length'))
            body = self.rfile.read(length)
            data = json.loads(body)

            with open(SQL_FILE, 'w') as f:
                f.write("INSERT INTO counts (type, points, count) VALUES\n")
                values = []
                for i, count in enumerate(data['studentCounts']):
                    values.append(f"('student', {i}, {count})")
                for i, count in enumerate(data['teacherCounts']):
                    values.append(f"('teacher', {i}, {count})")
                f.write(',\n'.join(values) + ';')

            self.send_response(200)
            self.end_headers()
        else:
            super().do_POST()

    def do_GET(self):
        if self.path == '/load-sql':
            try:
                studentCounts = [0] * 7
                teacherCounts = [0] * 7

                if os.path.exists(SQL_FILE):
                    with open(SQL_FILE, 'r') as f:
                        lines = f.readlines()
                        for line in lines:
                            if line.strip().startswith("('"):
                                parts = line.strip().strip(",").strip("();").split(",")
                                typ = parts[0].strip(" '")
                                points = int(parts[1])
                                count = int(parts[2])
                                if typ == 'student':
                                    studentCounts[points] = count
                                elif typ == 'teacher':
                                    teacherCounts[points] = count

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'studentCounts': studentCounts,
                    'teacherCounts': teacherCounts
                }).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error loading SQL: {e}".encode())
        else:
            super().do_GET()

def run():
    webbrowser.open(f"http://localhost:8000/index.html")

PORT = 8000

os.chdir(FRONTEND_DIR)
with HTTPServer(('localhost', PORT), MyHandler) as server:
    run()
    print(f"Serving at http://localhost:{PORT}")
    server.serve_forever()