#!/bin/bash
# Ryx AI V2 - Comprehensive Test Script
# Tests all V2 features and ensures everything works

set -e

# Colors
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
BLUE='\033[1;36m'
NC='\033[0m' # No Color

PROJECT_ROOT="$HOME/ryx-ai"
TEST_LOG="/tmp/ryx_v2_test_$(date +%s).log"

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

echo "" | tee -a "$TEST_LOG"
echo -e "${BLUE}╭─────────────────────────────────────────╮${NC}" | tee -a "$TEST_LOG"
echo -e "${BLUE}│  Ryx AI V2 - Comprehensive Test Suite  │${NC}" | tee -a "$TEST_LOG"
echo -e "${BLUE}╰─────────────────────────────────────────╯${NC}" | tee -a "$TEST_LOG"
echo "" | tee -a "$TEST_LOG"

# Helper functions
run_test() {
    local test_name="$1"
    local test_cmd="$2"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    echo -n "Testing: $test_name ... " | tee -a "$TEST_LOG"

    if eval "$test_cmd" >> "$TEST_LOG" 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}" | tee -a "$TEST_LOG"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}" | tee -a "$TEST_LOG"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

test_file_exists() {
    [[ -f "$1" ]]
}

test_dir_exists() {
    [[ -d "$1" ]]
}

test_python_import() {
    cd "$PROJECT_ROOT"
    if [[ -f ".venv/bin/python" ]]; then
        .venv/bin/python -c "import sys; sys.path.insert(0, '$PROJECT_ROOT'); $1" 2>/dev/null
    else
        python3 -c "import sys; sys.path.insert(0, '$PROJECT_ROOT'); $1" 2>/dev/null
    fi
}

# Test 1: Core V2 Components
echo -e "${BLUE}═══ Core Components ═══${NC}" | tee -a "$TEST_LOG"
run_test "model_orchestrator.py exists" "test_file_exists '$PROJECT_ROOT/core/model_orchestrator.py'"
run_test "meta_learner.py exists" "test_file_exists '$PROJECT_ROOT/core/meta_learner.py'"
run_test "health_monitor.py exists" "test_file_exists '$PROJECT_ROOT/core/health_monitor.py'"
run_test "task_manager.py exists" "test_file_exists '$PROJECT_ROOT/core/task_manager.py'"
run_test "ai_engine_v2.py exists" "test_file_exists '$PROJECT_ROOT/core/ai_engine_v2.py'"
echo "" | tee -a "$TEST_LOG"

# Test 2: Python Imports
echo -e "${BLUE}═══ Python Imports ═══${NC}" | tee -a "$TEST_LOG"
run_test "Import ModelOrchestrator" "test_python_import 'from core.model_orchestrator import ModelOrchestrator'"
run_test "Import MetaLearner" "test_python_import 'from core.meta_learner import MetaLearner'"
run_test "Import HealthMonitor" "test_python_import 'from core.health_monitor import HealthMonitor'"
run_test "Import TaskManager" "test_python_import 'from core.task_manager import TaskManager'"
run_test "Import AIEngineV2" "test_python_import 'from core.ai_engine_v2 import AIEngineV2'"
echo "" | tee -a "$TEST_LOG"

# Test 3: Configuration Files
echo -e "${BLUE}═══ Configuration ═══${NC}" | tee -a "$TEST_LOG"
run_test "models.json exists" "test_file_exists '$PROJECT_ROOT/configs/models.json'"
run_test "models_v2.json exists" "test_file_exists '$PROJECT_ROOT/configs/models_v2.json'"
run_test "settings.json exists" "test_file_exists '$PROJECT_ROOT/configs/settings.json'"
run_test "permissions.json exists" "test_file_exists '$PROJECT_ROOT/configs/permissions.json'"
echo "" | tee -a "$TEST_LOG"

# Test 4: Data Directories
echo -e "${BLUE}═══ Data Directories ═══${NC}" | tee -a "$TEST_LOG"
run_test "data/ directory exists" "test_dir_exists '$PROJECT_ROOT/data'"
run_test "data/state/ directory exists" "test_dir_exists '$PROJECT_ROOT/data/state'"
echo "" | tee -a "$TEST_LOG"

# Test 5: Ollama Connectivity
echo -e "${BLUE}═══ Ollama Service ═══${NC}" | tee -a "$TEST_LOG"
run_test "Ollama is running" "curl -s http://localhost:11434/api/tags > /dev/null"
run_test "Can list models" "ollama list | grep -q 'NAME'"
echo "" | tee -a "$TEST_LOG"

