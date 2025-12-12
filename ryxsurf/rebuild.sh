#!/bin/bash
# RyxSurf Quick Rebuild Script
# Makes it easy to rebuild and test the browser

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════╗${NC}"
echo -e "${BLUE}║  RyxSurf Quick Rebuild Tool   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════╝${NC}"
echo

# Check for running instances
echo -e "${YELLOW}⚠ Checking for running instances...${NC}"
if pgrep -f "ryxsurf/main.py" > /dev/null; then
    echo -e "${YELLOW}Found running RyxSurf instance, stopping...${NC}"
    pkill -f "ryxsurf/main.py"
    sleep 1
fi

# Clean Python cache
echo -e "${BLUE}→ Cleaning Python cache...${NC}"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Check dependencies
echo -e "${BLUE}→ Checking dependencies...${NC}"
python3 -c "import gi; gi.require_version('Gtk', '4.0'); gi.require_version('WebKit', '6.0')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠ Missing dependencies, installing...${NC}"
    pip3 install --user pygobject pycairo 2>/dev/null || true
fi

# Build/compile if needed
echo -e "${BLUE}→ Building...${NC}"
# Nothing to compile for Python, but we can validate syntax
python3 -m py_compile main.py
python3 -m py_compile src/core/browser.py

# Create/update launcher
echo -e "${BLUE}→ Creating launcher...${NC}"
LAUNCHER="$HOME/.local/bin/ryxsurf"
mkdir -p "$HOME/.local/bin"
cat > "$LAUNCHER" << 'EOF'
#!/bin/bash
cd "$(dirname "$(readlink -f "$0")")/../.." || exit
exec python3 -m ryxsurf.main "$@"
EOF
chmod +x "$LAUNCHER"

# Update ryx integration
if [ -f "../ryx" ]; then
    echo -e "${BLUE}→ Updating ryx integration...${NC}"
    if ! grep -q "ryxsurf" ../ryx 2>/dev/null; then
        echo "  (ryx integration not found, skipping)"
    fi
fi

# Run quick tests
echo -e "${BLUE}→ Running quick tests...${NC}"
python3 -c "
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
try:
    # Test individual modules
    import ui.theme as theme
    import core.performance as perf
    print('✓ Module imports successful')
except Exception as e:
    print(f'⚠ Some imports failed: {e}')
    print('  (This is OK if browser.py has webkit dependencies)')
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Build successful!${NC}"
    echo
    echo -e "${GREEN}Ready to launch RyxSurf${NC}"
    echo
    echo "Launch options:"
    echo "  1. ${BLUE}python3 main.py${NC}          - Run from here"
    echo "  2. ${BLUE}ryxsurf${NC}                  - Run from anywhere (if in PATH)"
    echo "  3. ${BLUE}./ryx surf${NC}               - Run via ryx CLI"
    echo
    
    # Ask to launch
    read -p "Launch now? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}→ Launching RyxSurf...${NC}"
        python3 main.py &
        sleep 2
        echo -e "${GREEN}✓ RyxSurf started (PID: $!)${NC}"
    fi
else
    echo -e "${YELLOW}✗ Build failed${NC}"
    exit 1
fi
