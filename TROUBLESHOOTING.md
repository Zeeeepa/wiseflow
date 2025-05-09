# WiseFlow Troubleshooting Guide

This guide provides solutions for common issues you might encounter when deploying and running WiseFlow.

## Table of Contents

- [Deployment Issues](#deployment-issues)
  - [Script Disappears Instantly](#script-disappears-instantly)
  - [Python Dependency Installation Failures](#python-dependency-installation-failures)
  - [PocketBase Installation Issues](#pocketbase-installation-issues)
  - [Docker Deployment Issues](#docker-deployment-issues)
- [Runtime Issues](#runtime-issues)
  - [Connection to PocketBase Failed](#connection-to-pocketbase-failed)
  - [LLM API Connection Issues](#llm-api-connection-issues)
  - [Memory Usage Problems](#memory-usage-problems)
  - [Performance Issues](#performance-issues)
- [Configuration Issues](#configuration-issues)
  - [Environment Variables Not Applied](#environment-variables-not-applied)
  - [Missing Configuration](#missing-configuration)
- [Platform-Specific Issues](#platform-specific-issues)
  - [Windows Issues](#windows-issues)
  - [macOS Issues](#macos-issues)
  - [Linux Issues](#linux-issues)
- [Logging and Debugging](#logging-and-debugging)
  - [Enabling Verbose Logging](#enabling-verbose-logging)
  - [Checking Log Files](#checking-log-files)
- [Getting Help](#getting-help)

## Deployment Issues

### Script Disappears Instantly

If you're experiencing an issue where the `deploy_and_launch.bat` script window disappears immediately after launching, try the following solutions:

#### Solution 1: Use the Unified Deployment Scripts

We've created new cross-platform deployment scripts that work on all operating systems:

1. Use `setup.py` for initial setup and configuration
2. Use `deploy.py` for managing the running application

Example:
```bash
python setup.py --all
python deploy.py --start
```

#### Solution 2: Use the Wrapper Script

If you prefer the batch files, we've created a wrapper script that will help keep the deployment window open:

1. Download both `deploy_and_launch.bat` and `run_deploy.bat` to the same folder
2. Run `run_deploy.bat` instead of directly running `deploy_and_launch.bat`
3. The deployment will start in a new window that will stay open

#### Solution 3: Run from Command Prompt

1. Open Command Prompt (Start menu > type "cmd" > press Enter)
2. Navigate to the folder containing the script:
   ```
   cd path\to\your\folder
   ```
3. Run the script directly:
   ```
   deploy_and_launch.bat
   ```

#### Solution 4: Run as Administrator

1. Right-click on `deploy_and_launch.bat`
2. Select "Run as administrator"
3. Confirm the User Account Control prompt if it appears

#### Solution 5: Create a Shortcut with Special Properties

1. Right-click in the folder containing the script and select New > Shortcut
2. In the location field, enter:
   ```
   cmd.exe /K "deploy_and_launch.bat"
   ```
3. Name the shortcut "Run WiseFlow Deployment"
4. Use this shortcut to run the deployment script

### Python Dependency Installation Failures

If you encounter issues installing Python dependencies, try the following solutions:

#### Solution 1: Update pip

```bash
python -m pip install --upgrade pip
```

#### Solution 2: Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y build-essential python3-dev
```

**CentOS/RHEL:**
```bash
sudo yum install -y gcc gcc-c++ python3-devel
```

**macOS:**
```bash
brew install python
```

#### Solution 3: Use a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Linux/macOS
venv\Scripts\activate     # On Windows
pip install -r requirements.txt
```

#### Solution 4: Install Dependencies One by One

If a specific dependency is causing issues, try installing dependencies one by one:

```bash
pip install requests
pip install python-dotenv
# Continue with other dependencies
```

### PocketBase Installation Issues

If you encounter issues installing or running PocketBase, try the following solutions:

#### Solution 1: Use the Setup Script

The `setup.py` script automates PocketBase installation:

```bash
python setup.py --setup-pocketbase
```

#### Solution 2: Manual Download

1. Visit the [PocketBase releases page](https://github.com/pocketbase/pocketbase/releases)
2. Download the appropriate version for your platform
3. Extract the executable to the `pb` directory
4. Make it executable (Linux/macOS): `chmod +x pb/pocketbase`

#### Solution 3: Check Firewall Settings

Ensure that port 8090 is not blocked by your firewall.

### Docker Deployment Issues

If you encounter issues with Docker deployment, try the following solutions:

#### Solution 1: Check Docker Installation

```bash
docker --version
docker-compose --version
```

#### Solution 2: Check Docker Service

```bash
# Linux
sudo systemctl status docker

# macOS/Windows
docker info
```

#### Solution 3: Check for Port Conflicts

```bash
# Linux/macOS
sudo lsof -i :8090

# Windows
netstat -ano | findstr :8090
```

#### Solution 4: Check Docker Logs

```bash
docker-compose logs
```

## Runtime Issues

### Connection to PocketBase Failed

If WiseFlow cannot connect to PocketBase, try the following solutions:

#### Solution 1: Check PocketBase Status

```bash
python deploy.py --status
```

#### Solution 2: Check PocketBase Logs

```bash
python deploy.py --logs
```

#### Solution 3: Verify PocketBase Configuration

Check the `PB_API_BASE` and `PB_API_AUTH` settings in your `.env` file.

#### Solution 4: Restart PocketBase

```bash
python deploy.py --restart
```

### LLM API Connection Issues

If WiseFlow cannot connect to the LLM API, try the following solutions:

#### Solution 1: Check API Key

Verify that your `LLM_API_KEY` is correct in the `.env` file.

#### Solution 2: Check API Base URL

Verify that your `LLM_API_BASE` is correct in the `.env` file.

#### Solution 3: Check Internet Connection

Ensure that your system can access the internet and the LLM API endpoint.

#### Solution 4: Check for Rate Limiting

You might be hitting rate limits with your LLM provider. Try reducing `LLM_CONCURRENT_NUMBER` in your `.env` file.

### Memory Usage Problems

If WiseFlow is using too much memory, try the following solutions:

#### Solution 1: Reduce Concurrency

Reduce `MAX_CONCURRENT_TASKS` and `LLM_CONCURRENT_NUMBER` in your `.env` file.

#### Solution 2: Limit Crawler Scope

Reduce `CRAWLER_MAX_PAGES` and `CRAWLER_MAX_DEPTH` in your `.env` file.

#### Solution 3: Monitor Resource Usage

Use the `deploy.py` script to check resource usage:

```bash
python deploy.py --status
```

### Performance Issues

If WiseFlow is running slowly, try the following solutions:

#### Solution 1: Increase Concurrency

Increase `MAX_CONCURRENT_TASKS` and `LLM_CONCURRENT_NUMBER` in your `.env` file.

#### Solution 2: Use a Faster LLM Model

Change `SECONDARY_MODEL` to a faster model in your `.env` file.

#### Solution 3: Optimize Docker Resources

If using Docker, allocate more resources to the Docker engine.

## Configuration Issues

### Environment Variables Not Applied

If your environment variables are not being applied, try the following solutions:

#### Solution 1: Check .env File Location

Ensure that your `.env` file is in the correct location:
- For native deployment: `core/.env`
- For Docker deployment: `.env` (root directory)

#### Solution 2: Check .env File Format

Ensure that your `.env` file has the correct format:
```
KEY=value
```

#### Solution 3: Restart WiseFlow

After changing environment variables, restart WiseFlow:

```bash
python deploy.py --restart
```

### Missing Configuration

If WiseFlow is missing configuration, try the following solutions:

#### Solution 1: Use the Configuration Script

```bash
python setup.py --configure
```

#### Solution 2: Copy from Example

```bash
cp .env.example core/.env
# Edit core/.env with your preferred text editor
```

## Platform-Specific Issues

### Windows Issues

#### Issue: Script Execution Policy

If you cannot run PowerShell scripts, try:

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
```

#### Issue: Long Path Support

If you encounter path length issues:

1. Enable long path support in Windows:
   ```
   reg add "HKLM\SYSTEM\CurrentControlSet\Control\FileSystem" /v LongPathsEnabled /t REG_DWORD /d 1 /f
   ```
2. Restart your computer

### macOS Issues

#### Issue: Python Version

macOS may have an outdated Python version. Install a newer version:

```bash
brew install python
```

#### Issue: Permission Denied

If you encounter permission issues:

```bash
chmod +x install_pocketbase.sh
chmod +x core/run.sh
```

### Linux Issues

#### Issue: Missing Libraries

Install required libraries:

```bash
sudo apt-get update
sudo apt-get install -y build-essential python3-dev python3-pip python3-venv
```

#### Issue: Permission Denied

If you encounter permission issues:

```bash
chmod +x install_pocketbase.sh
chmod +x core/run.sh
```

## Logging and Debugging

### Enabling Verbose Logging

To enable verbose logging, set `VERBOSE=true` in your `.env` file.

### Checking Log Files

WiseFlow logs are stored in the following locations:

- **Docker deployment**: View logs with `python deploy.py --docker --logs`
- **Native deployment**:
  - PocketBase logs: `pb/pocketbase.log`
  - WiseFlow logs: `core/wiseflow.log`
  - Setup logs: `wiseflow_setup.log`
  - Deployment logs: `wiseflow_deploy.log`

## Getting Help

If you continue to experience problems, please:

1. Create an issue on the GitHub repository with details about your system
2. Include any error messages from the log files
3. Describe the exact steps you're taking to run the script
4. Include your environment details (OS, Python version, etc.)