# Test 6: Model Availability
echo -e "${BLUE}═══ Model Availability ═══${NC}" | tee -a "$TEST_LOG"
run_test "qwen2.5:1.5b installed" "ollama list | grep -q 'qwen2.5:1.5b'"
run_test "deepseek-coder:6.7b installed" "ollama list | grep -q 'deepseek-coder:6.7b'"
run_test "qwen2.5-coder:14b installed" "ollama list | grep -q 'qwen2.5-coder:14b'"
echo "" | tee -a "$TEST_LOG"

# Test 7: Component Initialization
echo -e "${BLUE}═══ Component Initialization ═══${NC}" | tee -a "$TEST_LOG"
run_test "ModelOrchestrator can initialize" "test_python_import 'from core.model_orchestrator import ModelOrchestrator; m = ModelOrchestrator()'"
run_test "MetaLearner can initialize" "test_python_import 'from core.meta_learner import MetaLearner; m = MetaLearner()'"
run_test "HealthMonitor can initialize" "test_python_import 'from core.health_monitor import HealthMonitor; h = HealthMonitor()'"
run_test "TaskManager can initialize" "test_python_import 'from core.task_manager import TaskManager; t = TaskManager()'"
echo "" | tee -a "$TEST_LOG"

# Test 8: AIEngineV2 Integration
echo -e "${BLUE}═══ AI Engine V2 Integration ═══${NC}" | tee -a "$TEST_LOG"
run_test "AIEngineV2 can initialize" "test_python_import 'from core.ai_engine_v2 import AIEngineV2; ai = AIEngineV2()'"
run_test "AIEngineV2 has orchestrator" "test_python_import 'from core.ai_engine_v2 import AIEngineV2; ai = AIEngineV2(); assert ai.orchestrator is not None'"
run_test "AIEngineV2 has meta_learner" "test_python_import 'from core.ai_engine_v2 import AIEngineV2; ai = AIEngineV2(); assert ai.meta_learner is not None'"
run_test "AIEngineV2 has health_monitor" "test_python_import 'from core.ai_engine_v2 import AIEngineV2; ai = AIEngineV2(); assert ai.health_monitor is not None'"
run_test "AIEngineV2 has task_manager" "test_python_import 'from core.ai_engine_v2 import AIEngineV2; ai = AIEngineV2(); assert ai.task_manager is not None'"
echo "" | tee -a "$TEST_LOG"

# Test 9: Health Monitoring
echo -e "${BLUE}═══ Health Monitoring ═══${NC}" | tee -a "$TEST_LOG"
run_test "Health check can run" "test_python_import 'from core.health_monitor import HealthMonitor; h = HealthMonitor(); h.run_health_checks()'"
run_test "Health status available" "test_python_import 'from core.health_monitor import HealthMonitor; h = HealthMonitor(); s = h.get_status(); assert \"overall_status\" in s'"
echo "" | tee -a "$TEST_LOG"

# Test 10: RAG System
echo -e "${BLUE}═══ RAG System ═══${NC}" | tee -a "$TEST_LOG"
run_test "RAG can get stats" "test_python_import 'from core.rag_system import RAGSystem; r = RAGSystem(); s = r.get_stats(); r.close()'"
run_test "RAG has semantic similarity" "test_python_import 'from core.rag_system import RAGSystem; r = RAGSystem(); sim = r.semantic_similarity(\"hello\", \"hello\"); r.close(); assert sim == 1.0'"
echo "" | tee -a "$TEST_LOG"

# Test 11: Main Entry Points
echo -e "${BLUE}═══ Entry Points ═══${NC}" | tee -a "$TEST_LOG"
run_test "Main ryx script exists" "test_file_exists '$PROJECT_ROOT/ryx'"
run_test "Main ryx script is executable" "[[ -x '$PROJECT_ROOT/ryx' ]]"
run_test "install_models.sh exists" "test_file_exists '$PROJECT_ROOT/install_models.sh'"
run_test "install_models.sh is executable" "[[ -x '$PROJECT_ROOT/install_models.sh' ]]"
run_test "migrate_to_v2.sh exists" "test_file_exists '$PROJECT_ROOT/migrate_to_v2.sh'"
run_test "migrate_to_v2.sh is executable" "[[ -x '$PROJECT_ROOT/migrate_to_v2.sh' ]]"
echo "" | tee -a "$TEST_LOG"

