@echo off
:: WiseFlow Deployment Script for Windows
:: This script provides a simple way to deploy WiseFlow on Windows systems.

setlocal enabledelayedexpansion

:: Function to display help message
:show_help
echo WiseFlow Deployment Script
echo Usage: deploy.bat [options]
echo.
echo Options:
echo   --setup         Run the setup script
echo   --start         Start WiseFlow
echo   --stop          Stop WiseFlow
echo   --restart       Restart WiseFlow
echo   --status        Check WiseFlow status
echo   --logs          View WiseFlow logs
echo   --update        Update WiseFlow
echo   --docker        Use Docker deployment
echo   --native        Use native deployment
echo   --help          Show this help message
echo.
echo Examples:
echo   deploy.bat --setup          # Run the setup script
echo   deploy.bat --start          # Start WiseFlow
echo   deploy.bat --docker --start # Start WiseFlow with Docker
goto :eof

:: Parse command line arguments
set SETUP=false
set START=false
set STOP=false
set RESTART=false
set STATUS=false
set LOGS=false
set UPDATE=false
set DOCKER=false
set NATIVE=false

:: If no arguments provided, show help
if "%~1"=="" (
    call :show_help
    exit /b 0
)

:: Parse arguments
:parse_args
if "%~1"=="" goto :end_parse_args
if "%~1"=="--setup" (
    set SETUP=true
    shift
    goto :parse_args
)
if "%~1"=="--start" (
    set START=true
    shift
    goto :parse_args
)
if "%~1"=="--stop" (
    set STOP=true
    shift
    goto :parse_args
)
if "%~1"=="--restart" (
    set RESTART=true
    shift
    goto :parse_args
)
if "%~1"=="--status" (
    set STATUS=true
    shift
    goto :parse_args
)
if "%~1"=="--logs" (
    set LOGS=true
    shift
    goto :parse_args
)
if "%~1"=="--update" (
    set UPDATE=true
    shift
    goto :parse_args
)
if "%~1"=="--docker" (
    set DOCKER=true
    shift
    goto :parse_args
)
if "%~1"=="--native" (
    set NATIVE=true
    shift
    goto :parse_args
)
if "%~1"=="--help" (
    call :show_help
    exit /b 0
)
echo Unknown option: %~1
call :show_help
exit /b 1

:end_parse_args

:: Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python is not installed. Please install Python and try again.
    exit /b 1
)

:: Run setup script
if "%SETUP%"=="true" (
    echo Running setup script...
    if "%DOCKER%"=="true" (
        python setup.py --all --docker
    ) else if "%NATIVE%"=="true" (
        python setup.py --all --native
    ) else (
        python setup.py --all
    )
)

:: Run deploy script
if "%START%"=="true" (
    echo Starting WiseFlow...
    if "%DOCKER%"=="true" (
        python deploy.py --docker --start
    ) else if "%NATIVE%"=="true" (
        python deploy.py --native --start
    ) else (
        python deploy.py --start
    )
)

if "%STOP%"=="true" (
    echo Stopping WiseFlow...
    if "%DOCKER%"=="true" (
        python deploy.py --docker --stop
    ) else if "%NATIVE%"=="true" (
        python deploy.py --native --stop
    ) else (
        python deploy.py --stop
    )
)

if "%RESTART%"=="true" (
    echo Restarting WiseFlow...
    if "%DOCKER%"=="true" (
        python deploy.py --docker --restart
    ) else if "%NATIVE%"=="true" (
        python deploy.py --native --restart
    ) else (
        python deploy.py --restart
    )
)

if "%STATUS%"=="true" (
    echo Checking WiseFlow status...
    if "%DOCKER%"=="true" (
        python deploy.py --docker --status
    ) else if "%NATIVE%"=="true" (
        python deploy.py --native --status
    ) else (
        python deploy.py --status
    )
)

if "%LOGS%"=="true" (
    echo Viewing WiseFlow logs...
    if "%DOCKER%"=="true" (
        python deploy.py --docker --logs
    ) else if "%NATIVE%"=="true" (
        python deploy.py --native --logs
    ) else (
        python deploy.py --logs
    )
)

if "%UPDATE%"=="true" (
    echo Updating WiseFlow...
    if "%DOCKER%"=="true" (
        python deploy.py --docker --update
    ) else if "%NATIVE%"=="true" (
        python deploy.py --native --update
    ) else (
        python deploy.py --update
    )
)

:: Keep the window open
echo.
echo Press any key to exit...
pause >nul

