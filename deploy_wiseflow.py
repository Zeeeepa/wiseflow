#!/usr/bin/env python3
"""
WiseFlow Comprehensive Deployment Script

This script provides an interactive deployment process for WiseFlow:
1. Checks and installs all dependencies
2. Sets up databases
3. Configures environment variables
4. Allows selection of API endpoints
5. Launches the application

Usage:
    python deploy_wiseflow.py

Author: Codegen
"""

import os
import sys
import platform
import subprocess
import shutil
import json
import re
import time
import getpass
import urllib.request
import zipfile
import io
import tempfile
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Clear terminal screen
def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

# Print with color
def cprint(text: str, color: str, bold: bool = False, end: str = '\n'):
    """Print colored text to the terminal."""
    bold_code = Colors.BOLD if bold else ''
    print(f"{bold_code}{color}{text}{Colors.ENDC}", end=end)

# Print a section header
def print_header(text: str):
    """Print a section header."""
    print("\n" + "=" * 80)
    cprint(f" {text} ", Colors.HEADER, bold=True)
    print("=" * 80)

# Print a step
def print_step(step: int, total: int, text: str):
    """Print a step in the process."""
    cprint(f"[{step}/{total}] {text}", Colors.BLUE, bold=True)

# Print success message
def print_success(text: str):
    """Print a success message."""
    cprint(f"✓ {text}", Colors.GREEN)

# Print error message
def print_error(text: str):
    """Print an error message."""
    cprint(f"✗ {text}", Colors.RED, bold=True)

# Print warning message
def print_warning(text: str):
    """Print a warning message."""
    cprint(f"! {text}", Colors.YELLOW)

# Print info message
def print_info(text: str):
    """Print an info message."""
    cprint(f"ℹ {text}", Colors.CYAN)

# Run a command and return the output
def run_command(cmd: List[str], cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
    """Run a command and return the exit code, stdout, and stderr."""
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            env=env
        )
        stdout, stderr = process.communicate()
        return process.returncode, stdout, stderr
    except Exception as e:
        return 1, "", str(e)

# Check if a command exists
def command_exists(cmd: str) -> bool:
    """Check if a command exists in the system PATH."""
    return shutil.which(cmd) is not None

# Get user input with validation
def get_input(prompt: str, validator=None, default: Optional[str] = None, password: bool = False) -> str:
    """
    Get user input with validation.
    
    Args:
        prompt: The prompt to display to the user
        validator: A function that takes the input and returns True if valid
        default: Default value if user enters nothing
        password: Whether to hide the input (for passwords)
    
    Returns:
        The validated user input
    """
    while True:
        if default:
            display_prompt = f"{prompt} [{default}]: "
        else:
            display_prompt = f"{prompt}: "
        
        if password:
            user_input = getpass.getpass(display_prompt)
        else:
            user_input = input(display_prompt)
        
        if not user_input and default:
            user_input = default
        
        if not validator or validator(user_input):
            return user_input
        
        print_error("Invalid input. Please try again.")

# Validate email format
def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# Validate password
def validate_password(password: str) -> bool:
    """Validate password requirements."""
    if len(password) < 8:
        print_error("Password must be at least 8 characters long.")
        return False
    return True

# Validate API key format (basic check)
def validate_api_key(api_key: str) -> bool:
    """Validate API key format (basic check)."""
    if len(api_key) < 8:
        print_error("API key seems too short.")
        return False
    return True

# Check Python version
def check_python_version() -> bool:
    """Check if Python version is compatible."""
    print_step(1, 10, "Checking Python version...")
    
    major = sys.version_info.major
    minor = sys.version_info.minor
    
    if major < 3 or (major == 3 and minor < 8):
        print_error(f"Python 3.8+ is required. Found Python {major}.{minor}")
        return False
    
    print_success(f"Python {major}.{minor} detected (compatible)")
    return True

