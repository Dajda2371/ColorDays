from pathlib import Path
import datetime

# --- Configuration ---
BACKEND_DIR = Path(__file__).parent.resolve()
FRONTEND_DIR = (BACKEND_DIR.parent / 'frontend').resolve()
DATA_DIR = (BACKEND_DIR / 'data').resolve()
LOGS_DIR = DATA_DIR / 'logs'

# --- Refresh Intervals ---
# Keys are HTML file names to match the frontend, values are in milliseconds
REFRESH_INTERVALS = {
    "leaderboard.html": 5000,
    "index.html": 5000,
    "classes.html": 10000,
    "students.html": 10000,
    "student-is-counting.html": 10000
}

# --- Logger Setup ---
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILENAME = datetime.datetime.now().strftime("%Y-%m-%d.log")
LOG_PATH = LOGS_DIR / LOG_FILENAME

# --- Dynamic Data Directory based on Year ---
CURRENT_YEAR_DIR = DATA_DIR / str(datetime.datetime.now().year)

# Update file paths to point to the year-specific directory
LOGINS_SQL_FILE_PATH = DATA_DIR / 'logins.sql'
DOMAIN = 'barevnedny.davidbenes.cz'
HOST = '0.0.0.0'
PORT = 443
SUPPORTED_CLASSES = []
SQL_DAY_FILE_PATHS = {
    "monday": CURRENT_YEAR_DIR / 'tables-monday.sql',
    "tuesday": CURRENT_YEAR_DIR / 'tables-tuesday.sql',
    "wednesday": CURRENT_YEAR_DIR / 'tables-wednesday.sql',
}
STUDENTS_SQL_FILE_PATH = CURRENT_YEAR_DIR / 'students.sql'

# --- Google OAuth Configuration ---
CLIENT_SECRETS_FILE = DATA_DIR / 'client_secret.json'
GOOGLE_SCOPES = ['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']
if PORT == 443:
    GOOGLE_REDIRECT_URI = f'https://{DOMAIN}/oauth2callback'
else:
    GOOGLE_REDIRECT_URI = f'http://{DOMAIN}:{PORT}/oauth2callback'

# --- Secure Login Configuration ---
HASH_ALGORITHM = 'sha256'
ITERATIONS = 390000
SALT_BYTES = 16
DK_LENGTH = 32

# --- Role Configuration ---
ADMIN_ROLE = 'administrator'
TEACHER_ROLE = 'teacher'
DEFAULT_ROLE_FOR_NEW_USERS = TEACHER_ROLE

# --- Session Configuration ---
USERNAME_COOKIE_NAME = "ColorDaysUser"
SESSION_COOKIE_NAME = "ColorDaysSession"
VALID_SESSION_VALUE = "user_is_logged_in_secret_value"
CHANGE_PASSWORD_COOKIE_NAME = "ChangePasswordVerificationNotNeeded"
GOOGLE_COOKIE_NAME = "GoogleAuthUser"
SQL_COOKIE_NAME = "SQLAuthUser"
SQL_AUTH_USER_STUDENT_COOKIE_NAME = "SQLAuthUserStudent"
LANGUAGE_COOKIE_NAME = "language"
TRANSLATIONS_FILE_PATH = BACKEND_DIR / 'constants' / 'language_translations.json'

DATABASE_FILE = DATA_DIR / 'data.db'
YEAR_DATABASE_FILE = DATA_DIR / f"{datetime.datetime.now().year}.db"
