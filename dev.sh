#!/bin/bash

# EcoCoder Agent Development Script
# Usage: ./dev.sh [command]
# Commands: start, test, install, format, lint

set -e

# Configuration
VENV_DIR=".venv"
PYTHON_EXEC="$VENV_DIR/bin/python"
PIP_EXEC="$VENV_DIR/bin/pip"
PYTHON311="/opt/homebrew/bin/python3.11"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Check if virtual environment exists
check_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        log_error "Virtual environment not found at $VENV_DIR"
        log_info "Run './dev.sh install' to set up the development environment"
        exit 1
    fi
}

# Install dependencies
install_deps() {
    log_info "Setting up development environment with Python 3.11..."
    
    if [ ! -d "$VENV_DIR" ]; then
        log_info "Creating virtual environment with Python 3.11..."
        "$PYTHON311" -m venv "$VENV_DIR"
    fi
    
    log_info "Installing dependencies..."
    "$PIP_EXEC" install --upgrade pip
    
    log_info "Installing Strands SDK and BedrockAgentCore..."
    "$PIP_EXEC" install strands bedrock-agentcore bedrock-agentcore-starter-toolkit
    
    log_info "Installing other dependencies..."
    "$PIP_EXEC" install codecarbon pandas structlog requests python-dateutil pyyaml
    "$PIP_EXEC" install python-dotenv black isort flake8 mypy pytest pytest-cov pytest-mock
    
    log_success "Development environment ready!"
    log_info "You can now run: ./dev.sh start"
}

# Start the agent in development mode
start_agent() {
    check_venv
    log_info "Starting EcoCoder Agent in Development Mode..."
    export ENVIRONMENT=development
    "$PYTHON_EXEC" run_dev.py
}

# Run tests
run_tests() {
    check_venv
    log_info "Running tests..."
    if [ -d "tests" ]; then
        "$PYTHON_EXEC" -m pytest tests/ -v --cov=app --cov-report=term-missing
    else
        log_warning "No tests directory found"
    fi
}

# Format code
format_code() {
    check_venv
    log_info "Formatting code..."
    "$PYTHON_EXEC" -m black app/ --line-length 100
    "$PYTHON_EXEC" -m isort app/ --profile black
    log_success "Code formatted!"
}

# Lint code
lint_code() {
    check_venv
    log_info "Linting code..."
    "$PYTHON_EXEC" -m flake8 app/ --max-line-length=100 --extend-ignore=E203,W503
    log_success "Linting completed!"
}

# Type check
type_check() {
    check_venv
    log_info "Running type checks..."
    "$PYTHON_EXEC" -m mypy app/ --ignore-missing-imports
    log_success "Type checking completed!"
}

# Show usage
show_usage() {
    echo "EcoCoder Agent Development Tool"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  install   - Set up development environment and install dependencies"
    echo "  start     - Start the agent in development mode"
    echo "  test      - Run tests"
    echo "  format    - Format code with Black and isort"
    echo "  lint      - Lint code with flake8"
    echo "  typecheck - Run type checking with mypy"
    echo "  all       - Run format, lint, typecheck, and test"
    echo "  help      - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 install   # First-time setup"
    echo "  $0 start     # Start development server"
    echo "  $0 format    # Format all Python files"
}

# Main command dispatcher
case "${1:-}" in
    install)
        install_deps
        ;;
    start)
        start_agent
        ;;
    test)
        run_tests
        ;;
    format)
        format_code
        ;;
    lint)
        lint_code
        ;;
    typecheck)
        type_check
        ;;
    all)
        format_code
        lint_code
        type_check
        run_tests
        ;;
    help|--help|-h)
        show_usage
        ;;
    "")
        show_usage
        ;;
    *)
        log_error "Unknown command: $1"
        show_usage
        exit 1
        ;;
esac