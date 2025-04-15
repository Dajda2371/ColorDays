import webbrowser
import http.server
import socketserver
import os
import json

PORT = 8000

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "../frontend")
DATA_DIR = os.path.join(BASE_DIR, "data")
SQL_FILE = os.path.join(DATA_DIR, "tables.sql")

os.makedirs(DATA_DIR, exist_ok=True)  # Make sure /data exists
os.chdir(FRONTEND_DIR)  # Serve frontend files

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/save-sql':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                student_counts = data.get('studentCounts', [])
                teacher_counts = data.get('teacherCounts', [])

                sql_lines = ["-- SQL Export of point_counts", "DELETE FROM point_counts;"]
                for i in range(0, 7):
                    student = student_counts[i] if i < len(student_counts) else 0
                    teacher = teacher_counts[i] if i < len(teacher_counts) else 0
                    sql_lines.append(f"INSERT INTO point_counts (role, points, count) VALUES ('student', {i}, {student});")
                    sql_lines.append(f"INSERT INTO point_counts (role, points, count) VALUES ('teacher', {i}, {teacher});")

                with open(SQL_FILE, 'w') as f:
                    f.write("\n".join(sql_lines))

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"message": "SQL saved"}')

            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_msg = json.dumps({ "error": str(e) }).encode('utf-8')
                self.wfile.write(error_msg)
        else:
            self.send_error(404, 'Not Found')

Handler = CustomHandler

def run():
    webbrowser.open(f"http://localhost:{PORT}/index.html")

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    run()  # Comment out for headless
    print(f"Server running at http://localhost:{PORT}")
    httpd.serve_forever()