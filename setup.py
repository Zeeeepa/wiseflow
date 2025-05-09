#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WiseFlow Setup and Deployment Script

This script provides a unified, cross-platform approach to setting up and deploying
the WiseFlow application. It handles:

1. Environment validation
2. Dependency installation
3. PocketBase setup
4. Configuration management
5. Application deployment

Usage:
    python setup.py [options]

Options:
    --install-deps        Install Python dependencies
    --setup-pocketbase    Install and configure PocketBase
    --configure           Create or update configuration
    --deploy              Deploy the application
    --all                 Perform all setup steps (default)
    --docker              Use Docker for deployment
    --native              Use native deployment
    --help                Show this help message
"""

import os
import sys
import json
import shutil
import platform
import subprocess
import argparse
import logging
import getpass
import re
import urllib.request
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('wiseflow_setup.log')
    ]
)
logger = logging.getLogger("wiseflow-setup")

# Constants
REQUIRED_PYTHON_VERSION = (3, 8)
POCKETBASE_LATEST_URL = "https://api.github.com/repos/pocketbase/pocketbase/releases/latest"
DEFAULT_CONFIG = {
    "PROJECT_DIR": "work_dir",
    "VERBOSE": "false",
    "LLM_API_BASE": "https://api.openai.com/v1",
    "LLM_API_KEY": "",
    "PRIMARY_MODEL": "gpt-4o",
    "SECONDARY_MODEL": "gpt-4o-mini",
    "VL_MODEL": "gpt-4o",
    "LLM_CONCURRENT_NUMBER": "4",
    "PB_API_BASE": "http://127.0.0.1:8090",
    "PB_API_AUTH": "",
    "ZHIPU_API_KEY": "",
    "CRAWLER_TIMEOUT": "60",
    "CRAWLER_MAX_DEPTH": "3",
    "CRAWLER_MAX_PAGES": "100",
    "MAX_CONCURRENT_TASKS": "4",
    "AUTO_SHUTDOWN_ENABLED": "false",
    "AUTO_SHUTDOWN_IDLE_TIME": "3600",
    "AUTO_SHUTDOWN_CHECK_INTERVAL": "300",
    "ENABLE_MULTIMODAL": "false",
    "ENABLE_KNOWLEDGE_GRAPH": "false",
    "ENABLE_INSIGHTS": "true",
    "ENABLE_REFERENCES": "true"
}

class SetupError(Exception):
    """Exception raised for errors during setup."""
    pass

def check_python_version() -> bool:
    """
    Check if the current Python version meets the requirements.
    
    Returns:
        bool: True if the Python version is sufficient, False otherwise
    """
    current_version = sys.version_info
    if current_version.major < REQUIRED_PYTHON_VERSION[0] or \
       (current_version.major == REQUIRED_PYTHON_VERSION[0] and 
        current_version.minor < REQUIRED_PYTHON_VERSION[1]):
        logger.error(f"Python {REQUIRED_PYTHON_VERSION[0]}.{REQUIRED_PYTHON_VERSION[1]} or higher is required")
        logger.error(f"Current Python version: {current_version.major}.{current_version.minor}.{current_version.micro}")
        return False
    logger.info(f"Python version check passed: {current_version.major}.{current_version.minor}.{current_version.micro}")
    return True

def check_dependencies() -> Dict[str, bool]:
    """
    Check if required external dependencies are installed.
    
    Returns:
        Dict[str, bool]: Dictionary of dependencies and their availability
    """
    dependencies = {
        "git": False,
        "docker": False,
        "docker-compose": False
    }
    
    # Check Git
    try:
        subprocess.run(["git", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        dependencies["git"] = True
        logger.info("Git is installed")
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.warning("Git is not installed or not in PATH")
    
    # Check Docker
    try:
        subprocess.run(["docker", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        dependencies["docker"] = True
        logger.info("Docker is installed")
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.warning("Docker is not installed or not in PATH")
    
    # Check Docker Compose
    try:
        # Try docker-compose command first (older versions)
        subprocess.run(["docker-compose", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        dependencies["docker-compose"] = True
        logger.info("Docker Compose is installed (standalone)")
    except (subprocess.SubprocessError, FileNotFoundError):
        try:
            # Try docker compose command (newer versions)
            subprocess.run(["docker", "compose", "version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            dependencies["docker-compose"] = True
            logger.info("Docker Compose is installed (Docker plugin)")
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("Docker Compose is not installed or not in PATH")
    
    return dependencies

def install_python_dependencies(venv: bool = True) -> bool:
    """
    Install Python dependencies.
    
    Args:
        venv: Whether to create and use a virtual environment
        
    Returns:
        bool: True if installation was successful, False otherwise
    """
    try:
        if venv:
            # Check if venv module is available
            try:
                import venv
                logger.info("Creating virtual environment...")
                venv_dir = Path("venv")
                if not venv_dir.exists():
                    venv.create(venv_dir, with_pip=True)
                    logger.info("Virtual environment created")
                else:
                    logger.info("Virtual environment already exists")
                
                # Activate virtual environment
                if platform.system() == "Windows":
                    pip_path = venv_dir / "Scripts" / "pip"
                else:
                    pip_path = venv_dir / "bin" / "pip"
            except ImportError:
                logger.warning("venv module not available, using system Python")
                pip_path = "pip"
        else:
            pip_path = "pip"
        
        # Install dependencies
        logger.info("Installing Python dependencies...")
        subprocess.run([str(pip_path), "install", "-r", "requirements.txt"], check=True)
        logger.info("Python dependencies installed successfully")
        
        # Install optional dependencies if requested
        if input("Install optional dependencies? (y/n): ").lower() == 'y':
            logger.info("Installing optional dependencies...")
            subprocess.run([str(pip_path), "install", "-r", "requirements-optional.txt"], check=True)
            logger.info("Optional dependencies installed successfully")
        
        return True
    except subprocess.SubprocessError as e:
        logger.error(f"Failed to install Python dependencies: {e}")
        return False

def download_pocketbase() -> Optional[Path]:
    """
    Download the latest version of PocketBase.
    
    Returns:
        Optional[Path]: Path to the downloaded PocketBase executable, or None if download failed
    """
    try:
        logger.info("Fetching latest PocketBase version...")
        with urllib.request.urlopen(POCKETBASE_LATEST_URL) as response:
            release_info = json.loads(response.read().decode('utf-8'))
            latest_version = release_info['tag_name']
            logger.info(f"Latest PocketBase version: {latest_version}")
        
        # Determine platform and architecture
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        if system == "windows":
            platform_name = "windows"
        elif system == "darwin":
            platform_name = "darwin"
        elif system == "linux":
            platform_name = "linux"
        else:
            raise SetupError(f"Unsupported operating system: {system}")
        
        if machine in ("x86_64", "amd64"):
            arch = "amd64"
        elif machine in ("arm64", "aarch64"):
            arch = "arm64"
        else:
            raise SetupError(f"Unsupported architecture: {machine}")
        
        # Construct download URL
        version_num = latest_version.lstrip('v')
        filename = f"pocketbase_{version_num}_{platform_name}_{arch}.zip"
        download_url = f"https://github.com/pocketbase/pocketbase/releases/download/{latest_version}/{filename}"
        
        # Create pb directory if it doesn't exist
        pb_dir = Path("pb")
        pb_dir.mkdir(exist_ok=True)
        
        # Download PocketBase
        logger.info(f"Downloading PocketBase from {download_url}...")
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            with urllib.request.urlopen(download_url) as response:
                temp_file.write(response.read())
        
        # Extract PocketBase
        logger.info("Extracting PocketBase...")
        with zipfile.ZipFile(temp_file.name, 'r') as zip_ref:
            zip_ref.extract("pocketbase", str(pb_dir))
        
        # Make executable
        pocketbase_path = pb_dir / "pocketbase"
        if system != "windows":
            os.chmod(pocketbase_path, 0o755)
        
        # Clean up
        os.unlink(temp_file.name)
        
        logger.info(f"PocketBase downloaded and extracted to {pocketbase_path}")
        return pocketbase_path
    except Exception as e:
        logger.error(f"Failed to download PocketBase: {e}")
        return None

def configure_pocketbase() -> bool:
    """
    Configure PocketBase with admin credentials.
    
    Returns:
        bool: True if configuration was successful, False otherwise
    """
    try:
        # Check if PocketBase is already installed
        pb_dir = Path("pb")
        if platform.system() == "Windows":
            pocketbase_path = pb_dir / "pocketbase.exe"
        else:
            pocketbase_path = pb_dir / "pocketbase"
        
        if not pocketbase_path.exists():
            logger.info("PocketBase not found, downloading...")
            pocketbase_path = download_pocketbase()
            if not pocketbase_path:
                return False
        
        # Get admin credentials
        print("\nPocketBase Admin Configuration")
        print("-----------------------------")
        admin_email = input("Admin email: ")
        while not re.match(r"[^@]+@[^@]+\.[^@]+", admin_email):
            print("Invalid email format. Please try again.")
            admin_email = input("Admin email: ")
        
        admin_password = getpass.getpass("Admin password (min 8 characters): ")
        while len(admin_password) < 8:
            print("Password must be at least 8 characters long. Please try again.")
            admin_password = getpass.getpass("Admin password (min 8 characters): ")
        
        # Create PocketBase admin user
        logger.info("Creating PocketBase admin user...")
        os.chdir(pb_dir)
        subprocess.run([
            "./pocketbase" if platform.system() != "Windows" else "pocketbase.exe",
            "migrate",
            "up"
        ], check=True)
        
        result = subprocess.run([
            "./pocketbase" if platform.system() != "Windows" else "pocketbase.exe",
            "--dev",
            "superuser",
            "create",
            admin_email,
            admin_password
        ], check=True)
        
        os.chdir("..")
        
        # Update .env file with admin credentials
        env_path = Path("core") / ".env"
        if not env_path.parent.exists():
            env_path.parent.mkdir(parents=True, exist_ok=True)
        
        if env_path.exists():
            # Read existing .env file
            with open(env_path, 'r') as f:
                env_content = f.read()
            
            # Update PB_API_AUTH
            env_content = re.sub(
                r'PB_API_AUTH="[^"]*"',
                f'PB_API_AUTH="{admin_email}|{admin_password}"',
                env_content
            )
            
            # Write updated .env file
            with open(env_path, 'w') as f:
                f.write(env_content)
        else:
            # Create new .env file
            with open(env_path, 'w') as f:
                f.write(f'PB_API_AUTH="{admin_email}|{admin_password}"\n')
        
        logger.info("PocketBase configured successfully")
        return True
    except subprocess.SubprocessError as e:
        logger.error(f"Failed to configure PocketBase: {e}")
        return False
    except Exception as e:
        logger.error(f"Error configuring PocketBase: {e}")
        return False

def configure_environment() -> bool:
    """
    Configure environment variables.
    
    Returns:
        bool: True if configuration was successful, False otherwise
    """
    try:
        # Create core directory if it doesn't exist
        core_dir = Path("core")
        core_dir.mkdir(exist_ok=True)
        
        # Check if .env file exists
        env_path = core_dir / ".env"
        env_vars = {}
        
        if env_path.exists():
            # Read existing .env file
            logger.info(f"Found existing .env file at {env_path}")
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip().strip('"')
        
        # Update with default values for missing keys
        for key, default_value in DEFAULT_CONFIG.items():
            if key not in env_vars:
                env_vars[key] = default_value
        
        # Prompt for required values
        print("\nEnvironment Configuration")
        print("-----------------------")
        print("Please provide values for the following configuration settings:")
        
        # LLM API Key
        if not env_vars.get("LLM_API_KEY"):
            env_vars["LLM_API_KEY"] = input("LLM API Key: ")
        
        # Primary Model
        if not env_vars.get("PRIMARY_MODEL") or env_vars.get("PRIMARY_MODEL") == "":
            env_vars["PRIMARY_MODEL"] = input("Primary LLM Model (default: gpt-4o): ") or "gpt-4o"
        
        # Project Directory
        project_dir = input(f"Project Directory (default: {env_vars.get('PROJECT_DIR')}): ")
        if project_dir:
            env_vars["PROJECT_DIR"] = project_dir
        
        # Create project directory if it doesn't exist
        os.makedirs(env_vars["PROJECT_DIR"], exist_ok=True)
        
        # Write .env file
        with open(env_path, 'w') as f:
            f.write("# WiseFlow Environment Configuration\n\n")
            
            # Group by categories
            categories = {
                "Project Settings": ["PROJECT_DIR", "VERBOSE"],
                "LLM Settings": ["LLM_API_BASE", "LLM_API_KEY", "PRIMARY_MODEL", "SECONDARY_MODEL", "VL_MODEL", "LLM_CONCURRENT_NUMBER"],
                "PocketBase Settings": ["PB_API_BASE", "PB_API_AUTH"],
                "Search Settings": ["ZHIPU_API_KEY"],
                "Crawler Settings": ["CRAWLER_TIMEOUT", "CRAWLER_MAX_DEPTH", "CRAWLER_MAX_PAGES"],
                "Task Settings": ["MAX_CONCURRENT_TASKS", "AUTO_SHUTDOWN_ENABLED", "AUTO_SHUTDOWN_IDLE_TIME", "AUTO_SHUTDOWN_CHECK_INTERVAL"],
                "Feature Flags": ["ENABLE_MULTIMODAL", "ENABLE_KNOWLEDGE_GRAPH", "ENABLE_INSIGHTS", "ENABLE_REFERENCES"]
            }
            
            for category, keys in categories.items():
                f.write(f"# {category}\n")
                for key in keys:
                    if key in env_vars:
                        # Quote string values
                        value = env_vars[key]
                        if not value.isdigit() and value.lower() not in ("true", "false"):
                            value = f'"{value}"'
                        f.write(f"{key}={value}\n")
                f.write("\n")
        
        logger.info(f"Environment configuration saved to {env_path}")
        return True
    except Exception as e:
        logger.error(f"Error configuring environment: {e}")
        return False

def deploy_docker() -> bool:
    """
    Deploy using Docker.
    
    Returns:
        bool: True if deployment was successful, False otherwise
    """
    try:
        logger.info("Deploying with Docker...")
        
        # Check if docker-compose.yml exists
        if not Path("docker-compose.yml").exists():
            logger.error("docker-compose.yml not found")
            return False
        
        # Check if .env file exists
        env_path = Path("core") / ".env"
        if not env_path.exists():
            logger.error(".env file not found in core directory")
            return False
        
        # Copy .env file to root directory for Docker Compose
        shutil.copy(env_path, ".env")
        
        # Run Docker Compose
        logger.info("Starting Docker containers...")
        try:
            # Try docker-compose command first (older versions)
            subprocess.run(["docker-compose", "up", "-d"], check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            # Try docker compose command (newer versions)
            subprocess.run(["docker", "compose", "up", "-d"], check=True)
        
        logger.info("Docker containers started successfully")
        logger.info("WiseFlow is now running at http://localhost:8090")
        return True
    except subprocess.SubprocessError as e:
        logger.error(f"Failed to deploy with Docker: {e}")
        return False
    except Exception as e:
        logger.error(f"Error deploying with Docker: {e}")
        return False

def deploy_native() -> bool:
    """
    Deploy natively.
    
    Returns:
        bool: True if deployment was successful, False otherwise
    """
    try:
        logger.info("Deploying natively...")
        
        # Check if PocketBase is installed
        pb_dir = Path("pb")
        if platform.system() == "Windows":
            pocketbase_path = pb_dir / "pocketbase.exe"
        else:
            pocketbase_path = pb_dir / "pocketbase"
        
        if not pocketbase_path.exists():
            logger.error("PocketBase not found. Please run setup with --setup-pocketbase first")
            return False
        
        # Check if .env file exists
        env_path = Path("core") / ".env"
        if not env_path.exists():
            logger.error(".env file not found in core directory")
            return False
        
        # Start PocketBase in background
        logger.info("Starting PocketBase...")
        if platform.system() == "Windows":
            # Use subprocess.Popen to start in background
            subprocess.Popen([
                str(pocketbase_path),
                "serve",
                "--http=127.0.0.1:8090"
            ], cwd=str(pb_dir), creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            # Use nohup to start in background
            subprocess.Popen([
                "nohup",
                str(pocketbase_path),
                "serve",
                "--http=127.0.0.1:8090",
                "&"
            ], cwd=str(pb_dir))
        
        logger.info("PocketBase started")
        
        # Start WiseFlow core
        logger.info("Starting WiseFlow core...")
        if platform.system() == "Windows":
            # Use subprocess.Popen to start in background
            subprocess.Popen([
                sys.executable,
                "run_task.py"
            ], cwd="core", creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            # Use nohup to start in background
            subprocess.Popen([
                "nohup",
                sys.executable,
                "run_task.py",
                "&"
            ], cwd="core")
        
        logger.info("WiseFlow core started")
        logger.info("WiseFlow is now running")
        return True
    except subprocess.SubprocessError as e:
        logger.error(f"Failed to deploy natively: {e}")
        return False
    except Exception as e:
        logger.error(f"Error deploying natively: {e}")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="WiseFlow Setup and Deployment")
    parser.add_argument("--install-deps", action="store_true", help="Install Python dependencies")
    parser.add_argument("--setup-pocketbase", action="store_true", help="Install and configure PocketBase")
    parser.add_argument("--configure", action="store_true", help="Create or update configuration")
    parser.add_argument("--deploy", action="store_true", help="Deploy the application")
    parser.add_argument("--all", action="store_true", help="Perform all setup steps (default)")
    parser.add_argument("--docker", action="store_true", help="Use Docker for deployment")
    parser.add_argument("--native", action="store_true", help="Use native deployment")
    
    args = parser.parse_args()
    
    # If no arguments provided, default to --all
    if not any(vars(args).values()):
        args.all = True
    
    # Check Python version
    if not check_python_version():
        logger.error("Python version check failed")
        return 1
    
    # Check dependencies
    dependencies = check_dependencies()
    
    # Determine deployment method
    if args.docker:
        deployment_method = "docker"
    elif args.native:
        deployment_method = "native"
    else:
        if dependencies["docker"] and dependencies["docker-compose"]:
            deployment_method = "docker"
        else:
            deployment_method = "native"
    
    logger.info(f"Using {deployment_method} deployment method")
    
    # Install Python dependencies
    if args.install_deps or args.all:
        if not install_python_dependencies():
            logger.error("Failed to install Python dependencies")
            return 1
    
    # Setup PocketBase
    if args.setup_pocketbase or args.all:
        if not configure_pocketbase():
            logger.error("Failed to configure PocketBase")
            return 1
    
    # Configure environment
    if args.configure or args.all:
        if not configure_environment():
            logger.error("Failed to configure environment")
            return 1
    
    # Deploy
    if args.deploy or args.all:
        if deployment_method == "docker":
            if not deploy_docker():
                logger.error("Failed to deploy with Docker")
                return 1
        else:
            if not deploy_native():
                logger.error("Failed to deploy natively")
                return 1
    
    logger.info("Setup completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())

