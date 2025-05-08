@echo off
:: Setup environment for Inventory AI Agent
:: This script helps set up the OpenAI API key

TITLE Inventory AI Agent - Environment Setup

echo Inventory AI Agent - Environment Setup
echo.

:: Check if .env file exists
if exist .env (
  echo An .env file already exists. Do you want to overwrite it? (y/n)
  set /p response=
  if /i not "%response%"=="y" (
    echo Setup canceled. Your existing .env file was not modified.
    goto :end
  )
)

:: Ask for OpenAI API key
echo Please enter your OpenAI API key:
set /p api_key=

:: Create .env file
echo # Inventory AI Agent Environment Variables > .env
echo. >> .env
echo # OpenAI API key >> .env
echo OPENAI_API_KEY=%api_key% >> .env
echo. >> .env
echo # Database path (defaults to inventory.db in project root) >> .env
echo # DATABASE_URL=path/to/inventory.db >> .env

echo.
echo Environment setup complete!
echo Your OpenAI API key has been saved to the .env file.
echo.
echo Next steps:
echo 1. Run start_app.bat to start the application
echo 2. Access the web interface at http://localhost:3000
echo.

:end
pause 