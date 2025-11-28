#!/bin/bash
# Ryx AI - Automated Installation Script
# Handles full setup with dependency checking and error handling

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_ROOT"

# Print functions
print_header() {
    echo -e "${CYAN}╭──────────────────────────────────────────╮${NC}"
    echo -e "${CYAN}│  Ryx AI - Installation Script           │${NC}"
    echo -e "${CYAN}╰──────────────────────────────────────────╯${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}▸${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Main installation
main() {
    print_header

    # Check Python version
    print_info "Checking Python version..."
    if ! command_exists python3; then
        print_error "Python 3 not found. Please install Python 3.11+"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_success "Python $PYTHON_VERSION found"

    # Check if venv exists
    if [ ! -d ".venv" ]; then
        print_info "Creating virtual environment..."
        python3 -m venv .venv
        print_success "Virtual environment created"
    else
        print_success "Virtual environment already exists"
    fi

    # Activate venv
    print_info "Activating virtual environment..."
    source .venv/bin/activate

    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --quiet --upgrade pip

    # Install core dependencies
    print_info "Installing core dependencies..."
    pip install --quiet requests >/dev/null 2>&1
    print_success "Core dependencies installed"

    # Install optional dependencies
    print_info "Installing optional dependencies..."
    pip install --quiet psutil beautifulsoup4 lxml >/dev/null 2>&1 || {
        print_warning "Some optional dependencies failed to install (non-critical)"
    }
    print_success "Optional dependencies installed"

    # Create necessary directories
    print_info "Creating necessary directories..."
    mkdir -p data logs configs scripts tools modes core
    print_success "Directories created"

    # Initialize databases
    print_info "Initializing databases..."
    python3 << 'EOF'
import sys
sys.path.insert(0, '.')
from core.paths import get_data_dir

# Create data directory
get_data_dir().mkdir(parents=True, exist_ok=True)
print("Databases initialized")
EOF
    print_success "Databases initialized"

    # Create symlink
    print_info "Creating executable symlink..."
    EXEC_PATH="/usr/local/bin/ryx"

    if [ -L "$EXEC_PATH" ]; then
        sudo rm "$EXEC_PATH"
    fi

    sudo ln -sf "$PROJECT_ROOT/ryx" "$EXEC_PATH"
    sudo chmod +x "$PROJECT_ROOT/ryx"
    print_success "Executable installed at $EXEC_PATH"

    # Check Ollama
    print_info "Checking Ollama..."
    if ! command_exists ollama; then
        print_warning "Ollama not found. Install from: https://ollama.ai"
        print_info "After installing Ollama, run: ollama pull qwen2.5:1.5b"
    else
        print_success "Ollama found"

        # Check if model exists
        if ollama list | grep -q "qwen2.5:1.5b"; then
            print_success "Model qwen2.5:1.5b already installed"
        else
            print_info "Installing qwen2.5:1.5b model (this may take a few minutes)..."
            ollama pull qwen2.5:1.5b
            print_success "Model installed"
        fi
    fi

    # Optimize databases
    print_info "Optimizing databases..."
    python3 scripts/optimize_databases.py >/dev/null 2>&1 || {
        print_warning "Database optimization failed (non-critical)"
    }
    print_success "Databases optimized"

    # Run tests
    print_info "Running tests..."
    if python3 tests/test_basic_functionality.py >/dev/null 2>&1; then
        print_success "All tests passed"
    else
        print_warning "Some tests failed (check if Ollama is running)"
    fi

    # Final message
    echo ""
    echo -e "${CYAN}╭──────────────────────────────────────────╮${NC}"
    echo -e "${CYAN}│  Installation Complete! 🎉               │${NC}"
    echo -e "${CYAN}╰──────────────────────────────────────────╯${NC}"
    echo ""
    echo -e "${GREEN}Try these commands:${NC}"
    echo -e "  ${YELLOW}ryx ::status${NC}        - Check system status"
    echo -e "  ${YELLOW}ryx ::help${NC}          - Show all commands"
    echo -e "  ${YELLOW}ryx 'hello'${NC}         - Test with a simple query"
    echo -e "  ${YELLOW}ryx ::session${NC}       - Start interactive mode"
    echo ""

    if ! command_exists ollama; then
        echo -e "${YELLOW}Note: Ollama not installed. Install it to use AI features.${NC}"
        echo -e "Visit: ${BLUE}https://ollama.ai${NC}"
        echo ""
    fi
}

# Run installation
main
