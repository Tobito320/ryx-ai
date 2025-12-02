#!/usr/bin/env bash
# Ryx AI - Local Environment Verification Script
# Validates Python, Node, Ollama, tests, and builds

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

VENV_DIR="$PROJECT_ROOT/venv"
WEB_DIR="$PROJECT_ROOT/ryx/interfaces/web"
REQUIRED_MODELS=("qwen2.5:1.5b" "deepseek-coder:6.7b" "qwen2.5-coder:14b")

# Summary tracking
declare -a RESULTS=()

log_result() {
    local status=$1 msg=$2
    if [[ $status -eq 0 ]]; then
        echo "✅ $msg"
        RESULTS+=("✅ $msg")
    else
        echo "❌ $msg"
        RESULTS+=("❌ $msg")
        return 1
    fi
}

print_summary() {
    echo ""
    echo "═══════════════════════════════════════"
    echo "          VERIFICATION SUMMARY"
    echo "═══════════════════════════════════════"
    for r in "${RESULTS[@]}"; do
        echo "$r"
    done
    echo "═══════════════════════════════════════"
}

# ─────────────────────────────────────────────────────────────────────────────
# 1. Python venv + dependencies
# ─────────────────────────────────────────────────────────────────────────────
setup_python() {
    if [[ ! -d "$VENV_DIR" ]]; then
        python3 -m venv "$VENV_DIR" >/dev/null 2>&1
    fi
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    pip install --quiet --upgrade pip >/dev/null 2>&1
    pip install --quiet -e ".[dev]" >/dev/null 2>&1
    log_result $? "Python venv + deps"
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. Node dependencies (web UI)
# ─────────────────────────────────────────────────────────────────────────────
setup_node() {
    if [[ ! -d "$WEB_DIR" ]]; then
        log_result 1 "Web UI directory missing"
        return 1
    fi
    cd "$WEB_DIR"
    if [[ ! -d "node_modules" ]]; then
        npm install --silent --legacy-peer-deps >/dev/null 2>&1
    fi
    cd "$PROJECT_ROOT"
    log_result $? "Node deps (web UI)"
}

# ─────────────────────────────────────────────────────────────────────────────
# 3. Ollama running + required models
# ─────────────────────────────────────────────────────────────────────────────
check_ollama() {
    if ! command -v ollama &>/dev/null; then
        log_result 1 "Ollama not installed"
        return 1
    fi

    # Check if Ollama service is running
    if ! curl -sf http://localhost:11434/api/version >/dev/null 2>&1; then
        log_result 1 "Ollama not running (start with: ollama serve)"
        return 1
    fi
    log_result 0 "Ollama service running"

    # Check required models
    local installed_models
    installed_models=$(ollama list 2>/dev/null | awk 'NR>1 {print $1}')
    local missing=0
    for model in "${REQUIRED_MODELS[@]}"; do
        if ! echo "$installed_models" | grep -qF "$model"; then
            echo "   ⚠️  Missing model: $model (run: ollama pull $model)"
            missing=1
        fi
    done
    if [[ $missing -eq 1 ]]; then
        log_result 1 "Some Ollama models missing"
        return 1
    fi
    log_result 0 "Required Ollama models present"
}

# ─────────────────────────────────────────────────────────────────────────────
# 4. Python tests (pytest)
# ─────────────────────────────────────────────────────────────────────────────
run_python_tests() {
    cd "$PROJECT_ROOT"
    source "$VENV_DIR/bin/activate"
    local test_output
    test_output=$(pytest tests/ -q --tb=no 2>&1)
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        log_result 0 "Python tests (pytest)"
    else
        # Extract summary line
        local summary
        summary=$(echo "$test_output" | grep -oE "[0-9]+ failed, [0-9]+ passed" | tail -1)
        log_result 1 "Python tests (pytest) [$summary]"
        if [[ "${VERBOSE:-0}" == "1" ]]; then
            echo "$test_output" | grep "^FAILED" | head -10
        fi
        return 1
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# 5. Frontend build
# ─────────────────────────────────────────────────────────────────────────────
build_frontend() {
    cd "$WEB_DIR"
    if CI=true npm run build --silent >/dev/null 2>&1; then
        log_result 0 "Frontend build (npm)"
    else
        log_result 1 "Frontend build (npm)"
        return 1
    fi
    cd "$PROJECT_ROOT"
}

# ─────────────────────────────────────────────────────────────────────────────
# 6. Smoke checks (optional, non-blocking)
# ─────────────────────────────────────────────────────────────────────────────
smoke_checks() {
    cd "$PROJECT_ROOT"
    source "$VENV_DIR/bin/activate"

    # CLI version check
    if python ryx_main.py --version >/dev/null 2>&1; then
        log_result 0 "CLI smoke test (--version)"
    else
        log_result 1 "CLI smoke test (--version)"
    fi

    # Check if API module imports correctly
    if python -c "from ryx_core.api import app" >/dev/null 2>&1; then
        log_result 0 "API module import check"
    else
        log_result 1 "API module import check"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
main() {
    echo "🔍 Ryx AI Local Verification"
    echo "─────────────────────────────────────────"
    echo ""

    local failed=0

    setup_python   || failed=1
    setup_node     || failed=1
    check_ollama   || failed=1
    run_python_tests || failed=1
    build_frontend || failed=1
    smoke_checks   || failed=1

    print_summary

    if [[ $failed -eq 1 ]]; then
        echo ""
        echo "❌ Some checks failed. Review issues above."
        exit 1
    else
        echo ""
        echo "🚀 All checks passed! Project is ready."
        exit 0
    fi
}

main "$@"
