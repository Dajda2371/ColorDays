@echo off

REM Activate virtual environment if it exists
IF EXIST .venv (
    CALL .venv\Scripts\activate.bat
)

cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload