@echo off
setlocal enabledelayedexpansion

:: This ensures the window stays open even if the script fails
:: by setting up an error handler at the end
goto :main

:error
echo.
echo Error occurred! Error code: %errorlevel%
echo.
echo Press any key to exit...
pause >nul
exit /b %errorlevel%

:main
:: Save the start directory
set "ORIGINAL_DIR=%CD%"
set "SCRIPT_DIR=%~dp0"

echo ===== WiseFlow Deployment and Launch Script =====
echo.
echo Current directory: %CD%
echo Script directory: %SCRIPT_DIR%
echo.

:: Create a log file to track progress
echo WiseFlow deployment started at %date% %time% > "%SCRIPT_DIR%deploy_log.txt"

:: Check if Git is installed
echo Checking for Git...
where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Git is not installed. Please install Git from https://git-scm.com/downloads/win
    echo Git check failed >> "%SCRIPT_DIR%deploy_log.txt"
    goto :error
)
echo Git is installed >> "%SCRIPT_DIR%deploy_log.txt"

:: Check if Python is installed
echo Checking for Python...
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Python is not installed. Please install Python from https://www.python.org/downloads/
    echo Python check failed >> "%SCRIPT_DIR%deploy_log.txt"
    goto :error
)
echo Python is installed >> "%SCRIPT_DIR%deploy_log.txt"

:: Check Python version safely with error handling
echo Checking Python version...
python -c "import sys; print('Python ' + sys.version)" > "%TEMP%\pyversion.txt" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Failed to check Python version.
    type "%TEMP%\pyversion.txt"
    echo Python version check failed >> "%SCRIPT_DIR%deploy_log.txt"
    goto :error
)

:: Extract Python major version with error handling
python -c "import sys; print(sys.version.split('.')[0])" > "%TEMP%\pymajor.txt" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Failed to extract Python major version.
    type "%TEMP%\pymajor.txt"
    echo Python major version extraction failed >> "%SCRIPT_DIR%deploy_log.txt"
    goto :error
)
set /p PYTHON_MAJOR=<"%TEMP%\pymajor.txt"
echo Detected Python version: %PYTHON_MAJOR%
echo Python version: %PYTHON_MAJOR% >> "%SCRIPT_DIR%deploy_log.txt"

if %PYTHON_MAJOR% LSS 3 (
    echo Python version must be 3.8 or higher.
    echo Python version too low >> "%SCRIPT_DIR%deploy_log.txt"
    goto :error
)

:: Repository handling with better error checking
if exist "%SCRIPT_DIR%wiseflow\" (
    echo WiseFlow repository already exists.
    echo Repository exists >> "%SCRIPT_DIR%deploy_log.txt"
    
    :: Ask if user wants to update the repository
    choice /C YN /M "Do you want to update the repository?"
    if errorlevel 2 (
        echo Skipping repository update.
        echo Update skipped >> "%SCRIPT_DIR%deploy_log.txt"
    ) else (
        echo Updating WiseFlow repository...
        cd "%SCRIPT_DIR%wiseflow" || (
            echo Failed to change directory to wiseflow.
            echo CD to wiseflow failed >> "%SCRIPT_DIR%deploy_log.txt"
            goto :error
        )
        git pull
        if %ERRORLEVEL% NEQ 0 (
            echo Git pull failed. Continuing anyway...
            echo Git pull failed >> "%SCRIPT_DIR%deploy_log.txt"
        ) else (
            echo Repository updated successfully.
            echo Repository updated >> "%SCRIPT_DIR%deploy_log.txt"
        )
    )
) else (
    echo Cloning WiseFlow repository...
    git clone https://github.com/Zeeeepa/wiseflow.git "%SCRIPT_DIR%wiseflow"
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to clone repository.
        echo Clone failed >> "%SCRIPT_DIR%deploy_log.txt"
        goto :error
    )
    echo Repository cloned successfully.
    echo Repository cloned >> "%SCRIPT_DIR%deploy_log.txt"
)

:: Change to the wiseflow directory
cd "%SCRIPT_DIR%wiseflow" || (
    echo Failed to change directory to wiseflow.
    echo CD to wiseflow failed >> "%SCRIPT_DIR%deploy_log.txt"
    goto :error
)
echo Changed to wiseflow directory: %CD% >> "%SCRIPT_DIR%deploy_log.txt"