# Check and install required Python packages
def check_and_install_packages() -> bool:
    """Check and install required Python packages."""
    print_step(2, 10, "Checking and installing required Python packages...")
    
    # Core packages needed for the deployment script
    core_packages = [
        "requests",
        "python-dotenv",
        "tqdm"
    ]
    
    # Check if pip is available
    if not command_exists("pip") and not command_exists("pip3"):
        print_error("pip is not installed. Please install pip and try again.")
        return False
    
    pip_cmd = "pip3" if command_exists("pip3") else "pip"
    
    # Install core packages
    for package in core_packages:
        print_info(f"Checking {package}...")
        returncode, stdout, stderr = run_command([pip_cmd, "install", "--upgrade", package])
        if returncode != 0:
            print_error(f"Failed to install {package}: {stderr}")
            return False
    
    print_success("All core packages installed successfully")
    
    # Now we can import the packages we need
    global tqdm
    try:
        from tqdm import tqdm
    except ImportError:
        print_error("Failed to import tqdm. Please install it manually: pip install tqdm")
        return False
    
    return True

# Check and install Git
def check_git() -> bool:
    """Check if Git is installed."""
    print_step(3, 10, "Checking Git installation...")
    
    if not command_exists("git"):
        print_error("Git is not installed. Please install Git and try again.")
        print_info("Download Git from: https://git-scm.com/downloads")
        return False
    
    returncode, stdout, stderr = run_command(["git", "--version"])
    if returncode != 0:
        print_error(f"Git is installed but not working properly: {stderr}")
        return False
    
    print_success(f"Git {stdout.strip()} detected")
    return True

# Clone or update WiseFlow repository
def setup_repository() -> bool:
    """Clone or update WiseFlow repository."""
    print_step(4, 10, "Setting up WiseFlow repository...")
    
    repo_url = "https://github.com/Zeeeepa/wiseflow.git"
    repo_dir = os.path.join(os.getcwd(), "wiseflow")
    
    if os.path.exists(repo_dir):
        print_info("WiseFlow repository already exists. Checking for updates...")
        
        # Check if it's a git repository
        if not os.path.exists(os.path.join(repo_dir, ".git")):
            print_error(f"Directory {repo_dir} exists but is not a Git repository.")
            choice = get_input("Do you want to delete it and clone again? (y/n)", lambda x: x.lower() in ['y', 'n', 'yes', 'no'])
            if choice.lower() in ['y', 'yes']:
                try:
                    shutil.rmtree(repo_dir)
                except Exception as e:
                    print_error(f"Failed to delete directory: {e}")
                    return False
            else:
                return False
        else:
            # Update the repository
            returncode, stdout, stderr = run_command(["git", "pull"], cwd=repo_dir)
            if returncode != 0:
                print_error(f"Failed to update repository: {stderr}")
                return False
            
            print_success("Repository updated successfully")
            return True
    
    # Clone the repository
    print_info(f"Cloning WiseFlow repository from {repo_url}...")
    returncode, stdout, stderr = run_command(["git", "clone", repo_url, repo_dir])
    if returncode != 0:
        print_error(f"Failed to clone repository: {stderr}")
        return False
    
    print_success("Repository cloned successfully")
    return True

# Setup virtual environment
def setup_virtual_environment() -> Tuple[bool, Optional[str]]:
    """Setup Python virtual environment."""
    print_step(5, 10, "Setting up Python virtual environment...")
    
    repo_dir = os.path.join(os.getcwd(), "wiseflow")
    venv_dir = os.path.join(repo_dir, "venv")
    
    # Check if virtual environment already exists
    if os.path.exists(venv_dir):
        print_info("Virtual environment already exists.")
        choice = get_input("Do you want to recreate it? (y/n)", lambda x: x.lower() in ['y', 'n', 'yes', 'no'])
        if choice.lower() in ['y', 'yes']:
            try:
                shutil.rmtree(venv_dir)
            except Exception as e:
                print_error(f"Failed to delete virtual environment: {e}")
                return False, None
        else:
            # Activate the existing virtual environment
            if os.name == 'nt':  # Windows
                activate_script = os.path.join(venv_dir, "Scripts", "activate.bat")
                python_path = os.path.join(venv_dir, "Scripts", "python.exe")
            else:  # Unix-like
                activate_script = os.path.join(venv_dir, "bin", "activate")
                python_path = os.path.join(venv_dir, "bin", "python")
            
            print_info(f"Using existing virtual environment at {venv_dir}")
            return True, python_path
    
    # Create virtual environment
    print_info("Creating virtual environment...")
    returncode, stdout, stderr = run_command([sys.executable, "-m", "venv", venv_dir])
    if returncode != 0:
        print_error(f"Failed to create virtual environment: {stderr}")
        return False, None
    
    # Determine the path to the Python executable in the virtual environment
    if os.name == 'nt':  # Windows
        python_path = os.path.join(venv_dir, "Scripts", "python.exe")
    else:  # Unix-like
        python_path = os.path.join(venv_dir, "bin", "python")
    
    print_success(f"Virtual environment created at {venv_dir}")
    return True, python_path

