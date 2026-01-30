@echo off
setlocal
cd /d "%~dp0.."
set "REPO_ROOT=%CD%"

echo Setting up admin password...
python backend\setup_admin.py %*
if %ERRORLEVEL% NEQ 0 (
    echo "Error running setup script."
    exit /b %ERRORLEVEL%
)

endlocal
