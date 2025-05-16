#!/bin/bash
# WiseFlow Deployment Script for Unix Systems
# This script provides a simple way to deploy WiseFlow on Unix systems.

# Function to display help message
show_help() {
    echo "WiseFlow Deployment Script"
    echo "Usage: ./deploy.sh [options]"
    echo ""
    echo "Options:"
    echo "  --setup         Run the setup script"
    echo "  --start         Start WiseFlow"
    echo "  --stop          Stop WiseFlow"
    echo "  --restart       Restart WiseFlow"
    echo "  --status        Check WiseFlow status"
    echo "  --logs          View WiseFlow logs"
    echo "  --update        Update WiseFlow"
    echo "  --docker        Use Docker deployment"
    echo "  --native        Use native deployment"
    echo "  --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./deploy.sh --setup          # Run the setup script"
    echo "  ./deploy.sh --start          # Start WiseFlow"
    echo "  ./deploy.sh --docker --start # Start WiseFlow with Docker"
}

# Make the script executable
chmod +x "$0"

# Parse command line arguments
SETUP=false
START=false
STOP=false
RESTART=false
STATUS=false
LOGS=false
UPDATE=false
DOCKER=false
NATIVE=false

# If no arguments provided, show help
if [ $# -eq 0 ]; then
    show_help
    exit 0
fi

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --setup)
            SETUP=true
            shift
            ;;
        --start)
            START=true
            shift
            ;;
        --stop)
            STOP=true
            shift
            ;;
        --restart)
            RESTART=true
            shift
            ;;
        --status)
            STATUS=true
            shift
            ;;
        --logs)
            LOGS=true
            shift
            ;;
        --update)
            UPDATE=true
            shift
            ;;
        --docker)
            DOCKER=true
            shift
            ;;
        --native)
            NATIVE=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# Run setup script
if [ "$SETUP" = true ]; then
    echo "Running setup script..."
    if [ "$DOCKER" = true ]; then
        python3 setup.py --all --docker
    elif [ "$NATIVE" = true ]; then
        python3 setup.py --all --native
    else
        python3 setup.py --all
    fi
fi

# Run deploy script
if [ "$START" = true ]; then
    echo "Starting WiseFlow..."
    if [ "$DOCKER" = true ]; then
        python3 deploy.py --docker --start
    elif [ "$NATIVE" = true ]; then
        python3 deploy.py --native --start
    else
        python3 deploy.py --start
    fi
fi

if [ "$STOP" = true ]; then
    echo "Stopping WiseFlow..."
    if [ "$DOCKER" = true ]; then
        python3 deploy.py --docker --stop
    elif [ "$NATIVE" = true ]; then
        python3 deploy.py --native --stop
    else
        python3 deploy.py --stop
    fi
fi

if [ "$RESTART" = true ]; then
    echo "Restarting WiseFlow..."
    if [ "$DOCKER" = true ]; then
        python3 deploy.py --docker --restart
    elif [ "$NATIVE" = true ]; then
        python3 deploy.py --native --restart
    else
        python3 deploy.py --restart
    fi
fi

if [ "$STATUS" = true ]; then
    echo "Checking WiseFlow status..."
    if [ "$DOCKER" = true ]; then
        python3 deploy.py --docker --status
    elif [ "$NATIVE" = true ]; then
        python3 deploy.py --native --status
    else
        python3 deploy.py --status
    fi
fi

if [ "$LOGS" = true ]; then
    echo "Viewing WiseFlow logs..."
    if [ "$DOCKER" = true ]; then
        python3 deploy.py --docker --logs
    elif [ "$NATIVE" = true ]; then
        python3 deploy.py --native --logs
    else
        python3 deploy.py --logs
    fi
fi

if [ "$UPDATE" = true ]; then
    echo "Updating WiseFlow..."
    if [ "$DOCKER" = true ]; then
        python3 deploy.py --docker --update
    elif [ "$NATIVE" = true ]; then
        python3 deploy.py --native --update
    else
        python3 deploy.py --update
    fi
fi