# Install WiseFlow dependencies
def install_dependencies(python_path: str) -> bool:
    """Install WiseFlow dependencies."""
    print_step(6, 10, "Installing WiseFlow dependencies...")
    
    repo_dir = os.path.join(os.getcwd(), "wiseflow")
    requirements_file = os.path.join(repo_dir, "requirements.txt")
    
    if not os.path.exists(requirements_file):
        print_error(f"Requirements file not found: {requirements_file}")
        return False
    
    print_info("Installing dependencies from requirements.txt...")
    returncode, stdout, stderr = run_command([python_path, "-m", "pip", "install", "-r", requirements_file], cwd=repo_dir)
    if returncode != 0:
        print_error(f"Failed to install dependencies: {stderr}")
        return False
    
    # Install playwright dependencies if needed
    print_info("Installing Playwright dependencies...")
    returncode, stdout, stderr = run_command([python_path, "-m", "playwright", "install", "--with-deps", "chromium"], cwd=repo_dir)
    if returncode != 0:
        print_warning(f"Failed to install Playwright dependencies: {stderr}")
        print_warning("Some features requiring web browsing might not work properly.")
    
    print_success("Dependencies installed successfully")
    return True

# Setup PocketBase
def setup_pocketbase() -> bool:
    """Download and setup PocketBase."""
    print_step(7, 10, "Setting up PocketBase database...")
    
    repo_dir = os.path.join(os.getcwd(), "wiseflow")
    pb_dir = os.path.join(repo_dir, "pb")
    
    # Create PocketBase directory if it doesn't exist
    os.makedirs(pb_dir, exist_ok=True)
    
    # Check if PocketBase is already installed
    pb_executable = "pocketbase.exe" if os.name == 'nt' else "pocketbase"
    pb_path = os.path.join(pb_dir, pb_executable)
    
    if os.path.exists(pb_path):
        print_info("PocketBase is already installed.")
        choice = get_input("Do you want to reinstall it? (y/n)", lambda x: x.lower() in ['y', 'n', 'yes', 'no'])
        if choice.lower() not in ['y', 'yes']:
            return True
    
    # Determine the system and architecture
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    # Map architecture names
    arch_map = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }
    
    arch = arch_map.get(machine, machine)
    
    # Determine the download URL
    pb_version = "0.19.4"  # Latest stable version as of script creation
    
    if system == "windows":
        download_url = f"https://github.com/pocketbase/pocketbase/releases/download/v{pb_version}/pocketbase_{pb_version}_windows_amd64.zip"
    elif system == "darwin":  # macOS
        download_url = f"https://github.com/pocketbase/pocketbase/releases/download/v{pb_version}/pocketbase_{pb_version}_darwin_{arch}.zip"
    elif system == "linux":
        download_url = f"https://github.com/pocketbase/pocketbase/releases/download/v{pb_version}/pocketbase_{pb_version}_linux_{arch}.zip"
    else:
        print_error(f"Unsupported system: {system}")
        return False
    
    # Download PocketBase
    print_info(f"Downloading PocketBase v{pb_version} from {download_url}...")
    
    try:
        with urllib.request.urlopen(download_url) as response:
            with zipfile.ZipFile(io.BytesIO(response.read())) as zip_file:
                zip_file.extractall(pb_dir)
        
        # Make the executable file executable on Unix-like systems
        if system != "windows":
            os.chmod(pb_path, 0o755)
        
        print_success("PocketBase downloaded and extracted successfully")
        return True
    except Exception as e:
        print_error(f"Failed to download PocketBase: {e}")
        return False

