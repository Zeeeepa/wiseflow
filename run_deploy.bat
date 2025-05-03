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
    echo.
    echo Troubleshooting tips:
    echo 1. Check deploy_log.txt for detailed error information
    echo 2. Make sure Git and Python 3.8+ are installed
    echo 3. Verify you have internet connection to clone the repository
    echo 4. Ensure the PocketBase installation script exists at:
    echo    "%SCRIPT_DIR%wiseflow\install_pocketbase.ps1" or
    echo    "%SCRIPT_DIR%install_pocketbase.ps1"
    echo 5. Run as administrator if you encounter permission issues
    echo.
    echo Press any key to exit...
    pause >nul
)

:: Exit with the same error code
exit /b %DEPLOY_RESULT%
