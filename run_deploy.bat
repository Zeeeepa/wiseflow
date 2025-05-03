@echo off
setlocal enabledelayedexpansion

:: This script is a simplified launcher for deploy_and_launch.bat
:: It ensures the script runs from the correct directory

:: Get the directory of this script
set "SCRIPT_DIR=%~dp0"

:: Change to the script directory
cd /d "%SCRIPT_DIR%"

echo Starting WiseFlow deployment script...
echo The deployment window will open and stay open until the process completes.
echo.

:: Run the main deployment script
call deploy_and_launch.bat
set DEPLOY_RESULT=%errorlevel%

:: Provide feedback if there was an error
if %DEPLOY_RESULT% NEQ 0 (
    echo.
    echo Deployment encountered an error (code: %DEPLOY_RESULT%).
    echo Please check the deploy_log.txt file for more details.
    echo.
    echo Press any key to exit...
    pause >nul
)

:: Exit with the same error code
exit /b %DEPLOY_RESULT%
