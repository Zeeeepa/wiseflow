@echo off
setlocal enabledelayedexpansion

:: This script is a simplified launcher for deploy_and_launch.bat
:: It ensures the script runs from the correct directory

:: Get the directory of this script
set "SCRIPT_DIR=%~dp0"

:: Change to the script directory
cd /d "%SCRIPT_DIR%"

:: Run the main deployment script
call deploy_and_launch.bat

:: Exit with the same error code
exit /b %errorlevel%

