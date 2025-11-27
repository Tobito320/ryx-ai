#!/bin/bash
# Ryx AI V2 - Migration Script
# Safely migrates from V1 to V2 with backup and rollback capability

set -e

# Colors
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
BLUE='\033[1;36m'
NC='\033[0m' # No Color

PROJECT_ROOT="$HOME/ryx-ai"
BACKUP_DIR="$HOME/ryx-ai-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/ryx-ai-v1-$TIMESTAMP"

echo ""
echo -e "${BLUE}╭─────────────────────────────────────────╮${NC}"
echo -e "${BLUE}│  Ryx AI V2 - Migration Tool             │${NC}"
echo -e "${BLUE}╰─────────────────────────────────────────╯${NC}"
echo ""

# Verify we're in the right directory
if [[ ! -d "$PROJECT_ROOT" ]]; then
    echo -e "${RED}✗${NC} Ryx AI not found at $PROJECT_ROOT"
    exit 1
fi

echo -e "${GREEN}✓${NC} Found Ryx AI at $PROJECT_ROOT"
echo ""

# Create backup
echo -e "${BLUE}▸${NC} Creating backup..."
mkdir -p "$BACKUP_DIR"

# Backup configs
if [[ -d "$PROJECT_ROOT/configs" ]]; then
    mkdir -p "$BACKUP_PATH/configs"
    cp -r "$PROJECT_ROOT/configs/"* "$BACKUP_PATH/configs/" 2>/dev/null || true
    echo -e "${GREEN}  ✓${NC} Backed up configs"
fi

# Backup data
if [[ -d "$PROJECT_ROOT/data" ]]; then
    mkdir -p "$BACKUP_PATH/data"
    cp -r "$PROJECT_ROOT/data/"* "$BACKUP_PATH/data/" 2>/dev/null || true
    echo -e "${GREEN}  ✓${NC} Backed up data"
fi

# Backup old core files
if [[ -f "$PROJECT_ROOT/core/ai_engine.py" ]]; then
    mkdir -p "$BACKUP_PATH/core"
    cp "$PROJECT_ROOT/core/ai_engine.py" "$BACKUP_PATH/core/" 2>/dev/null || true
    echo -e "${GREEN}  ✓${NC} Backed up core files"
fi

echo -e "${GREEN}✓${NC} Backup created at: $BACKUP_PATH"
echo ""

# Check V2 components
echo -e "${BLUE}▸${NC} Verifying V2 components..."

required_files=(
    "core/model_orchestrator.py"
    "core/meta_learner.py"
    "core/health_monitor.py"
    "core/task_manager.py"
    "core/ai_engine_v2.py"
)

missing=0
for file in "${required_files[@]}"; do
    if [[ ! -f "$PROJECT_ROOT/$file" ]]; then
        echo -e "${RED}  ✗${NC} Missing: $file"
        missing=1
    else
        echo -e "${GREEN}  ✓${NC} Found: $file"
    fi
done

if [[ $missing -eq 1 ]]; then
    echo ""
    echo -e "${RED}✗${NC} Migration incomplete - missing V2 components"
    echo "Please ensure all V2 files are in place"
    exit 1
fi

echo ""

# Update configs
echo -e "${BLUE}▸${NC} Updating configuration..."

# Copy V2 model config
if [[ -f "$PROJECT_ROOT/configs/models_v2.json" ]]; then
    # Backup old models.json
    if [[ -f "$PROJECT_ROOT/configs/models.json" ]]; then
        cp "$PROJECT_ROOT/configs/models.json" "$PROJECT_ROOT/configs/models.json.v1.bak"
    fi

    # Use V2 config
    cp "$PROJECT_ROOT/configs/models_v2.json" "$PROJECT_ROOT/configs/models.json"
    echo -e "${GREEN}  ✓${NC} Updated models.json to V2 format"
fi

echo ""

# Create required directories
echo -e "${BLUE}▸${NC} Creating required directories..."

dirs=(
    "$PROJECT_ROOT/data/state"
    "$PROJECT_ROOT/data/history"
)

for dir in "${dirs[@]}"; do
    if [[ ! -d "$dir" ]]; then
        mkdir -p "$dir"
        echo -e "${GREEN}  ✓${NC} Created: $dir"
    else
        echo -e "${YELLOW}  ○${NC} Already exists: $dir"
    fi
done

echo ""

