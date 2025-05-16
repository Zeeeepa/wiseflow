#!/usr/bin/env python3
"""
WiseFlow Unified Launcher

This script provides a single entry point to launch all WiseFlow components:
- PocketBase database (if needed)
- API Server
- Task Processor
- Dashboard

Usage:
    python wiseflow.py [--no-db] [--no-api] [--no-task] [--no-dashboard]
"""

import os
import sys
import time
import argparse
import subprocess
import signal
import threading
import logging
import webbrowser
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("wiseflow-launcher")

# Load environment variables
load_dotenv()

# Global variables to track processes
processes = {}
stop_event = threading.Event()

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="WiseFlow Unified Launcher")
    parser.add_argument("--no-db", action="store_true", help="Don't start the PocketBase database")
    parser.add_argument("--no-api", action="store_true", help="Don't start the API server")
    parser.add_argument("--no-task", action="store_true", help="Don't start the task processor")
    parser.add_argument("--no-dashboard", action="store_true", help="Don't start the dashboard")
    parser.add_argument("--no-browser", action="store_true", help="Don't open the dashboard in a browser")
    parser.add_argument("--env-file", type=str, default=".env", help="Path to the environment file")
    
    return parser.parse_args()

def load_environment(env_file):
    """Load environment variables from the specified file."""
    if not os.path.exists(env_file):
        logger.warning(f"Environment file {env_file} not found. Using default environment variables.")
        return
    
    load_dotenv(env_file)
    logger.info(f"Loaded environment variables from {env_file}")

def check_pocketbase():
    """Check if PocketBase is installed and available."""
    try:
        # Check if PocketBase directory exists
        pb_dir = Path("pb")
        if not pb_dir.exists():
            pb_dir.mkdir(exist_ok=True)
            logger.info("Created PocketBase directory")
        
        # Check if PocketBase executable exists
        pb_executable = pb_dir / "pocketbase"
        if not pb_executable.exists():
            logger.warning("PocketBase executable not found. Will attempt to download it.")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error checking PocketBase: {e}")
        return False

def download_pocketbase():
    """Download PocketBase if not available."""
    import platform
    import requests
    import zipfile
    import io
    
    system = platform.system().lower()
    arch = platform.machine().lower()
    
    # Map architecture names
    arch_map = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }
    
    if arch in arch_map:
        arch = arch_map[arch]
    else:
        logger.error(f"Unsupported architecture: {arch}")
        return False
    
    # Determine the download URL based on the system and architecture
    if system == "linux":
        url = f"https://github.com/pocketbase/pocketbase/releases/download/v0.19.4/pocketbase_0.19.4_linux_{arch}.zip"
    elif system == "darwin":
        url = f"https://github.com/pocketbase/pocketbase/releases/download/v0.19.4/pocketbase_0.19.4_darwin_{arch}.zip"
    elif system == "windows":
        url = "https://github.com/pocketbase/pocketbase/releases/download/v0.19.4/pocketbase_0.19.4_windows_amd64.zip"
    else:
        logger.error(f"Unsupported system: {system}")
        return False
    
    try:
        logger.info(f"Downloading PocketBase from {url}")
        response = requests.get(url)
        response.raise_for_status()
        
        # Extract the zip file
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            zip_file.extractall("pb")
        
        # Make the executable file executable on Unix-like systems
        if system != "windows":
            pb_executable = Path("pb") / "pocketbase"
            pb_executable.chmod(0o755)
        
        logger.info("PocketBase downloaded and extracted successfully")
        return True
    except Exception as e:
        logger.error(f"Error downloading PocketBase: {e}")
        return False

