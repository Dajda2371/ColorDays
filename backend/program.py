import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import http.server
import socketserver
import threading

from config import HOST, PORT, LOG_FILENAME, LOG_PATH
from data_manager import (
    load_main_config_from_json,
    create_tables,
    migrate_logins_to_db,
    migrate_tokens_to_db,
    migrate_classes_to_db,
    migrate_students_to_db,
    load_user_data_from_db,
    load_class_data_from_db,
    load_students_data_from_db,
    ensure_year_data_directory_exists,
)
from server import ColorDaysHandler

# --- Logger Setup ---
logger = logging.getLogger('ColorDaysLogger')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler(LOG_PATH, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class StreamToLogger:
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
        self.buffer = ''

    def write(self, message):
        message = message.rstrip()
        if message:
            self.logger.log(self.level, message)

    def flush(self):
        pass

sys.stdout = StreamToLogger(logger, logging.INFO)
sys.stderr = StreamToLogger(logger, logging.ERROR)

logger.info("Logging directly to dated file: %s", LOG_FILENAME)

def main():
    """Main function to run the web server."""
    ensure_year_data_directory_exists()
    load_main_config_from_json()
    load_class_data_from_db()
    load_students_data_from_db()
    load_user_data_from_db()

    # Use ThreadingTCPServer for better performance with multiple connections
    httpd = socketserver.ThreadingTCPServer(("", PORT), ColorDaysHandler)
    httpd.allow_reuse_address = True
    # Set socket timeout to allow shutdown to complete faster
    httpd.socket.settimeout(1.0)

    server_thread = threading.Thread(target=httpd.serve_forever, kwargs={'poll_interval': 0.5})
    server_thread.daemon = True
    server_thread.start()

    print(f"Serving at port {PORT}")
    print("Type 'stop' and press Enter to stop the server.")

    while True:
        try:
            user_input = input().strip().lower()
            if user_input == 'stop':
                print("Stopping server...")
                httpd.shutdown()
                server_thread.join(timeout=5)
                if server_thread.is_alive():
                    print("Warning: Server thread did not stop gracefully")
                httpd.server_close()
                print("Server stopped.")
                break
        except KeyboardInterrupt:
            print("\nStopping server...")
            httpd.shutdown()
            server_thread.join(timeout=5)
            if server_thread.is_alive():
                print("Warning: Server thread did not stop gracefully")
            httpd.server_close()
            print("Server stopped.")
            break
        except EOFError:
            # Handle case when running without stdin (e.g., in background)
            print("No input available (running in background?). Server will continue running.")
            # Keep the server running if there's no stdin
            try:
                server_thread.join()
            except KeyboardInterrupt:
                print("\nStopping server...")
                httpd.shutdown()
                httpd.server_close()
                print("Server stopped.")
            break

if __name__ == "__main__":
    main()