#!/bin/bash
# Ryx AI V2 - Model Installation Script
# Installs and tests the 3-tier model setup

set -e

# Colors
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
BLUE='\033[1;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}╭─────────────────────────────────────────╮${NC}"
echo -e "${BLUE}│  Ryx AI V2 - Model Installation        │${NC}"
echo -e "${BLUE}╰─────────────────────────────────────────╯${NC}"
echo ""

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo -e "${RED}✗${NC} Ollama not found"
    echo ""
    echo "Install Ollama from: https://ollama.ai"
    echo "Or run: curl https://ollama.ai/install.sh | sh"
    exit 1
fi

echo -e "${GREEN}✓${NC} Ollama found"

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠${NC} Ollama not running, attempting to start..."

    # Try to start Ollama
    if systemctl --user is-active --quiet ollama 2>/dev/null; then
        systemctl --user restart ollama
    else
        echo ""
        echo "Please start Ollama manually:"
        echo "  ollama serve"
        echo ""
        echo "Then run this script again"
        exit 1
    fi

    # Wait for Ollama to start
    sleep 2

    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${RED}✗${NC} Failed to start Ollama"
        exit 1
    fi
fi

echo -e "${GREEN}✓${NC} Ollama is running"
echo ""

# Model configuration
declare -A MODELS
MODELS[ultra_fast]="qwen2.5:1.5b"
MODELS[balanced]="deepseek-coder:6.7b"
MODELS[powerful]="qwen2.5-coder:14b"

# Check and install models
install_model() {
    local tier=$1
    local model=$2

    echo -e "${BLUE}▸${NC} Checking $tier tier: $model"

    # Check if model exists
    if ollama list | grep -q "^${model}"; then
        echo -e "${GREEN}  ✓${NC} Already installed"
        return 0
    fi

    echo -e "${YELLOW}  ↓${NC} Installing $model (this may take a while)..."

    if ollama pull "$model"; then
        echo -e "${GREEN}  ✓${NC} Successfully installed"
    else
        echo -e "${RED}  ✗${NC} Failed to install"
        return 1
    fi
}

# Test model
test_model() {
    local model=$1

    echo -e "${BLUE}  ▸${NC} Testing $model..."

    response=$(ollama run "$model" "Say 'OK' if you can hear me" 2>&1 | head -1)

    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}  ✓${NC} Test passed"
        return 0
    else
        echo -e "${RED}  ✗${NC} Test failed"
        return 1
    fi
}

# Install all models
echo "Installing 3-tier model setup:"
echo ""

# Tier 1: Ultra-fast (always loaded)
install_model "Ultra-fast (1.5B)" "${MODELS[ultra_fast]}"
test_model "${MODELS[ultra_fast]}"
echo ""

# Tier 2: Balanced (load on-demand)
install_model "Balanced (6.7B)" "${MODELS[balanced]}"
test_model "${MODELS[balanced]}"
echo ""

# Tier 3: Powerful (rare use)
install_model "Powerful (14B)" "${MODELS[powerful]}"
test_model "${MODELS[powerful]}"
echo ""

# Summary
echo -e "${GREEN}╭─────────────────────────────────────────╮${NC}"
echo -e "${GREEN}│  Installation Complete                  │${NC}"
echo -e "${GREEN}╰─────────────────────────────────────────╯${NC}"
echo ""
echo "Installed models:"
echo -e "  ${GREEN}●${NC} ${MODELS[ultra_fast]} (ultra-fast, always loaded)"
echo -e "  ${YELLOW}○${NC} ${MODELS[balanced]} (balanced, on-demand)"
echo -e "  ${YELLOW}○${NC} ${MODELS[powerful]} (powerful, rare)"
echo ""
echo "Next steps:"
echo "  1. Run migration: ./migrate_to_v2.sh"
echo "  2. Test system: ./test_v2.sh"
echo "  3. Start using: ryx 'hello world'"
echo ""
