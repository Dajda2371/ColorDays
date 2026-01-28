from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import (
    FRONTEND_DIR, ADMIN_ROLE, SESSION_COOKIE_NAME, VALID_SESSION_VALUE,
    SQL_AUTH_USER_STUDENT_COOKIE_NAME, DATABASE_FILE, YEAR_DATABASE_FILE, BACKEND_DIR
)
from data_manager import (
    load_user_data_from_db,
    load_class_data_from_db,
    load_students_data_from_db,
    load_main_config_from_json,
    ensure_year_data_directory_exists,
    create_tables
)
from routers import auth, users, classes, students, counts, config as config_router
from dependencies import get_current_user_info, active_sessions

# Setup startup tasks
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Startup: Loading data...")
    # Ensure directories exist
    ensure_year_data_directory_exists()

    # Initialize DBs
    try:
        create_tables(DATABASE_FILE, BACKEND_DIR / 'schema.sql')
        create_tables(YEAR_DATABASE_FILE, BACKEND_DIR / 'schema_year.sql')
    except Exception as e:
         print(f"Error initializing database tables: {e}")

    # Load data
    try:
        load_user_data_from_db()
        load_class_data_from_db()
        load_students_data_from_db()
        load_main_config_from_json()
    except Exception as e:
        print(f"Error loading initial data: {e}")

    yield
    print("Shutdown: cleanup if needed")

app = FastAPI(lifespan=lifespan)

# CORS configuration
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(classes.router)
app.include_router(students.router)
app.include_router(counts.router)
app.include_router(config_router.router)

# Protected pages
@app.get("/")
@app.get("/index.html")
@app.get("/menu.html")
@app.get("/classes.html")
@app.get("/config.html")
@app.get("/students.html")
@app.get("/change-password.html")
async def protected_pages(request: Request):
    path = request.url.path
    if path == "/":
        path = "/index.html"

    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    is_logged_in = False
    if session_cookie and (session_cookie == VALID_SESSION_VALUE or session_cookie in active_sessions):
         is_logged_in = True

    if not is_logged_in:
        return RedirectResponse("/login.html")

    user_key, user_role = get_current_user_info(request)

    if path == "/config.html":
        if user_role != ADMIN_ROLE:
             return JSONResponse(status_code=403, content={"error": "Forbidden: Administrator access required."})

    if path == "/classes.html":
        if request.cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME):
             return JSONResponse(status_code=403, content={"error": "Forbidden: Access to this page is restricted for your account type."})

    file_path = FRONTEND_DIR / path.lstrip('/')
    if file_path.is_file():
        return FileResponse(file_path)
    return Response(status_code=404)

# Mount static files
app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="static")
