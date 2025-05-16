#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WiseFlow Deployment Script

This script provides a unified, cross-platform approach to deploying the WiseFlow application.
It supports both Docker and native deployment methods.

Usage:
    python deploy.py [options]

Options:
    --docker             Use Docker for deployment (default if Docker is available)
    --native             Use native deployment
    --start              Start the application
    --stop               Stop the application
    --restart            Restart the application
    --status             Check the status of the application
    --logs               View application logs
    --update             Update the application
    --help               Show this help message
"""

import os
import sys
import json
import shutil
import platform
import subprocess
import argparse
import logging
import time
import signal
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('wiseflow_deploy.log')
    ]
)
logger = logging.getLogger("wiseflow-deploy")

class DeployError(Exception):
    """Exception raised for errors during deployment."""
    pass

def check_dependencies() -> Dict[str, bool]:
    """
    Check if required external dependencies are installed.
    
    Returns:
        Dict[str, bool]: Dictionary of dependencies and their availability
    """
    dependencies = {
        "docker": False,
        "docker-compose": False
    }
    
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

def run_docker_compose(command: List[str]) -> bool:
    """
    Run a Docker Compose command.
    
    Args:
        command: Docker Compose command to run
        
    Returns:
        bool: True if the command was successful, False otherwise
    """
    try:
        try:
            # Try docker-compose command first (older versions)
            subprocess.run(["docker-compose"] + command, check=True)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            # Try docker compose command (newer versions)
            subprocess.run(["docker", "compose"] + command, check=True)
            return True
    except subprocess.SubprocessError as e:
        logger.error(f"Docker Compose command failed: {e}")
        return False

def start_docker() -> bool:
    """
    Start the application using Docker.
    
    Returns:
        bool: True if startup was successful, False otherwise
    """
    try:
        logger.info("Starting WiseFlow with Docker...")
        
        # Check if docker-compose.yml exists
        if not Path("docker-compose.yml").exists():
            logger.error("docker-compose.yml not found")
            return False
        
        # Check if .env file exists in core directory
        core_env_path = Path("core") / ".env"
        if not core_env_path.exists():
            logger.error(".env file not found in core directory")
            return False
        
        # Copy .env file to root directory for Docker Compose if it doesn't exist
        root_env_path = Path(".env")
        if not root_env_path.exists():
            shutil.copy(core_env_path, root_env_path)
            logger.info("Copied .env file from core directory to root directory")
        
        # Start Docker containers
        if not run_docker_compose(["up", "-d"]):
            return False
        
        logger.info("WiseFlow started successfully with Docker")
        return True
    except Exception as e:
        logger.error(f"Error starting WiseFlow with Docker: {e}")
        return False

def stop_docker() -> bool:
    """
    Stop the application using Docker.
    
    Returns:
        bool: True if shutdown was successful, False otherwise
    """
    try:
        logger.info("Stopping WiseFlow with Docker...")
        
        # Stop Docker containers
        if not run_docker_compose(["down"]):
            return False
        
        logger.info("WiseFlow stopped successfully with Docker")
        return True
    except Exception as e:
        logger.error(f"Error stopping WiseFlow with Docker: {e}")
        return False

def restart_docker() -> bool:
    """
    Restart the application using Docker.
    
    Returns:
        bool: True if restart was successful, False otherwise
    """
    try:
        logger.info("Restarting WiseFlow with Docker...")
        
        # Restart Docker containers
        if not run_docker_compose(["restart"]):
            return False
        
        logger.info("WiseFlow restarted successfully with Docker")
        return True
    except Exception as e:
        logger.error(f"Error restarting WiseFlow with Docker: {e}")
        return False

def status_docker() -> bool:
    """
    Check the status of the application using Docker.
    
    Returns:
        bool: True if status check was successful, False otherwise
    """
    try:
        logger.info("Checking WiseFlow status with Docker...")
        
        # Check Docker container status
        subprocess.run(["docker-compose", "ps"], check=False)
        
        return True
    except Exception as e:
        logger.error(f"Error checking WiseFlow status with Docker: {e}")
        return False

def logs_docker() -> bool:
    """
    View application logs using Docker.
    
    Returns:
        bool: True if log retrieval was successful, False otherwise
    """
    try:
        logger.info("Viewing WiseFlow logs with Docker...")
        
        # View Docker container logs
        subprocess.run(["docker-compose", "logs"], check=False)
        
        return True
    except Exception as e:
        logger.error(f"Error viewing WiseFlow logs with Docker: {e}")
        return False

def update_docker() -> bool:
    """
    Update the application using Docker.
    
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        logger.info("Updating WiseFlow with Docker...")
        
        # Pull latest images
        if not run_docker_compose(["pull"]):
            return False
        
        # Restart containers with new images
        if not run_docker_compose(["up", "-d"]):
            return False
        
        logger.info("WiseFlow updated successfully with Docker")
        return True
    except Exception as e:
        logger.error(f"Error updating WiseFlow with Docker: {e}")
        return False