# Configure PocketBase admin account
def configure_pocketbase_admin() -> Tuple[bool, str, str]:
    """Configure PocketBase admin account."""
    print_step(8, 10, "Configuring PocketBase admin account...")
    
    # Get admin email and password
    admin_email = get_input(
        "Enter admin email",
        validate_email,
        default="admin@example.com"
    )
    
    admin_password = get_input(
        "Enter admin password (min 8 characters)",
        validate_password,
        password=True
    )
    
    # Confirm password
    confirm_password = get_input(
        "Confirm admin password",
        lambda x: x == admin_password,
        password=True
    )
    
    if admin_password != confirm_password:
        print_error("Passwords do not match.")
        return False, "", ""
    
    repo_dir = os.path.join(os.getcwd(), "wiseflow")
    pb_dir = os.path.join(repo_dir, "pb")
    pb_executable = "pocketbase.exe" if os.name == 'nt' else "pocketbase"
    pb_path = os.path.join(pb_dir, pb_executable)
    
    # Initialize PocketBase database
    print_info("Initializing PocketBase database...")
    returncode, stdout, stderr = run_command([pb_path, "migrate", "up"], cwd=pb_dir)
    if returncode != 0:
        print_error(f"Failed to initialize PocketBase database: {stderr}")
        return False, "", ""
    
    # Create admin user
    print_info("Creating admin user...")
    returncode, stdout, stderr = run_command(
        [pb_path, "--dev", "superuser", "create", admin_email, admin_password],
        cwd=pb_dir
    )
    if returncode != 0:
        print_error(f"Failed to create admin user: {stderr}")
        return False, "", ""
    
    print_success("PocketBase admin account configured successfully")
    return True, admin_email, admin_password

# Configure environment variables
def configure_environment(admin_email: str, admin_password: str) -> bool:
    """Configure environment variables."""
    print_step(9, 10, "Configuring environment variables...")
    
    repo_dir = os.path.join(os.getcwd(), "wiseflow")
    env_example_path = os.path.join(repo_dir, ".env.example")
    env_path = os.path.join(repo_dir, ".env")
    
    # Check if .env.example exists
    if not os.path.exists(env_example_path):
        print_error(f".env.example file not found: {env_example_path}")
        return False
    
    # Read .env.example
    with open(env_example_path, 'r') as f:
        env_content = f.read()
    
    # Get LLM API settings
    print_info("\nLLM API Configuration:")
    
    # Select LLM provider
    llm_providers = {
        "1": {
            "name": "OpenAI",
            "base_url": "https://api.openai.com/v1",
            "models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]
        },
        "2": {
            "name": "Anthropic",
            "base_url": "https://api.anthropic.com/v1",
            "models": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]
        },
        "3": {
            "name": "Custom",
            "base_url": "",
            "models": []
        }
    }
    
    print_info("Available LLM providers:")
    for key, provider in llm_providers.items():
        print(f"{key}. {provider['name']}")
    
    provider_choice = get_input(
        "Select LLM provider (1-3)",
        lambda x: x in llm_providers.keys(),
        default="1"
    )
    
    selected_provider = llm_providers[provider_choice]
    
    if provider_choice == "3":  # Custom provider
        base_url = get_input("Enter API base URL", lambda x: x.startswith("http"))
        primary_model = get_input("Enter primary model name")
        secondary_model = get_input("Enter secondary model name", default=primary_model)
        vl_model = get_input("Enter vision model name", default=primary_model)
    else:
        base_url = selected_provider["base_url"]
        
        print_info(f"\nAvailable models for {selected_provider['name']}:")
        for i, model in enumerate(selected_provider["models"], 1):
            print(f"{i}. {model}")
        
        model_choice = get_input(
            "Select primary model",
            lambda x: x.isdigit() and 1 <= int(x) <= len(selected_provider["models"]),
            default="1"
        )
        primary_model = selected_provider["models"][int(model_choice) - 1]
        
        model_choice = get_input(
            "Select secondary model",
            lambda x: x.isdigit() and 1 <= int(x) <= len(selected_provider["models"]),
            default=model_choice
        )
        secondary_model = selected_provider["models"][int(model_choice) - 1]
        
        # For vision model, use the same as primary if available
        vl_model = primary_model
    
    api_key = get_input(
        f"Enter {selected_provider['name']} API key",
        validate_api_key,
        password=True
    )
    
    # Get ZhiPu API key (for search)
    zhipu_api_key = get_input(
        "Enter ZhiPu API key (for search, leave empty to skip)",
        lambda x: True
    )
    
    # Update environment variables
    env_content = re.sub(r'LLM_API_BASE="[^"]*"', f'LLM_API_BASE="{base_url}"', env_content)
    env_content = re.sub(r'LLM_API_KEY="[^"]*"', f'LLM_API_KEY="{api_key}"', env_content)
    env_content = re.sub(r'PRIMARY_MODEL="[^"]*"', f'PRIMARY_MODEL="{primary_model}"', env_content)
    env_content = re.sub(r'SECONDARY_MODEL="[^"]*"', f'SECONDARY_MODEL="{secondary_model}"', env_content)
    env_content = re.sub(r'VL_MODEL="[^"]*"', f'VL_MODEL="{vl_model}"', env_content)
    
    # Update PocketBase auth
    env_content = re.sub(
        r'PB_API_AUTH="[^"]*"',
        f'PB_API_AUTH="{admin_email}|{admin_password}"',
        env_content
    )
    
    # Update ZhiPu API key if provided
    if zhipu_api_key:
        env_content = re.sub(
            r'ZHIPU_API_KEY="[^"]*"',
            f'ZHIPU_API_KEY="{zhipu_api_key}"',
            env_content
        )
    
    # Write .env file
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print_success("Environment variables configured successfully")
    return True

