import webbrowser
import http.server
import socketserver

PORT = 8000

# Define handler
Handler = http.server.SimpleHTTPRequestHandler

def open():
    # Opens the UI in a web browser.
    webbrowser.open(f"http://localhost:{PORT}/index.html")

# Start the server
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    open()
    print(f"Server running at http://localhost:{PORT}")
    httpd.serve_forever()