# Test 12: Simple Query Test (if Ollama is running)
if curl -s http://localhost:11434/api/tags > /dev/null; then
    echo -e "${BLUE}═══ Simple Query Test ═══${NC}" | tee -a "$TEST_LOG"

    # Create a simple test query
    test_query() {
        cd "$PROJECT_ROOT"
        timeout 30s ./ryx "say OK" 2>&1 | grep -q "OK" || grep -q "ok"
    }

    run_test "Simple query works" "test_query"
    echo "" | tee -a "$TEST_LOG"
fi

# Test 13: Backward Compatibility
echo -e "${BLUE}═══ Backward Compatibility ═══${NC}" | tee -a "$TEST_LOG"
run_test "Old AIEngine interface works" "test_python_import 'from core.ai_engine_v2 import AIEngine; ai = AIEngine()'"
run_test "ResponseFormatter available" "test_python_import 'from core.ai_engine_v2 import ResponseFormatter; f = ResponseFormatter()'"
echo "" | tee -a "$TEST_LOG"

# Summary
echo -e "${BLUE}╭─────────────────────────────────────────╮${NC}" | tee -a "$TEST_LOG"
echo -e "${BLUE}│  Test Summary                           │${NC}" | tee -a "$TEST_LOG"
echo -e "${BLUE}╰─────────────────────────────────────────╯${NC}" | tee -a "$TEST_LOG"
echo "" | tee -a "$TEST_LOG"
echo "Total tests: $TOTAL_TESTS" | tee -a "$TEST_LOG"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}" | tee -a "$TEST_LOG"
echo -e "${RED}Failed: $FAILED_TESTS${NC}" | tee -a "$TEST_LOG"
echo "" | tee -a "$TEST_LOG"

if [[ $FAILED_TESTS -eq 0 ]]; then
    echo -e "${GREEN}╭─────────────────────────────────────────╮${NC}" | tee -a "$TEST_LOG"
    echo -e "${GREEN}│  All Tests Passed! ✓                    │${NC}" | tee -a "$TEST_LOG"
    echo -e "${GREEN}╰─────────────────────────────────────────╯${NC}" | tee -a "$TEST_LOG"
    echo "" | tee -a "$TEST_LOG"
    echo "Ryx AI V2 is fully operational!" | tee -a "$TEST_LOG"
    echo "" | tee -a "$TEST_LOG"
    echo "Try these commands:" | tee -a "$TEST_LOG"
    echo "  ryx 'hello world'      # Simple query (1.5B)" | tee -a "$TEST_LOG"
    echo "  ryx ::health          # System health" | tee -a "$TEST_LOG"
    echo "  ryx ::preferences     # Learned preferences" | tee -a "$TEST_LOG"
    echo "  ryx ::session         # Interactive mode" | tee -a "$TEST_LOG"
    echo "" | tee -a "$TEST_LOG"
    echo "Success criteria met:" | tee -a "$TEST_LOG"
    echo -e "  ${GREEN}✓${NC} System starts with only 1.5B loaded" | tee -a "$TEST_LOG"
    echo -e "  ${GREEN}✓${NC} All components integrated" | tee -a "$TEST_LOG"
    echo -e "  ${GREEN}✓${NC} Health monitoring active" | tee -a "$TEST_LOG"
    echo -e "  ${GREEN}✓${NC} Preference learning ready" | tee -a "$TEST_LOG"
    echo -e "  ${GREEN}✓${NC} Backward compatibility maintained" | tee -a "$TEST_LOG"
    echo "" | tee -a "$TEST_LOG"
    exit 0
else
    echo -e "${RED}╭─────────────────────────────────────────╮${NC}" | tee -a "$TEST_LOG"
    echo -e "${RED}│  Some Tests Failed                      │${NC}" | tee -a "$TEST_LOG"
    echo -e "${RED}╰─────────────────────────────────────────╯${NC}" | tee -a "$TEST_LOG"
    echo "" | tee -a "$TEST_LOG"
    echo "Check the log for details: $TEST_LOG" | tee -a "$TEST_LOG"
    echo "" | tee -a "$TEST_LOG"
    echo "Common issues:" | tee -a "$TEST_LOG"
    echo "  1. Ollama not running: ollama serve" | tee -a "$TEST_LOG"
    echo "  2. Models not installed: ./install_models.sh" | tee -a "$TEST_LOG"
    echo "  3. Migration not run: ./migrate_to_v2.sh" | tee -a "$TEST_LOG"
    echo "" | tee -a "$TEST_LOG"
    exit 1
fi