:: Install PocketBase if not already installed
if not exist "%SCRIPT_DIR%wiseflow\pb\pocketbase.exe" (
    echo Installing PocketBase...
    echo Installing PocketBase >> "%SCRIPT_DIR%deploy_log.txt"
    
    :: Check if PowerShell script exists
    if exist "%SCRIPT_DIR%wiseflow\install_pocketbase.ps1" (
        powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%wiseflow\install_pocketbase.ps1"
        if %ERRORLEVEL% NEQ 0 (
            echo Failed to install PocketBase.
            echo PocketBase installation failed >> "%SCRIPT_DIR%deploy_log.txt"
            goto :error
        )
    ) else (
        echo PocketBase installation script not found.
        echo PocketBase script missing >> "%SCRIPT_DIR%deploy_log.txt"
        goto :error
    )
)

:: Check if .env file exists in core directory, if not create it
if not exist "%SCRIPT_DIR%wiseflow\core\.env" (
    echo Creating .env file in core directory...
    echo Creating .env file >> "%SCRIPT_DIR%deploy_log.txt"
    
    :: Create core directory if it doesn't exist
    if not exist "%SCRIPT_DIR%wiseflow\core" (
        mkdir "%SCRIPT_DIR%wiseflow\core"
    )
    
    :: Create a basic .env file template
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
    ) > "%SCRIPT_DIR%wiseflow\core\.env"
    
    echo .env file created. Please edit it with your API keys and settings.
    echo .env file created >> "%SCRIPT_DIR%deploy_log.txt"
    
    echo Press any key to open the .env file for editing...
    pause >nul
    start notepad "%SCRIPT_DIR%wiseflow\core\.env"
    
    echo After configuring the .env file, press any key to continue...
    pause >nul
)

:: Virtual environment setup with better error handling
choice /C YN /M "Do you want to create a Python virtual environment?"
if errorlevel 2 (
    echo Skipping virtual environment creation.
    echo Skipping venv creation >> "%SCRIPT_DIR%deploy_log.txt"
) else (
    :: Check if conda is available
    where conda >nul 2>nul
    set CONDA_AVAILABLE=%ERRORLEVEL%
    
    if %CONDA_AVAILABLE% EQU 0 (
        echo Using Conda to create environment...
        echo Using Conda >> "%SCRIPT_DIR%deploy_log.txt"
        set PYTHON_VERSION=3.12
        if defined WISEFLOW_PYTHON_VERSION set PYTHON_VERSION=!WISEFLOW_PYTHON_VERSION!
        
        :: Check if conda environment already exists
        conda env list | findstr /C:"wiseflow" >nul
        if %ERRORLEVEL% NEQ 0 (
            echo Creating conda environment wiseflow with Python !PYTHON_VERSION!...
            conda create -n wiseflow python=!PYTHON_VERSION! -y
            if %ERRORLEVEL% NEQ 0 (
                echo Failed to create conda environment.
                echo Conda env creation failed >> "%SCRIPT_DIR%deploy_log.txt"
                goto :error
            )
            echo Conda environment created >> "%SCRIPT_DIR%deploy_log.txt"
        ) else (
            echo Conda environment 'wiseflow' already exists.
            echo Conda env exists >> "%SCRIPT_DIR%deploy_log.txt"
        )
        
        :: Activate conda environment
        echo Activating conda environment...
        call conda activate wiseflow
        if %ERRORLEVEL% NEQ 0 (
            echo Failed to activate conda environment. Continuing without it...
            echo Conda activation failed >> "%SCRIPT_DIR%deploy_log.txt"
        ) else (
            echo Conda environment activated >> "%SCRIPT_DIR%deploy_log.txt"
        )
    ) else (
        echo Conda not found. Using venv instead...
        echo Using venv >> "%SCRIPT_DIR%deploy_log.txt"
        if not exist "%SCRIPT_DIR%wiseflow\venv\" (
            echo Creating virtual environment...
            python -m venv "%SCRIPT_DIR%wiseflow\venv"
            if %ERRORLEVEL% NEQ 0 (
                echo Failed to create virtual environment.
                echo Venv creation failed >> "%SCRIPT_DIR%deploy_log.txt"
                goto :error
            )
            echo Virtual environment created >> "%SCRIPT_DIR%deploy_log.txt"
        ) else (
            echo Virtual environment already exists.
            echo Venv exists >> "%SCRIPT_DIR%deploy_log.txt"
        )
        
        :: Activate venv with error handling
        echo Activating virtual environment...
        if exist "%SCRIPT_DIR%wiseflow\venv\Scripts\activate.bat" (
            call "%SCRIPT_DIR%wiseflow\venv\Scripts\activate.bat"
            if %ERRORLEVEL% NEQ 0 (
                echo Failed to activate virtual environment. Continuing without it...
                echo Venv activation failed >> "%SCRIPT_DIR%deploy_log.txt"
            ) else (
                echo Virtual environment activated >> "%SCRIPT_DIR%deploy_log.txt"
            )
        ) else (
            echo Activation script not found. Continuing without virtual environment.
            echo Activation script missing >> "%SCRIPT_DIR%deploy_log.txt"
        )
    )
)