# Launch WiseFlow
def launch_wiseflow(python_path: str) -> bool:
    """Launch WiseFlow."""
    print_step(10, 10, "Launching WiseFlow...")
    
    repo_dir = os.path.join(os.getcwd(), "wiseflow")
    wiseflow_script = os.path.join(repo_dir, "wiseflow.py")
    
    if not os.path.exists(wiseflow_script):
        print_error(f"WiseFlow script not found: {wiseflow_script}")
        return False
    
    # Make the script executable on Unix-like systems
    if os.name != 'nt':
        os.chmod(wiseflow_script, 0o755)
    
    # Launch options
    print_info("\nLaunch options:")
    
    open_browser = get_input(
        "Open dashboard in browser when ready? (y/n)",
        lambda x: x.lower() in ['y', 'n', 'yes', 'no'],
        default="y"
    ).lower() in ['y', 'yes']
    
    # Prepare command
    cmd = [python_path, wiseflow_script]
    
    if not open_browser:
        cmd.append("--no-browser")
    
    # Launch WiseFlow
    print_info("Starting WiseFlow...")
    print_info("Press Ctrl+C to stop.")
    
    try:
        # Use subprocess.Popen to run the command in the background
        process = subprocess.Popen(
            cmd,
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Print the first few lines of output
        for _ in range(10):
            line = process.stdout.readline()
            if not line:
                break
            print(line.strip())
        
        print_success("WiseFlow started successfully!")
        print_info("The application is now running in the background.")
        
        # Show URLs
        print_info("\nAccess WiseFlow at:")
        print_info("- Dashboard: http://localhost:8080")
        print_info("- API: http://localhost:8000")
        print_info("- PocketBase Admin: http://localhost:8090/_/")
        
        return True
    except KeyboardInterrupt:
        print_info("\nLaunch interrupted by user.")
        return False
    except Exception as e:
        print_error(f"Failed to launch WiseFlow: {e}")
        return False

# Main function
def main():
    """Main function."""
    clear_screen()
    
    print_header("WiseFlow Comprehensive Deployment")
    print_info("This script will guide you through the deployment of WiseFlow.")
    print_info("It will check dependencies, set up databases, and configure the application.")
    print()
    
    # Check Python version
    if not check_python_version():
        return 1
    
    # Check and install required packages
    if not check_and_install_packages():
        return 1
    
    # Check Git
    if not check_git():
        return 1
    
    # Setup repository
    if not setup_repository():
        return 1
    
    # Setup virtual environment
    success, python_path = setup_virtual_environment()
    if not success or not python_path:
        return 1
    
    # Install dependencies
    if not install_dependencies(python_path):
        return 1
    
    # Setup PocketBase
    if not setup_pocketbase():
        return 1
    
    # Configure PocketBase admin account
    success, admin_email, admin_password = configure_pocketbase_admin()
    if not success:
        return 1
    
    # Configure environment variables
    if not configure_environment(admin_email, admin_password):
        return 1
    
    # Launch WiseFlow
    if not launch_wiseflow(python_path):
        return 1
    
    print_header("WiseFlow Deployment Complete")
    print_success("WiseFlow has been successfully deployed and is now running!")
    print_info("You can access the dashboard at: http://localhost:8080")
    print_info("To stop WiseFlow, press Ctrl+C in the terminal where it's running.")
    print()
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print_info("\nDeployment interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")
        sys.exit(1)