# Check Python dependencies
echo -e "${BLUE}▸${NC} Checking Python dependencies..."

if [[ -f "$PROJECT_ROOT/.venv/bin/python" ]]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
    PIP="$PROJECT_ROOT/.venv/bin/pip"

    # Check if requests is installed
    if ! "$PYTHON" -c "import requests" 2>/dev/null; then
        echo -e "${YELLOW}  ↓${NC} Installing requests..."
        "$PIP" install requests > /dev/null 2>&1
        echo -e "${GREEN}  ✓${NC} Installed requests"
    else
        echo -e "${GREEN}  ✓${NC} requests already installed"
    fi
else
    echo -e "${YELLOW}  ⚠${NC} Virtual environment not found"
    echo "    Using system Python (may require dependencies)"
fi

echo ""

# Test import of V2 components
echo -e "${BLUE}▸${NC} Testing V2 components..."

cd "$PROJECT_ROOT"

test_imports() {
    cat > /tmp/test_ryx_v2.py << 'EOF'
import sys
sys.path.insert(0, '$PROJECT_ROOT')

try:
    from core.model_orchestrator import ModelOrchestrator
    print("✓ model_orchestrator")
except Exception as e:
    print(f"✗ model_orchestrator: {e}")
    sys.exit(1)

try:
    from core.meta_learner import MetaLearner
    print("✓ meta_learner")
except Exception as e:
    print(f"✗ meta_learner: {e}")
    sys.exit(1)

try:
    from core.health_monitor import HealthMonitor
    print("✓ health_monitor")
except Exception as e:
    print(f"✗ health_monitor: {e}")
    sys.exit(1)

try:
    from core.task_manager import TaskManager
    print("✓ task_manager")
except Exception as e:
    print(f"✗ task_manager: {e}")
    sys.exit(1)

try:
    from core.ai_engine_v2 import AIEngineV2
    print("✓ ai_engine_v2")
except Exception as e:
    print(f"✗ ai_engine_v2: {e}")
    sys.exit(1)

print("\nAll V2 components loaded successfully!")
EOF

    if [[ -f "$PROJECT_ROOT/.venv/bin/python" ]]; then
        "$PROJECT_ROOT/.venv/bin/python" /tmp/test_ryx_v2.py
    else
        python3 /tmp/test_ryx_v2.py
    fi
}

if test_imports; then
    echo -e "${GREEN}  ✓${NC} All V2 components tested successfully"
else
    echo -e "${RED}  ✗${NC} Component test failed"
    echo ""
    echo "Rollback instructions:"
    echo "  1. Restore configs: cp -r $BACKUP_PATH/configs/* $PROJECT_ROOT/configs/"
    echo "  2. Restore data: cp -r $BACKUP_PATH/data/* $PROJECT_ROOT/data/"
    exit 1
fi

echo ""

# Success!
echo -e "${GREEN}╭─────────────────────────────────────────╮${NC}"
echo -e "${GREEN}│  Migration Complete!                    │${NC}"
echo -e "${GREEN}╰─────────────────────────────────────────╯${NC}"
echo ""
echo "What changed:"
echo -e "  ${GREEN}✓${NC} V2 components installed and tested"
echo -e "  ${GREEN}✓${NC} Configuration updated for 3-tier models"
echo -e "  ${GREEN}✓${NC} Data directories created"
echo -e "  ${GREEN}✓${NC} Backup saved to: $BACKUP_PATH"
echo ""
echo "New features available:"
echo -e "  ${BLUE}●${NC} Lazy-loaded models (1.5B → 7B → 14B)"
echo -e "  ${BLUE}●${NC} Preference learning (use nvim!)"
echo -e "  ${BLUE}●${NC} Self-healing (auto-fixes Ollama)"
echo -e "  ${BLUE}●${NC} Graceful Ctrl+C (state save)"
echo ""
echo "Try it out:"
echo "  ryx 'hello world'       # Simple query (1.5B model)"
echo "  ryx ::health           # Check system health"
echo "  ryx ::preferences      # View learned preferences"
echo "  ryx ::session          # Interactive mode with Ctrl+C support"
echo ""
echo "Rollback if needed:"
echo "  cp -r $BACKUP_PATH/configs/* $PROJECT_ROOT/configs/"
echo "  cp -r $BACKUP_PATH/data/* $PROJECT_ROOT/data/"
echo ""
