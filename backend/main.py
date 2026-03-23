from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import (
    FRONTEND_DIR, ADMIN_ROLE, SESSION_COOKIE_NAME, VALID_SESSION_VALUE,
    SQL_AUTH_USER_STUDENT_COOKIE_NAME, DATABASE_FILE, YEAR_DATABASE_FILE, BACKEND_DIR,
    PORT, DOMAIN, LANGUAGE_COOKIE_NAME
)
from data_manager import (
    load_user_data_from_db,
    load_class_data_from_db,
    load_students_data_from_db,
    load_main_config_from_json,
    create_tables,
    server_config
)
from dependencies import get_current_user_info, active_sessions
import importlib.util
import os
from pathlib import Path

# Setup startup tasks
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Startup: Loading data...")

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
    f"http://localhost:{PORT}",
    f"http://127.0.0.1:{PORT}",
    f"https://localhost:{PORT}" if PORT != 443 else "https://localhost",
    f"https://127.0.0.1:{PORT}" if PORT != 443 else "https://127.0.0.1",
    f"http://{DOMAIN}:{PORT}",
    f"https://{DOMAIN}" if PORT == 443 else f"https://{DOMAIN}:{PORT}",
]

import asyncio

global_write_lock = asyncio.Lock()

@app.middleware("http")
async def language_cookie_middleware(request: Request, call_next):
    if LANGUAGE_COOKIE_NAME not in request.cookies:
        response = await call_next(request)
        default_lang = server_config.get("default_language", "en")
        response.set_cookie(key=LANGUAGE_COOKIE_NAME, value=default_lang, max_age=31536000, path="/")
        return response
    return await call_next(request)

@app.middleware("http")
async def force_password_change_middleware(request: Request, call_next):
    from config import CHANGE_PASSWORD_COOKIE_NAME
    if request.cookies.get(CHANGE_PASSWORD_COOKIE_NAME):
        allowed_paths = ["/change-password.html", "/logout", "/api/logout", "/api/translations", "/api/language/set"]
        is_allowed = request.url.path in allowed_paths or \
                     request.url.path.startswith("/api/auth/") or \
                     request.url.path.startswith("/oauth2callback") or \
                     request.url.path.startswith("/api/translations") or \
                     any(request.url.path.endswith(ext) for ext in [".css", ".js", ".png", ".jpg", ".svg", ".json", ".ico"])
        
        if not is_allowed:
             if request.url.path.startswith("/api/"):
                  return JSONResponse(status_code=403, content={"error": "Password change required."})
             return RedirectResponse("/change-password.html?forced=true")
        
    return await call_next(request)

@app.middleware("http")
async def concurrency_lock_middleware(request: Request, call_next):
    if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
        async with global_write_lock:
            return await call_next(request)
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def include_routers_recursively(app: FastAPI, directory: Path):
    print(f"Loading routers from {directory}...")
    routers_to_include = []

    method_priority = {
        "GET": 0,
        "POST": 1,
        "PATCH": 2,
        "PUT": 3,
        "DELETE": 4
    }

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                file_path = Path(root) / file
                # Generate a unique module name
                module_name = "api_dynamic_" + str(file_path.relative_to(directory)).replace(os.sep, "_").replace(".", "_")

                try:
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        if hasattr(module, "router"):
                            # Determine metadata for sorting
                            router = module.router

                            # Determine Category
                            category = file_path.parent.name
                            if category.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH", "API"]:
                                category = "General"

                            # Determine Path and Method
                            path = ""
                            method_rank = 10

                            if router.routes:
                                route = router.routes[0]
                                path = getattr(route, "path", "")
                                methods = getattr(route, "methods", set())
                                if methods:
                                    # Find the method with the highest priority (lowest rank)
                                    best_rank = 10
                                    for m in methods:
                                        rank = method_priority.get(m, 5)
                                        if rank < best_rank:
                                            best_rank = rank
                                    method_rank = best_rank

                            routers_to_include.append({
                                "module": module,
                                "category": category,
                                "path": path,
                                "method_rank": method_rank
                            })

                except Exception as e:
                    print(f"Error loading router from {file_path}: {e}")

    # Sort the routers
    def sort_key(item):
        return (item["category"], item["path"], item["method_rank"])

    routers_to_include.sort(key=sort_key)

    # Include them
    for item in routers_to_include:
        print(f"Including router from {item['module'].__file__} (Category: {item['category']})")
        app.include_router(item['module'].router, tags=[item['category']])

include_routers_recursively(app, BACKEND_DIR / "api")

# Protected pages
@app.get("/")
@app.get("/index.html")
@app.get("/menu.html")
@app.get("/classes.html")
@app.get("/config.html")
@app.get("/students.html")
@app.get("/change-password.html")
@app.get("/leaderboard.html")
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

    # Forced password change redirect
    from config import CHANGE_PASSWORD_COOKIE_NAME
    if request.cookies.get(CHANGE_PASSWORD_COOKIE_NAME) and path != "/change-password.html":
        return RedirectResponse("/change-password.html?forced=true")

    if path == "/config.html":
        if user_role != ADMIN_ROLE:
             return JSONResponse(status_code=403, content={"error": "Forbidden: Administrator access required."})

    if path in ["/classes.html", "/change-password.html", "/leaderboard.html"]:
        if request.cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME):
             return JSONResponse(status_code=403, content={"error": "Forbidden: Access to this page is restricted for your account type."})

    file_path = FRONTEND_DIR / path.lstrip('/')
    if file_path.is_file():
        return FileResponse(file_path)
    return Response(status_code=404)

# Mount static files
app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="static")
