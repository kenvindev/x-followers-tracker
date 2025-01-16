@echo off
setlocal enabledelayedexpansion

:: Check if Python is installed
python --version > nul 2>&1
if errorlevel 1 (
    echo Python is not installed. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

:: Create data directory if it doesn't exist
if not exist "data" (
    mkdir data
    echo Created data directory
)

:: Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment
        pause
        exit /b 1
    )
)

:: Activate virtual environment and install dependencies
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Install requirements
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies
    pause
    exit /b 1
)

:: Check for .env file
if not exist ".env" (
    if exist ".env.example" (
        echo Creating .env file from .env.example...
        copy .env.example .env
        echo Please edit the .env file with your settings:
        echo - TARGET_USERNAME: Twitter username to track
        echo - SCAN_INTERVAL_MINUTES: Time between scans
        echo - SYNC_INTERVAL_MINUTES: Time between API syncs
        echo - WEB_PORT: Port for web interface
        echo - API_ENDPOINT: API endpoint for syncing followers
        echo - API_TOKEN: API authentication token
        pause
    ) else (
        echo .env.example file not found
        pause
        exit /b 1
    )
)

:: Run the application
echo Starting Twitter Follower Tracker...
python src/main.py

:: Keep window open if there's an error
if errorlevel 1 (
    echo Application exited with an error
    pause
) 