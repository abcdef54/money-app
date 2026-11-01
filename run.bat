@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo ========================================
echo Personal Finance Analytics - One Click Run
echo ========================================
echo.

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm is not installed or not on PATH.
  echo Install Node.js LTS from https://nodejs.org and try again.
  pause
  exit /b 1
)

echo [1/5] Preparing backend virtual environment...
pushd "%ROOT%backend"
if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 -m venv .venv
  ) else (
    python -m venv .venv
  )
)
if errorlevel 1 (
  echo [ERROR] Failed to create backend virtual environment.
  popd
  pause
  exit /b 1
)

echo [2/5] Installing backend dependencies...
call ".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
  echo [ERROR] Failed to upgrade pip.
  popd
  pause
  exit /b 1
)
call ".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] Failed to install backend requirements.
  popd
  pause
  exit /b 1
)

echo [3/5] Applying database migrations...
call ".venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 (
  echo [ERROR] Failed to apply migrations.
  popd
  pause
  exit /b 1
)

if not exist "finance.db" (
  echo [4/5] Seeding initial data on first run...
  call ".venv\Scripts\python.exe" seed.py
  if errorlevel 1 (
    echo [ERROR] Failed to seed database.
    popd
    pause
    exit /b 1
  )
) else (
  echo [4/5] Database exists, skipping seed step.
)
popd

echo [5/5] Installing frontend dependencies (if needed)...
pushd "%ROOT%frontend"
if not exist "node_modules" (
  call npm install
  if errorlevel 1 (
    echo [ERROR] Failed to install frontend dependencies.
    popd
    pause
    exit /b 1
  )
) else (
  echo Frontend dependencies already installed.
)
popd

echo.
echo Starting backend and frontend in separate windows...
start "Backend - FastAPI" cmd /k "cd /d ""%ROOT%backend"" && call "".venv\Scripts\activate.bat"" && uvicorn app.main:app --reload"
start "Frontend - Vite" cmd /k "cd /d ""%ROOT%frontend"" && npm run dev"

echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo API Docs: http://localhost:8000/docs
echo.
echo You can close this window. Servers continue in the two new terminal windows.
exit /b 0
