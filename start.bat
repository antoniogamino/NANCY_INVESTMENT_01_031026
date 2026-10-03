@echo off
REM ── Nancy Investment Intelligence: starts backend (FastAPI) and frontend (Vite) ──
setlocal
cd /d "%~dp0"

REM ---- locate Node.js even if it is not in PATH ----
where npm >nul 2>nul && goto :node_ok
if exist "%ProgramFiles%\nodejs\npm.cmd" set "PATH=%ProgramFiles%\nodejs;%PATH%"
if exist "%LOCALAPPDATA%\Programs\nodejs\npm.cmd" set "PATH=%LOCALAPPDATA%\Programs\nodejs;%PATH%"
where npm >nul 2>nul && goto :node_ok
echo [ERROR] Node.js 18+ not found. Install the LTS version from https://nodejs.org
pause
exit /b 1
:node_ok

REM ---- locate Python (python.exe or the "py" launcher) ----
set "PY=python"
where python >nul 2>nul || set "PY=py"
%PY% --version >nul 2>nul && goto :py_ok
echo [ERROR] Python 3.11+ not found. Install it from https://www.python.org and tick "Add Python to PATH"
pause
exit /b 1
:py_ok
echo Using Node:
call npm --version
echo Using Python:
%PY% --version

if not exist ".env" if exist ".env.example" copy ".env.example" ".env" >nul

REM ---- backend ----
if not exist "backend\.venv\Scripts\python.exe" (
  echo [setup] Creating Python virtual environment...
  %PY% -m venv backend\.venv || (echo [ERROR] venv failed & pause & exit /b 1)
  backend\.venv\Scripts\python.exe -m pip install --upgrade pip >nul
  backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt || (echo [ERROR] pip install failed & pause & exit /b 1)
)

REM ---- frontend ----
if not exist "frontend\node_modules" (
  echo [setup] Installing frontend dependencies...
  pushd frontend
  call npm install
  popd
)

echo Starting backend on http://127.0.0.1:8000 ...
start "NII backend" /D "%~dp0backend" cmd /k .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

echo Starting frontend on http://localhost:5173 ...
start "NII frontend" /D "%~dp0frontend" cmd /k npm run dev

timeout /t 6 /nobreak >nul
start "" http://localhost:5173
echo.
echo Both servers are running in their own windows. Close those windows to stop them.
endlocal
