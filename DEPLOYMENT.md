# WiseFlow Deployment Guide

This guide provides comprehensive instructions for deploying and configuring WiseFlow in various environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Deployment Methods](#deployment-methods)
  - [Docker Deployment](#docker-deployment)
  - [Native Deployment](#native-deployment)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [PocketBase Setup](#pocketbase-setup)
- [Deployment Scripts](#deployment-scripts)
  - [setup.py](#setuppy)
  - [deploy.py](#deploypy)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)
- [Updating WiseFlow](#updating-wiseflow)
- [Platform-Specific Notes](#platform-specific-notes)

## Prerequisites

Before deploying WiseFlow, ensure you have the following:

- **Python 3.8 or higher**
- **Git** (for cloning the repository and updates)
- For Docker deployment:
  - Docker Engine
  - Docker Compose
- For native deployment:
  - Python virtual environment (recommended)
  - Required system libraries (see below)

### Required System Libraries

For native deployment, you may need the following system libraries:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y build-essential python3-dev python3-pip python3-venv
```

**CentOS/RHEL:**
```bash
sudo yum install -y gcc gcc-c++ python3-devel python3-pip
```

**macOS:**
```bash
brew install python
```

**Windows:**
- Install Python from [python.org](https://www.python.org/downloads/)
- Install Git from [git-scm.com](https://git-scm.com/downloads)

## Quick Start

The fastest way to get WiseFlow up and running is to use the automated setup script:

```bash
# Clone the repository
git clone https://github.com/Zeeeepa/wiseflow.git
cd wiseflow

# Run the setup script
python setup.py --all
```

This will:
1. Check prerequisites
2. Install Python dependencies
3. Set up PocketBase
4. Configure environment variables
5. Deploy WiseFlow

## Deployment Methods

WiseFlow supports two primary deployment methods: Docker and native deployment.

### Docker Deployment

Docker deployment is recommended for production environments and provides the most consistent experience across platforms.

#### Prerequisites for Docker Deployment

- Docker Engine
- Docker Compose

#### Docker Deployment Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Zeeeepa/wiseflow.git
   cd wiseflow
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your preferred text editor
   ```

3. **Start the containers:**
   ```bash
   python deploy.py --docker --start
   ```

4. **Verify deployment:**
   ```bash
   python deploy.py --docker --status
   ```

#### Docker Compose Services

The Docker deployment includes the following services:

- **pocketbase**: Database and authentication service
- **core**: Main WiseFlow application
- **dashboard** (optional): Web interface for WiseFlow

#### Docker Compose Commands

You can also use Docker Compose directly:

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs

# Restart services
docker-compose restart
```

### Native Deployment

Native deployment runs WiseFlow directly on your system without containers.

#### Prerequisites for Native Deployment

- Python 3.8 or higher
- Git
- Python virtual environment (recommended)

#### Native Deployment Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Zeeeepa/wiseflow.git
   cd wiseflow
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up PocketBase:**
   ```bash
   python setup.py --setup-pocketbase
   ```

5. **Configure environment variables:**
   ```bash
   python setup.py --configure
   ```

6. **Start WiseFlow:**
   ```bash
   python deploy.py --native --start
   ```

7. **Verify deployment:**
   ```bash
   python deploy.py --native --status
   ```

## Configuration

### Environment Variables

WiseFlow is configured using environment variables. The following categories of settings are available:

- **Project Settings**: General project configuration
- **LLM Settings**: Configuration for language models
- **PocketBase Settings**: Database and authentication configuration
- **Search Settings**: Configuration for search functionality
- **Crawler Settings**: Configuration for web crawling
- **Task Settings**: Configuration for task execution
- **Feature Flags**: Enable/disable specific features

See [.env.example](.env.example) for a complete list of environment variables and their descriptions.

### PocketBase Setup

PocketBase is used for database storage and authentication. The setup process includes:

1. **Download PocketBase**: The setup script will download the appropriate version for your platform
2. **Create admin user**: You'll be prompted to create an admin user during setup
3. **Configure environment**: The admin credentials will be added to your .env file

## Deployment Scripts

WiseFlow includes two main deployment scripts:

### setup.py

The `setup.py` script handles initial setup and configuration:

```bash
python setup.py [options]
```

Options:
- `--install-deps`: Install Python dependencies
- `--setup-pocketbase`: Install and configure PocketBase
- `--configure`: Create or update configuration
- `--deploy`: Deploy the application
- `--all`: Perform all setup steps (default)
- `--docker`: Use Docker for deployment
- `--native`: Use native deployment

### deploy.py

The `deploy.py` script manages the running application:

```bash
python deploy.py [options]
```

Options:
- `--docker`: Use Docker for deployment
- `--native`: Use native deployment
- `--start`: Start the application
- `--stop`: Stop the application
- `--restart`: Restart the application
- `--status`: Check the status of the application
- `--logs`: View application logs
- `--update`: Update the application

## Troubleshooting

### Common Issues

#### PocketBase Connection Issues

**Symptom**: WiseFlow cannot connect to PocketBase

**Solutions**:
1. Check if PocketBase is running: `python deploy.py --status`
2. Verify PocketBase credentials in .env file
3. Check PocketBase logs: `python deploy.py --logs`

#### Docker Container Issues

**Symptom**: Docker containers fail to start

**Solutions**:
1. Check Docker logs: `docker-compose logs`
2. Verify Docker and Docker Compose installation
3. Check for port conflicts (8090 for PocketBase)

#### Python Dependency Issues

**Symptom**: Error installing Python dependencies

**Solutions**:
1. Update pip: `pip install --upgrade pip`
2. Install system dependencies (see Prerequisites)
3. Use a virtual environment: `python -m venv venv`

### Logging

WiseFlow logs are stored in the following locations:

- **Docker deployment**: View logs with `python deploy.py --docker --logs`
- **Native deployment**:
  - PocketBase logs: `pb/pocketbase.log`
  - WiseFlow logs: `core/wiseflow.log`
  - Setup logs: `wiseflow_setup.log`
  - Deployment logs: `wiseflow_deploy.log`

## Security Considerations

### API Keys

API keys and credentials should be kept secure:

1. Never commit .env files to version control
2. Use environment variables for sensitive information
3. Restrict access to the .env file

### PocketBase Security

1. Use a strong password for the PocketBase admin user
2. Change the default admin email and password
3. Consider running PocketBase behind a reverse proxy with HTTPS

### Docker Security

1. Don't run containers as root
2. Keep Docker and container images updated
3. Use Docker secrets for sensitive information in production

## Updating WiseFlow

### Docker Deployment

```bash
# Pull latest changes
git pull

# Update and restart containers
python deploy.py --docker --update
```

### Native Deployment

```bash
# Pull latest changes
git pull

# Update dependencies
pip install -r requirements.txt

# Restart WiseFlow
python deploy.py --native --restart
```

## Platform-Specific Notes

### Windows

- Use PowerShell or Command Prompt with Administrator privileges
- If using WSL, follow the Linux instructions
- Windows Defender or antivirus software may block some operations

### macOS

- Install Python using Homebrew for best results
- Use Terminal.app or iTerm2

### Linux

- Different distributions may require different system dependencies
- Use your distribution's package manager to install prerequisites

