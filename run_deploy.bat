@echo off
REM This is a wrapper script to ensure the deploy_and_launch.bat window stays open
REM It runs the deploy_and_launch.bat script in a new command window with the /K flag
REM which forces the window to stay open after the script completes or encounters an error

echo Starting WiseFlow deployment script...
echo The deployment window will open in a new command prompt.
echo.

REM Run the deploy_and_launch.bat script in a new window that stays open
start cmd /K "deploy_and_launch.bat"

echo.
echo If the deployment window still closes immediately, please try the following:
echo 1. Right-click on run_deploy.bat and select "Run as administrator"
echo 2. Open a command prompt manually, navigate to this folder, and run: deploy_and_launch.bat
echo 3. Contact support if the issue persists
echo.
echo Press any key to exit this window...
pause > nul