:: Install dependencies with better error handling
echo Installing Python dependencies...
echo Installing dependencies >> "%SCRIPT_DIR%deploy_log.txt"

:: Navigate to core directory
if exist "%SCRIPT_DIR%wiseflow\core" (
    cd "%SCRIPT_DIR%wiseflow\core" || (
        echo Failed to navigate to core directory.
        echo CD to core failed >> "%SCRIPT_DIR%deploy_log.txt"
        goto :error
    )
    echo Changed to core directory: %CD% >> "%SCRIPT_DIR%deploy_log.txt"
) else (
    echo Core directory not found.
    echo Core directory missing >> "%SCRIPT_DIR%deploy_log.txt"
    goto :error
)

:: Check if requirements.txt exists
if exist "%SCRIPT_DIR%wiseflow\core\requirements.txt" (
    pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to install Python dependencies.
        echo Pip install failed >> "%SCRIPT_DIR%deploy_log.txt"
        goto :error
    )
    echo Dependencies installed >> "%SCRIPT_DIR%deploy_log.txt"
) else (
    echo requirements.txt not found.
    echo requirements.txt missing >> "%SCRIPT_DIR%deploy_log.txt"
    goto :error
)

:: Install Playwright with error handling
echo Installing Playwright...
echo Installing Playwright >> "%SCRIPT_DIR%deploy_log.txt"
python -m playwright install --with-deps chromium
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install Playwright.
    echo Playwright installation failed >> "%SCRIPT_DIR%deploy_log.txt"
    goto :error
)
echo Playwright installed >> "%SCRIPT_DIR%deploy_log.txt"

:: Launch WiseFlow with better error handling
echo.
echo ===== WiseFlow Setup Complete =====
echo.
echo Starting WiseFlow...
echo Starting WiseFlow >> "%SCRIPT_DIR%deploy_log.txt"

:: Check for different possible entry points
if exist "%SCRIPT_DIR%wiseflow\core\windows_run.py" (
    echo Running windows_run.py...
    python windows_run.py
    set LAUNCH_RESULT=%ERRORLEVEL%
    echo Ran windows_run.py with result: !LAUNCH_RESULT! >> "%SCRIPT_DIR%deploy_log.txt"
) else if exist "%SCRIPT_DIR%wiseflow\core\app.py" (
    echo windows_run.py not found. Running app.py instead...
    python app.py
    set LAUNCH_RESULT=%ERRORLEVEL%
    echo Ran app.py with result: !LAUNCH_RESULT! >> "%SCRIPT_DIR%deploy_log.txt"
) else if exist "%SCRIPT_DIR%wiseflow\app.py" (
    echo Trying to run app.py from main directory...
    cd "%SCRIPT_DIR%wiseflow"
    python app.py
    set LAUNCH_RESULT=%ERRORLEVEL%
    echo Ran app.py from main directory with result: !LAUNCH_RESULT! >> "%SCRIPT_DIR%deploy_log.txt"
) else (
    echo Could not find any application entry point.
    echo No entry point found >> "%SCRIPT_DIR%deploy_log.txt"
    goto :error
)

:: Return to original directory
cd "%ORIGINAL_DIR%"
echo Returned to original directory >> "%SCRIPT_DIR%deploy_log.txt"

:: Keep the window open after completion
echo.
echo WiseFlow has been closed. Press any key to exit...
echo Deployment completed at %date% %time% >> "%SCRIPT_DIR%deploy_log.txt"
pause >nul

endlocal
exit /b 0

