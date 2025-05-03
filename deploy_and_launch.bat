@echo off
setlocal enabledelayedexpansion

echo ===== WiseFlow Deployment and Launch Script =====
echo.

REM Keep track of the original directory
set "ORIGINAL_DIR=%CD%"

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

REM Fix: Add a fallback method for Python version detection
python -c "import sys; print(sys.version_info[0])" > python_version.tmp 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Warning: Could not determine Python version using primary method.
    echo Trying alternative method...
    python --version > python_version_full.tmp 2>&1
    for /f "tokens=2 delims= " %%i in (python_version_full.tmp) do (
        for /f "tokens=1 delims=." %%j in ("%%i") do set PYTHON_MAJOR=%%j
    )
    del python_version_full.tmp
) else (
    set /p PYTHON_MAJOR=<python_version.tmp
    del python_version.tmp
)

echo Detected Python version: %PYTHON_MAJOR%
if %PYTHON_MAJOR% LSS 3 (
    echo Python version must be 3.8 or higher.
    echo Press any key to exit...
    pause >nul
    cd "%ORIGINAL_DIR%"
    exit /b 1
)

REM Check if repository exists, if not clone it
if not exist wiseflow\ (
    echo Cloning WiseFlow repository...
    git clone https://github.com/Zeeeepa/wiseflow.git
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to clone repository.
        echo Press any key to exit...
        pause >nul
        exit /b 1
    )
    cd wiseflow
) else (
    echo WiseFlow repository already exists.
    
    REM Ask if user wants to update the repository
    set /p UPDATE_REPO=Do you want to update the repository? (y/n): 
    if /i "!UPDATE_REPO!"=="y" (
        echo Updating WiseFlow repository...
        cd wiseflow
        git pull
    ) else (
        cd wiseflow
    )
)

REM Install PocketBase if not already installed
if not exist pb\pocketbase.exe (
    echo Installing PocketBase...
    powershell -ExecutionPolicy Bypass -File install_pocketbase.ps1
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to install PocketBase.
        echo Press any key to exit...
        pause >nul
        cd "%ORIGINAL_DIR%"
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
    REM Check if conda is available
    where conda >nul 2>nul
    set CONDA_AVAILABLE=%ERRORLEVEL%
    
    if %CONDA_AVAILABLE% EQU 0 (
        echo Using Conda to create environment...
        set PYTHON_VERSION=3.12
        if defined WISEFLOW_PYTHON_VERSION set PYTHON_VERSION=!WISEFLOW_PYTHON_VERSION!
        
        REM Check if conda environment already exists
        conda env list | findstr /C:"wiseflow" >nul
        if %ERRORLEVEL% NEQ 0 (
            conda create -n wiseflow python=!PYTHON_VERSION! -y
            if %ERRORLEVEL% NEQ 0 (
                echo Failed to create conda environment.
                echo Press any key to exit...
                pause >nul
                cd "%ORIGINAL_DIR%"
                exit /b 1
            )
        ) else (
            echo Conda environment 'wiseflow' already exists.
        )
        
        REM Activate conda environment
        echo Activating conda environment...
        call conda activate wiseflow
        if %ERRORLEVEL% NEQ 0 (
            echo Failed to activate conda environment.
            set /p CONTINUE_WITHOUT_ENV=Continue without environment? (y/n): 
            if /i "!CONTINUE_WITHOUT_ENV!"=="n" (
                echo Aborting setup as requested.
                echo Press any key to exit...
                pause >nul
                cd "%ORIGINAL_DIR%"
                exit /b 1
            ) else (
                echo Continuing without conda environment...
            )
        )
    ) else (
        echo Conda not found. Using venv instead...
        if not exist venv\ (
            python -m venv venv
            if %ERRORLEVEL% NEQ 0 (
                echo Failed to create virtual environment.
                echo Press any key to exit...
                pause >nul
                cd "%ORIGINAL_DIR%"
                exit /b 1
            )
        ) else (
            echo Virtual environment already exists.
        )
        
        REM Activate venv
        echo Activating virtual environment...
        call venv\Scripts\activate.bat
        if %ERRORLEVEL% NEQ 0 (
            echo Failed to activate virtual environment.
            set /p CONTINUE_WITHOUT_ENV=Continue without environment? (y/n): 
            if /i "!CONTINUE_WITHOUT_ENV!"=="n" (
                echo Aborting setup as requested.
                echo Press any key to exit...
                pause >nul
                cd "%ORIGINAL_DIR%"
                exit /b 1
            ) else (
                echo Continuing without virtual environment...
            )
        )
    )
)

REM Install dependencies
echo Installing Python dependencies...
cd core || (
    echo Failed to navigate to core directory.
    echo Press any key to exit...
    pause >nul
    cd "%ORIGINAL_DIR%"
    exit /b 1
)

pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install Python dependencies.
    echo Press any key to exit...
    pause >nul
    cd "%ORIGINAL_DIR%"
    exit /b 1
)

REM Install Playwright
echo Installing Playwright...
python -m playwright install --with-deps chromium
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install Playwright.
    echo Press any key to exit...
    pause >nul
    cd "%ORIGINAL_DIR%"
    exit /b 1
)

REM Launch WiseFlow
echo.
echo ===== WiseFlow Setup Complete =====
echo.
echo Starting WiseFlow...

REM Fix: Navigate back to the main directory before checking for run scripts
cd ..

REM Check if windows_run.py exists
if exist windows_run.py (
    python windows_run.py
) else (
    echo windows_run.py not found. Trying to run app.py instead...
    if exist app.py (
        python app.py
    ) else (
        echo Could not find the main application file.
        echo Press any key to exit...
        pause >nul
        cd "%ORIGINAL_DIR%"
        exit /b 1
    )
)

REM Return to original directory
cd "%ORIGINAL_DIR%"

REM Keep the window open after completion
echo.
echo WiseFlow has been closed. Press any key to exit...
pause >nul

endlocal