def start_pocketbase():
    """Start the PocketBase database."""
    try:
        # Get PocketBase credentials from environment variables
        pb_email = os.environ.get("PB_SUPERUSER_EMAIL", "admin@example.com")
        pb_password = os.environ.get("PB_SUPERUSER_PASSWORD", "adminpassword")
        
        # Determine the PocketBase executable path
        system = platform.system().lower()
        if system == "windows":
            pb_executable = str(Path("pb") / "pocketbase.exe")
        else:
            pb_executable = str(Path("pb") / "pocketbase")
        
        # Create the command
        cmd = [
            pb_executable,
            "serve",
            "--http=0.0.0.0:8090",
            "--dir=./pb/pb_data"
        ]
        
        # Start PocketBase
        logger.info("Starting PocketBase...")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        processes["pocketbase"] = process
        
        # Start a thread to monitor the process output
        threading.Thread(
            target=monitor_process_output,
            args=(process, "pocketbase"),
            daemon=True
        ).start()
        
        # Wait for PocketBase to start
        time.sleep(2)
        
        # Check if PocketBase is running
        if process.poll() is not None:
            logger.error("PocketBase failed to start")
            return False
        
        logger.info("PocketBase started successfully")
        return True
    except Exception as e:
        logger.error(f"Error starting PocketBase: {e}")
        return False

def start_api_server():
    """Start the API server."""
    try:
        # Get API server settings from environment variables
        api_host = os.environ.get("API_HOST", "0.0.0.0")
        api_port = os.environ.get("API_PORT", "8000")
        
        # Create the command
        cmd = [
            sys.executable,
            "api_server.py"
        ]
        
        # Start the API server
        logger.info("Starting API server...")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        processes["api_server"] = process
        
        # Start a thread to monitor the process output
        threading.Thread(
            target=monitor_process_output,
            args=(process, "api_server"),
            daemon=True
        ).start()
        
        # Wait for the API server to start
        time.sleep(2)
        
        # Check if the API server is running
        if process.poll() is not None:
            logger.error("API server failed to start")
            return False
        
        logger.info(f"API server started successfully at http://{api_host}:{api_port}")
        return True
    except Exception as e:
        logger.error(f"Error starting API server: {e}")
        return False

def start_task_processor():
    """Start the task processor."""
    try:
        # Create the command
        cmd = [
            sys.executable,
            "core/run_task.py"
        ]
        
        # Start the task processor
        logger.info("Starting task processor...")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        processes["task_processor"] = process
        
        # Start a thread to monitor the process output
        threading.Thread(
            target=monitor_process_output,
            args=(process, "task_processor"),
            daemon=True
        ).start()
        
        # Wait for the task processor to start
        time.sleep(2)
        
        # Check if the task processor is running
        if process.poll() is not None:
            logger.error("Task processor failed to start")
            return False
        
        logger.info("Task processor started successfully")
        return True
    except Exception as e:
        logger.error(f"Error starting task processor: {e}")
        return False

def start_dashboard():
    """Start the dashboard."""
    try:
        # Get dashboard settings from environment variables
        dashboard_host = os.environ.get("DASHBOARD_HOST", "0.0.0.0")
        dashboard_port = os.environ.get("DASHBOARD_PORT", "8080")
        
        # Create the command
        cmd = [
            sys.executable,
            "dashboard/main.py"
        ]
        
        # Start the dashboard
        logger.info("Starting dashboard...")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        processes["dashboard"] = process
        
        # Start a thread to monitor the process output
        threading.Thread(
            target=monitor_process_output,
            args=(process, "dashboard"),
            daemon=True
        ).start()
        
        # Wait for the dashboard to start
        time.sleep(2)
        
        # Check if the dashboard is running
        if process.poll() is not None:
            logger.error("Dashboard failed to start")
            return False
        
        logger.info(f"Dashboard started successfully at http://{dashboard_host}:{dashboard_port}")
        return True
    except Exception as e:
        logger.error(f"Error starting dashboard: {e}")
        return False

