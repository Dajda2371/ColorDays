import webbrowser
import http.server
import socketserver
import os

PORT = 8000

# Get absolute path to frontend folder relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "../frontend")

# Change working directory to frontend
os.chdir(os.path.abspath(FRONTEND_DIR))

Handler = http.server.SimpleHTTPRequestHandler

def run():
    webbrowser.open(f"http://localhost:{PORT}/index.html")

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    run() # Only for testing purposes, comment out while running the server.
    print(f"Server running at http://localhost:{PORT}")
    httpd.serve_forever()