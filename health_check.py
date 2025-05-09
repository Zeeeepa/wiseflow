#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WiseFlow Health Check Script

This script checks the health of WiseFlow components and reports their status.
It can be used for monitoring and troubleshooting.

Usage:
    python health_check.py [options]

Options:
    --verbose       Show detailed information
    --json          Output in JSON format
    --email=EMAIL   Send report to email address
    --help          Show this help message
"""

import os
import sys
import json
import argparse
import platform
import subprocess
import requests
import psutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

def check_pocketbase() -> Dict[str, Any]:
    """
    Check if PocketBase is running and accessible.
    
    Returns:
        Dict[str, Any]: Status information
    """
    result = {
        "component": "PocketBase",
        "running": False,
        "accessible": False,
        "version": None,
        "uptime": None,
        "error": None
    }
    
    # Check if PocketBase process is running
    pocketbase_pids = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if "pocketbase" in proc.info['name'].lower():
                pocketbase_pids.append(proc.info['pid'])
                result["running"] = True
            elif proc.info['cmdline'] and any("pocketbase" in cmd.lower() for cmd in proc.info['cmdline']):
                pocketbase_pids.append(proc.info['pid'])
                result["running"] = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    # Get process uptime if running
    if result["running"] and pocketbase_pids:
        try:
            process = psutil.Process(pocketbase_pids[0])
            result["uptime"] = time.time() - process.create_time()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    # Check if PocketBase API is accessible
    try:
        # Try to load PB_API_BASE from environment
        pb_api_base = os.environ.get("PB_API_BASE", "http://127.0.0.1:8090")
        
        # Try to access the health endpoint
        response = requests.get(f"{pb_api_base}/api/health", timeout=5)
        if response.status_code == 200:
            result["accessible"] = True
            # Try to get version information
            try:
                version_response = requests.get(f"{pb_api_base}/api/", timeout=5)
                if version_response.status_code == 200:
                    data = version_response.json()
                    result["version"] = data.get("version", "Unknown")
            except Exception:
                pass
    except Exception as e:
        result["error"] = str(e)
    
    return result

def check_wiseflow_core() -> Dict[str, Any]:
    """
    Check if WiseFlow core is running.
    
    Returns:
        Dict[str, Any]: Status information
    """
    result = {
        "component": "WiseFlow Core",
        "running": False,
        "uptime": None,
        "memory_usage": None,
        "cpu_usage": None,
        "error": None
    }
    
    # Check if WiseFlow core process is running
    wiseflow_pids = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline'] and any("run_task.py" in cmd for cmd in proc.info['cmdline']):
                wiseflow_pids.append(proc.info['pid'])
                result["running"] = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    # Get process information if running
    if result["running"] and wiseflow_pids:
        try:
            process = psutil.Process(wiseflow_pids[0])
            result["uptime"] = time.time() - process.create_time()
            result["memory_usage"] = process.memory_info().rss / (1024 * 1024)  # MB
            result["cpu_usage"] = process.cpu_percent(interval=0.1)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    return result

def check_docker() -> Dict[str, Any]:
    """
    Check Docker status if using Docker deployment.
    
    Returns:
        Dict[str, Any]: Status information
    """
    result = {
        "component": "Docker",
        "available": False,
        "containers": [],
        "error": None
    }
    
    # Check if Docker is available
    try:
        subprocess.run(["docker", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result["available"] = True
    except (subprocess.SubprocessError, FileNotFoundError):
        result["error"] = "Docker not installed or not in PATH"
        return result
    
    # Check Docker containers
    try:
        output = subprocess.check_output(["docker", "ps", "--format", "{{.Names}},{{.Status}},{{.Ports}}"], universal_newlines=True)
        for line in output.strip().split("\n"):
            if line:
                parts = line.split(",")
                if len(parts) >= 2:
                    name = parts[0]
                    status = parts[1]
                    ports = parts[2] if len(parts) > 2 else ""
                    
                    if "wiseflow" in name.lower() or "pocketbase" in name.lower():
                        result["containers"].append({
                            "name": name,
                            "status": status,
                            "ports": ports
                        })
    except subprocess.SubprocessError as e:
        result["error"] = str(e)
    
    return result

def check_system_resources() -> Dict[str, Any]:
    """
    Check system resources.
    
    Returns:
        Dict[str, Any]: Status information
    """
    result = {
        "component": "System Resources",
        "cpu_usage": None,
        "memory_usage": None,
        "disk_usage": None,
        "python_version": None,
        "platform": None
    }
    
    # CPU usage
    result["cpu_usage"] = psutil.cpu_percent(interval=1)
    
    # Memory usage
    memory = psutil.virtual_memory()
    result["memory_usage"] = {
        "total": memory.total / (1024 * 1024 * 1024),  # GB
        "available": memory.available / (1024 * 1024 * 1024),  # GB
        "percent": memory.percent
    }
    
    # Disk usage
    disk = psutil.disk_usage("/")
    result["disk_usage"] = {
        "total": disk.total / (1024 * 1024 * 1024),  # GB
        "free": disk.free / (1024 * 1024 * 1024),  # GB
        "percent": disk.percent
    }
    
    # Python version
    result["python_version"] = platform.python_version()
    
    # Platform information
    result["platform"] = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine()
    }
    
    return result

def check_environment() -> Dict[str, Any]:
    """
    Check environment configuration.
    
    Returns:
        Dict[str, Any]: Status information
    """
    result = {
        "component": "Environment",
        "env_file_exists": False,
        "required_vars_present": False,
        "missing_vars": [],
        "error": None
    }
    
    # Check if .env file exists
    env_paths = [
        Path("core") / ".env",
        Path(".env")
    ]
    
    for env_path in env_paths:
        if env_path.exists():
            result["env_file_exists"] = True
            result["env_file_path"] = str(env_path)
            break
    
    # Check required environment variables
    required_vars = [
        "LLM_API_KEY",
        "PRIMARY_MODEL",
        "PB_API_AUTH"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    result["missing_vars"] = missing_vars
    result["required_vars_present"] = len(missing_vars) == 0
    
    return result

def run_health_check(verbose: bool = False) -> Dict[str, Any]:
    """
    Run a comprehensive health check.
    
    Args:
        verbose: Whether to include detailed information
        
    Returns:
        Dict[str, Any]: Health check results
    """
    results = {
        "timestamp": time.time(),
        "overall_status": "unknown",
        "components": {}
    }
    
    # Check PocketBase
    pocketbase_status = check_pocketbase()
    results["components"]["pocketbase"] = pocketbase_status
    
    # Check WiseFlow core
    wiseflow_status = check_wiseflow_core()
    results["components"]["wiseflow_core"] = wiseflow_status
    
    # Check Docker
    docker_status = check_docker()
    results["components"]["docker"] = docker_status
    
    # Check system resources
    system_status = check_system_resources()
    results["components"]["system"] = system_status
    
    # Check environment
    env_status = check_environment()
    results["components"]["environment"] = env_status
    
    # Determine overall status
    if pocketbase_status["accessible"] and wiseflow_status["running"]:
        results["overall_status"] = "healthy"
    elif pocketbase_status["running"] or wiseflow_status["running"]:
        results["overall_status"] = "degraded"
    else:
        results["overall_status"] = "unhealthy"
    
    # Remove detailed information if not verbose
    if not verbose:
        for component in results["components"].values():
            for key in list(component.keys()):
                if key not in ["component", "running", "accessible", "available", "error"]:
                    component.pop(key, None)
    
    return results

def format_uptime(seconds: Optional[float]) -> str:
    """
    Format uptime in a human-readable format.
    
    Args:
        seconds: Uptime in seconds
        
    Returns:
        str: Formatted uptime
    """
    if seconds is None:
        return "Unknown"
    
    days, remainder = divmod(int(seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m {seconds}s"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def print_health_check(results: Dict[str, Any]) -> None:
    """
    Print health check results in a human-readable format.
    
    Args:
        results: Health check results
    """
    print(f"WiseFlow Health Check - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Overall Status: {results['overall_status'].upper()}")
    print("-" * 80)
    
    # PocketBase
    pb = results["components"]["pocketbase"]
    print(f"PocketBase: {'✅' if pb['accessible'] else '❌'}")
    print(f"  Running: {pb['running']}")
    print(f"  Accessible: {pb['accessible']}")
    if "version" in pb and pb["version"]:
        print(f"  Version: {pb['version']}")
    if "uptime" in pb and pb["uptime"]:
        print(f"  Uptime: {format_uptime(pb['uptime'])}")
    if pb["error"]:
        print(f"  Error: {pb['error']}")
    print()
    
    # WiseFlow Core
    wf = results["components"]["wiseflow_core"]
    print(f"WiseFlow Core: {'✅' if wf['running'] else '❌'}")
    print(f"  Running: {wf['running']}")
    if "uptime" in wf and wf["uptime"]:
        print(f"  Uptime: {format_uptime(wf['uptime'])}")
    if "memory_usage" in wf and wf["memory_usage"]:
        print(f"  Memory Usage: {wf['memory_usage']:.2f} MB")
    if "cpu_usage" in wf and wf["cpu_usage"]:
        print(f"  CPU Usage: {wf['cpu_usage']:.2f}%")
    if wf["error"]:
        print(f"  Error: {wf['error']}")
    print()
    
    # Docker
    docker = results["components"]["docker"]
    print(f"Docker: {'✅' if docker['available'] else '❌'}")
    print(f"  Available: {docker['available']}")
    if docker["available"] and "containers" in docker:
        print(f"  Containers:")
        for container in docker["containers"]:
            print(f"    {container['name']}: {container['status']}")
    if docker["error"]:
        print(f"  Error: {docker['error']}")
    print()
    
    # System Resources
    system = results["components"]["system"]
    print("System Resources:")
    if "cpu_usage" in system:
        print(f"  CPU Usage: {system['cpu_usage']}%")
    if "memory_usage" in system:
        mem = system["memory_usage"]
        print(f"  Memory: {mem['percent']}% used ({mem['available']:.2f} GB free of {mem['total']:.2f} GB)")
    if "disk_usage" in system:
        disk = system["disk_usage"]
        print(f"  Disk: {disk['percent']}% used ({disk['free']:.2f} GB free of {disk['total']:.2f} GB)")
    if "python_version" in system:
        print(f"  Python Version: {system['python_version']}")
    if "platform" in system:
        platform_info = system["platform"]
        print(f"  Platform: {platform_info['system']} {platform_info['release']} ({platform_info['machine']})")
    print()
    
    # Environment
    env = results["components"]["environment"]
    print(f"Environment: {'✅' if env['required_vars_present'] else '❌'}")
    print(f"  .env File: {'Found' if env['env_file_exists'] else 'Not found'}")
    if env["env_file_exists"] and "env_file_path" in env:
        print(f"  .env Path: {env['env_file_path']}")
    print(f"  Required Variables: {'All present' if env['required_vars_present'] else 'Some missing'}")
    if env["missing_vars"]:
        print(f"  Missing Variables: {', '.join(env['missing_vars'])}")
    if env["error"]:
        print(f"  Error: {env['error']}")
    print()

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="WiseFlow Health Check")
    parser.add_argument("--verbose", action="store_true", help="Show detailed information")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--email", help="Send report to email address")
    
    args = parser.parse_args()
    
    # Run health check
    results = run_health_check(verbose=args.verbose)
    
    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_health_check(results)
    
    # Send email if requested
    if args.email:
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # Create message
            msg = MIMEMultipart()
            msg["Subject"] = f"WiseFlow Health Check - {results['overall_status'].upper()}"
            msg["From"] = "wiseflow@example.com"
            msg["To"] = args.email
            
            # Create text content
            text_content = f"WiseFlow Health Check - {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            text_content += f"Overall Status: {results['overall_status'].upper()}\n\n"
            text_content += f"See attached JSON report for details."
            
            # Attach text content
            msg.attach(MIMEText(text_content, "plain"))
            
            # Attach JSON report
            json_attachment = MIMEText(json.dumps(results, indent=2), "plain")
            json_attachment.add_header("Content-Disposition", "attachment", filename="wiseflow_health_check.json")
            msg.attach(json_attachment)
            
            # Send email
            print(f"Sending email to {args.email}...")
            # This is a placeholder - you would need to configure SMTP settings
            print("Email sending not implemented. Please configure SMTP settings in the script.")
            
        except ImportError:
            print("Email modules not available. Please install 'email' package.")
        except Exception as e:
            print(f"Error sending email: {e}")
    
    # Return exit code based on status
    if results["overall_status"] == "healthy":
        return 0
    elif results["overall_status"] == "degraded":
        return 1
    else:
        return 2

if __name__ == "__main__":
    sys.exit(main())

