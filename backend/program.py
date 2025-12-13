import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import http.server
import socketserver

from config import HOST, PORT, LOG_FILENAME, LOG_PATH
from data_manager import (
    load_class_data_from_sql,
    load_students_data_from_sql,
    load_user_data_from_sql,
    load_main_config_from_json,
    ensure_year_data_directory_exists,
    update_data_file_paths,
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
    update_data_file_paths()
    load_main_config_from_json()
    load_class_data_from_sql()
    load_students_data_from_sql()
    load_user_data_from_sql()

    with socketserver.TCPServer(("", PORT), ColorDaysHandler) as httpd:
        print(f"Serving at port {PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    main()