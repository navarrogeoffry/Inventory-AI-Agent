@echo off
:: Start Inventory AI Agent (both backend and frontend)
:: This script starts both servers and keeps them running

TITLE Inventory AI Agent Launcher

echo Starting Inventory AI Agent...
echo.

:: Create logs directory
if not exist logs mkdir logs

:: Check for OpenAI API key in .env file
if exist .env (
  set /p OPENAI_API_KEY=<.env
  for /f "tokens=1,* delims==" %%a in (.env) do (
    if "%%a"=="OPENAI_API_KEY" set OPENAI_API_KEY=%%b
  )
)

:: Check if key is set
if "%OPENAI_API_KEY%"=="" (
  echo ERROR: OpenAI API key not found.
  echo Please run setup_env.bat to set up your API key.
  echo.
  pause
  exit /b 1
)

:: Set the Python path to the current directory
set PYTHONPATH=%CD%

:: Start the backend server in a new window with logging
echo Starting backend server...
start "Inventory AI Backend" cmd /k "python app\main.py > logs\backend.log 2>&1"

:: Wait for the backend to initialize
timeout /t 5 /nobreak > nul

:: Check if backend log has errors
findstr /C:"ERROR" logs\backend.log > nul
if %ERRORLEVEL% == 0 (
  echo WARNING: Backend may have encountered errors. Check logs\backend.log for details.
  echo Common issues:
  echo - Invalid OpenAI API key
  echo - Missing dependencies (run pip install -r requirements.txt)
  echo.
)

:: Start the React frontend in a new window with logging
echo Starting frontend server...
cd chatbot-ui
start "Inventory AI Frontend" cmd /k "npm start > ..\logs\frontend.log 2>&1"

echo.
echo Servers are starting...
echo Backend server: http://localhost:8000
echo Frontend: will open automatically in your browser
echo.
echo Backend logs: logs\backend.log
echo Frontend logs: logs\frontend.log
echo.

echo Servers are running in separate windows.
echo Close those windows to stop the servers.
echo.

pause 