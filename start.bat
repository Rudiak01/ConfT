@echo off
echo ===================================================
echo Starting ConfT - Network Configuration Tool
echo ===================================================

@REM echo.
@REM echo [1/3] Starting Docker containers (MariaDB and phpMyAdmin)...
@REM docker compose up -d

@REM echo.
@REM echo Waiting 5 seconds for the database to be ready...
@REM timeout /t 5 /nobreak > NUL

echo.
echo [2/3] Activating Python virtual environment...
if exist "env\Scripts\activate.bat" (
    call env\Scripts\activate.bat
) else (
    echo [WARNING] Virtual environment 'env' not found. Ensure dependencies are installed globally.
)

echo.
echo [3/3] Starting FastAPI server...
echo The application will be available at: http://localhost:8000
echo.
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

pause