def find_process(name: str) -> List[int]:
    """
    Find process IDs by name.
    
    Args:
        name: Process name to find
        
    Returns:
        List[int]: List of process IDs
    """
    pids = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Check if the process name matches
            if name in proc.info['name']:
                pids.append(proc.info['pid'])
            # Check if the process command line contains the name
            elif proc.info['cmdline'] and any(name in cmd for cmd in proc.info['cmdline']):
                pids.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return pids

def start_native() -> bool:
    """
    Start the application natively.
    
    Returns:
        bool: True if startup was successful, False otherwise
    """
    try:
        logger.info("Starting WiseFlow natively...")
        
        # Check if PocketBase is installed
        pb_dir = Path("pb")
        if platform.system() == "Windows":
            pocketbase_path = pb_dir / "pocketbase.exe"
        else:
            pocketbase_path = pb_dir / "pocketbase"
        
        if not pocketbase_path.exists():
            logger.error("PocketBase not found. Please run setup.py with --setup-pocketbase first")
            return False
        
        # Check if .env file exists
        env_path = Path("core") / ".env"
        if not env_path.exists():
            logger.error(".env file not found in core directory")
            return False
        
        # Check if PocketBase is already running
        pocketbase_pids = find_process("pocketbase")
        if pocketbase_pids:
            logger.info("PocketBase is already running")
        else:
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
                with open(pb_dir / "pocketbase.log", "a") as log_file:
                    subprocess.Popen([
                        str(pocketbase_path),
                        "serve",
                        "--http=127.0.0.1:8090"
                    ], cwd=str(pb_dir), stdout=log_file, stderr=log_file,
                    start_new_session=True)
            
            logger.info("PocketBase started")
        
        # Check if WiseFlow core is already running
        wiseflow_pids = find_process("run_task.py")
        if wiseflow_pids:
            logger.info("WiseFlow core is already running")
        else:
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
                with open("core/wiseflow.log", "a") as log_file:
                    subprocess.Popen([
                        sys.executable,
                        "run_task.py"
                    ], cwd="core", stdout=log_file, stderr=log_file,
                    start_new_session=True)
            
            logger.info("WiseFlow core started")
        
        logger.info("WiseFlow is now running")
        return True
    except Exception as e:
        logger.error(f"Error starting WiseFlow natively: {e}")
        return False

def stop_native() -> bool:
    """
    Stop the application natively.
    
    Returns:
        bool: True if shutdown was successful, False otherwise
    """
    try:
        logger.info("Stopping WiseFlow natively...")
        
        # Find and stop WiseFlow core processes
        wiseflow_pids = find_process("run_task.py")
        for pid in wiseflow_pids:
            try:
                os.kill(pid, signal.SIGTERM)
                logger.info(f"Sent SIGTERM to WiseFlow core process {pid}")
            except OSError as e:
                logger.error(f"Failed to terminate WiseFlow core process {pid}: {e}")
        
        # Find and stop PocketBase processes
        pocketbase_pids = find_process("pocketbase")
        for pid in pocketbase_pids:
            try:
                os.kill(pid, signal.SIGTERM)
                logger.info(f"Sent SIGTERM to PocketBase process {pid}")
            except OSError as e:
                logger.error(f"Failed to terminate PocketBase process {pid}: {e}")
        
        logger.info("WiseFlow stopped successfully")
        return True
    except Exception as e:
        logger.error(f"Error stopping WiseFlow natively: {e}")
        return False

def restart_native() -> bool:
    """
    Restart the application natively.
    
    Returns:
        bool: True if restart was successful, False otherwise
    """
    try:
        logger.info("Restarting WiseFlow natively...")
        
        # Stop the application
        if not stop_native():
            logger.warning("Failed to stop WiseFlow, attempting to start anyway")
        
        # Wait a moment for processes to terminate
        time.sleep(2)
        
        # Start the application
        if not start_native():
            return False
        
        logger.info("WiseFlow restarted successfully")
        return True
    except Exception as e:
        logger.error(f"Error restarting WiseFlow natively: {e}")
        return False