def monitor_process_output(process, name):
    """Monitor the output of a process and log it."""
    while not stop_event.is_set() and process.poll() is None:
        try:
            # Read stdout
            stdout_line = process.stdout.readline()
            if stdout_line:
                logger.info(f"[{name}] {stdout_line.strip()}")
            
            # Read stderr
            stderr_line = process.stderr.readline()
            if stderr_line:
                logger.error(f"[{name}] {stderr_line.strip()}")
            
            # If both stdout and stderr are empty, the process might have ended
            if not stdout_line and not stderr_line:
                if process.poll() is not None:
                    break
                time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error monitoring {name} output: {e}")
            break
    
    # Check if the process has ended
    if process.poll() is not None:
        logger.warning(f"{name} process has ended with return code {process.returncode}")

def open_dashboard_in_browser():
    """Open the dashboard in a web browser."""
    try:
        # Get dashboard URL from environment variables
        dashboard_host = os.environ.get("DASHBOARD_HOST", "0.0.0.0")
        dashboard_port = os.environ.get("DASHBOARD_PORT", "8080")
        
        # Replace 0.0.0.0 with localhost for browser access
        if dashboard_host == "0.0.0.0":
            dashboard_host = "localhost"
        
        dashboard_url = f"http://{dashboard_host}:{dashboard_port}"
        
        # Wait a moment for the dashboard to fully initialize
        time.sleep(5)
        
        # Open the dashboard in a web browser
        logger.info(f"Opening dashboard in web browser: {dashboard_url}")
        webbrowser.open(dashboard_url)
    except Exception as e:
        logger.error(f"Error opening dashboard in browser: {e}")

def handle_signal(signum, frame):
    """Handle termination signals."""
    logger.info(f"Received signal {signum}. Shutting down...")
    stop_all_processes()
    sys.exit(0)

def stop_all_processes():
    """Stop all running processes."""
    logger.info("Stopping all processes...")
    stop_event.set()
    
    # Stop processes in reverse order
    for name in reversed(list(processes.keys())):
        process = processes.get(name)
        if process and process.poll() is None:
            logger.info(f"Stopping {name}...")
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"{name} did not terminate gracefully, killing...")
                process.kill()
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
    
    logger.info("All processes stopped")

def main():
    """Main entry point."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Load environment variables
    load_environment(args.env_file)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    try:
        # Create project directory if it doesn't exist
        project_dir = os.environ.get("PROJECT_DIR", "work_dir")
        os.makedirs(project_dir, exist_ok=True)
        
        # Start PocketBase if needed
        if not args.no_db:
            if not check_pocketbase():
                if not download_pocketbase():
                    logger.error("Failed to download PocketBase. Please install it manually.")
                    return 1
            
            if not start_pocketbase():
                logger.error("Failed to start PocketBase")
                return 1
        
        # Start API server if needed
        if not args.no_api:
            if not start_api_server():
                logger.error("Failed to start API server")
                return 1
        
        # Start task processor if needed
        if not args.no_task:
            if not start_task_processor():
                logger.error("Failed to start task processor")
                return 1
        
        # Start dashboard if needed
        if not args.no_dashboard:
            if not start_dashboard():
                logger.error("Failed to start dashboard")
                return 1
            
            # Open dashboard in browser if requested
            if not args.no_browser:
                threading.Thread(
                    target=open_dashboard_in_browser,
                    daemon=True
                ).start()
        
        logger.info("WiseFlow started successfully")
        logger.info("Press Ctrl+C to stop")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
            # Check if any process has ended unexpectedly
            for name, process in list(processes.items()):
                if process.poll() is not None:
                    logger.error(f"{name} process has ended unexpectedly with return code {process.returncode}")
                    
                    # Remove the process from the list
                    del processes[name]
                    
                    # If all processes have ended, exit
                    if not processes:
                        logger.error("All processes have ended. Exiting...")
                        return 1
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
    finally:
        stop_all_processes()
    
    return 0

if __name__ == "__main__":
    import platform
    sys.exit(main())

