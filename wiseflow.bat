@echo off
REM WiseFlow Launcher Script for Windows

REM Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Python is required but not installed. Please install Python and try again.
    exit /b 1
)

REM Check if pip is installed
where pip >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo pip is required but not installed. Please install pip and try again.
    exit /b 1
)

REM Check if virtual environment exists, create if not
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    
    REM Activate virtual environment
    call venv\Scripts\activate.bat
    
    REM Install dependencies
    echo Installing dependencies...
    pip install -r requirements.txt
) else (
    REM Activate virtual environment
    call venv\Scripts\activate.bat
)

REM Check if .env file exists, create from example if not
if not exist .env (
    if exist .env.example (
        echo Creating .env file from .env.example...
        copy .env.example .env
        echo Please edit the .env file with your configuration before running WiseFlow.
        exit /b 1
    ) else (
        echo No .env or .env.example file found. Please create a .env file with your configuration.
        exit /b 1
    )
)

REM Run the WiseFlow launcher
python wiseflow.py %*

