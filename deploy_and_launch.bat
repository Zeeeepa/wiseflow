@echo off
setlocal enabledelayedexpansion

echo ===== WiseFlow Deployment and Launch Script =====
echo.

REM Check if Git is installed
where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Git is not installed. Please install Git from https://git-scm.com/downloads/win
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

REM Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Python is not installed. Please install Python from https://www.python.org/downloads/
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

REM Check if repository exists, if not clone it
if not exist wiseflow\ (
    echo Cloning WiseFlow repository...
    git clone https://github.com/TeamWiseFlow/wiseflow.git
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to clone repository.
        echo Press any key to exit...
        pause >nul
        exit /b 1
    )
) else (
    echo WiseFlow repository already exists.
    
    REM Ask if user wants to update the repository
    set /p UPDATE_REPO=Do you want to update the repository? (y/n): 
    if /i "!UPDATE_REPO!"=="y" (
        echo Updating WiseFlow repository...
        cd wiseflow
        git pull
        cd ..
    )
)

REM Navigate to wiseflow directory
cd wiseflow

REM Install PocketBase if not already installed
if not exist pb\pocketbase.exe (
    echo Installing PocketBase...
    powershell -ExecutionPolicy Bypass -File install_pocketbase.ps1
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to install PocketBase.
        echo Press any key to exit...
        pause >nul
        exit /b 1
    )
)

REM Check if .env file exists in core directory, if not create it
if not exist core\.env (
    echo Creating .env file in core directory...
    echo Please configure your .env file with the required settings.
    
    REM Create a basic .env file template
    (
        echo # LLM API Configuration
        echo LLM_API_KEY=Your_API_KEY
        echo LLM_API_BASE="https://api.siliconflow.cn/v1"
        echo PRIMARY_MODEL="deepseek-ai/DeepSeek-R1-Distill-Qwen-14B"
        echo SECONDARY_MODEL="Qwen/Qwen2.5-14B-Instruct"
        echo VL_MODEL="deepseek-ai/deepseek-vl2"
        echo PROJECT_DIR="work_dir"
        echo.
        echo # PocketBase Configuration
        echo PB_API_AUTH="test@example.com|1234567890"
        echo.
        echo # ZhiPu API Configuration (for search engine)
        echo ZHIPU_API_KEY=Your_API_KEY
        echo.
        echo # Optional Configurations
        echo #VERBOSE="true"
        echo #PB_API_BASE=""
        echo #LLM_CONCURRENT_NUMBER=8
    ) > core\.env
    
    echo .env file created. Please edit it with your API keys and settings.
    echo Press any key to open the .env file for editing...
    pause >nul
    start notepad core\.env
    
    echo After configuring the .env file, press any key to continue...
    pause >nul
)

REM Ask if user wants to create a Python virtual environment
set /p CREATE_VENV=Do you want to create a Python virtual environment? (y/n): 
if /i "!CREATE_VENV!"=="y" (
    echo Creating Python virtual environment...
:: Check Python version
for /f "tokens=2 delims=." %%i in ('python -c "import sys; print(sys.version)"') do set PYTHON_VER=%%i
if %PYTHON_VER% LSS 8 (
    echo Python version must be 3.8 or higher
    call :handleError "Python version check"
)

:: Create conda environment with configurable Python version
set PYTHON_VERSION=3.12
if defined WISEFLOW_PYTHON_VERSION set PYTHON_VERSION=%WISEFLOW_PYTHON_VERSION%
conda create -n wiseflow python=%PYTHON_VERSION% -y
        echo Using Conda to create environment...
        conda create -n wiseflow python=3.12 -y
        conda activate wiseflow
    ) else (
        echo Conda not found. Using venv instead...
        python -m venv venv
        call venv\Scripts\activate
    )
)

REM Install dependencies
echo Installing Python dependencies...
cd core
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install Python dependencies.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

REM Install Playwright
echo Installing Playwright...
python -m playwright install --with-deps chromium
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install Playwright.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

REM Launch WiseFlow
echo.
echo ===== WiseFlow Setup Complete =====
echo.
echo Starting WiseFlow...
python windows_run.py

REM Return to original directory
cd ..

endlocal