def status_native() -> bool:
    """
    Check the status of the application natively.
    
    Returns:
        bool: True if status check was successful, False otherwise
    """
    try:
        logger.info("Checking WiseFlow status natively...")
        
        # Check PocketBase status
        pocketbase_pids = find_process("pocketbase")
        if pocketbase_pids:
            logger.info(f"PocketBase is running (PIDs: {', '.join(map(str, pocketbase_pids))})")
        else:
            logger.info("PocketBase is not running")
        
        # Check WiseFlow core status
        wiseflow_pids = find_process("run_task.py")
        if wiseflow_pids:
            logger.info(f"WiseFlow core is running (PIDs: {', '.join(map(str, wiseflow_pids))})")
        else:
            logger.info("WiseFlow core is not running")
        
        return True
    except Exception as e:
        logger.error(f"Error checking WiseFlow status natively: {e}")
        return False

def logs_native() -> bool:
    """
    View application logs natively.
    
    Returns:
        bool: True if log retrieval was successful, False otherwise
    """
    try:
        logger.info("Viewing WiseFlow logs natively...")
        
        # Check if log files exist
        pb_log_path = Path("pb") / "pocketbase.log"
        wiseflow_log_path = Path("core") / "wiseflow.log"
        
        if pb_log_path.exists():
            logger.info(f"PocketBase log file: {pb_log_path}")
            with open(pb_log_path, 'r') as f:
                print("\n=== PocketBase Logs ===")
                # Print the last 50 lines
                lines = f.readlines()
                for line in lines[-50:]:
                    print(line.strip())
        else:
            logger.warning("PocketBase log file not found")
        
        if wiseflow_log_path.exists():
            logger.info(f"WiseFlow log file: {wiseflow_log_path}")
            with open(wiseflow_log_path, 'r') as f:
                print("\n=== WiseFlow Logs ===")
                # Print the last 50 lines
                lines = f.readlines()
                for line in lines[-50:]:
                    print(line.strip())
        else:
            logger.warning("WiseFlow log file not found")
        
        return True
    except Exception as e:
        logger.error(f"Error viewing WiseFlow logs natively: {e}")
        return False

def update_native() -> bool:
    """
    Update the application natively.
    
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        logger.info("Updating WiseFlow natively...")
        
        # Check if git is available
        try:
            subprocess.run(["git", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.error("Git is not installed or not in PATH")
            return False
        
        # Stop the application
        if not stop_native():
            logger.warning("Failed to stop WiseFlow, attempting to update anyway")
        
        # Pull latest changes
        logger.info("Pulling latest changes from Git repository...")
        try:
            subprocess.run(["git", "pull"], check=True)
        except subprocess.SubprocessError as e:
            logger.error(f"Failed to pull latest changes: {e}")
            return False
        
        # Install dependencies
        logger.info("Installing dependencies...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        except subprocess.SubprocessError as e:
            logger.error(f"Failed to install dependencies: {e}")
            return False
        
        # Start the application
        if not start_native():
            return False
        
        logger.info("WiseFlow updated successfully")
        return True
    except Exception as e:
        logger.error(f"Error updating WiseFlow natively: {e}")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="WiseFlow Deployment")
    parser.add_argument("--docker", action="store_true", help="Use Docker for deployment")
    parser.add_argument("--native", action="store_true", help="Use native deployment")
    parser.add_argument("--start", action="store_true", help="Start the application")
    parser.add_argument("--stop", action="store_true", help="Stop the application")
    parser.add_argument("--restart", action="store_true", help="Restart the application")
    parser.add_argument("--status", action="store_true", help="Check the status of the application")
    parser.add_argument("--logs", action="store_true", help="View application logs")
    parser.add_argument("--update", action="store_true", help="Update the application")
    
    args = parser.parse_args()
    
    # If no action specified, default to --start
    if not any([args.start, args.stop, args.restart, args.status, args.logs, args.update]):
        args.start = True
    
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
    
    # Execute requested action
    if args.start:
        if deployment_method == "docker":
            if not start_docker():
                return 1
        else:
            if not start_native():
                return 1
    
    if args.stop:
        if deployment_method == "docker":
            if not stop_docker():
                return 1
        else:
            if not stop_native():
                return 1
    
    if args.restart:
        if deployment_method == "docker":
            if not restart_docker():
                return 1
        else:
            if not restart_native():
                return 1
    
    if args.status:
        if deployment_method == "docker":
            if not status_docker():
                return 1
        else:
            if not status_native():
                return 1
    
    if args.logs:
        if deployment_method == "docker":
            if not logs_docker():
                return 1
        else:
            if not logs_native():
                return 1
    
    if args.update:
        if deployment_method == "docker":
            if not update_docker():
                return 1
        else:
            if not update_native():
                return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

