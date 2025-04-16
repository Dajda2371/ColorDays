import webbrowser
import os
import json
from http.server import SimpleHTTPRequestHandler, HTTPServer
import urllib.parse

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
        if self.path == "/save-sql":
            length = int(self.headers['Content-Length'])
            data = self.rfile.read(length)
            payload = json.loads(data)

            student_counts = payload.get("studentCounts", [0]*7)
            teacher_counts = payload.get("teacherCounts", [0]*7)

            sql = generate_sql(student_counts, teacher_counts)
            with open(SQL_FILE, 'w') as f:
                f.write(sql)

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"saved"}')

        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == "/load-sql":
            student_counts, teacher_counts = parse_sql()
            response = {
                "studentCounts": student_counts,
                "teacherCounts": teacher_counts
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            super().do_GET()

def run():
    webbrowser.open(f"http://localhost:8000/index.html")

os.chdir(FRONTEND_DIR)
with HTTPServer(("", 8000), MyHandler) as httpd:
    run()
    print("Server running at http://localhost:8000")
    httpd.serve_forever()