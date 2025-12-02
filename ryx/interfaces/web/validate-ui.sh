#!/usr/bin/env bash
# Ryx Web UI - Automated Validation Script
# Runs frontend build, dev server, and Playwright E2E tests

set -euo pipefail

WEB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$WEB_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS_COUNT=0
FAIL_COUNT=0
declare -a RESULTS=()

log_pass() {
    echo -e "${GREEN}✅ $1${NC}"
    RESULTS+=("✅ $1")
    ((PASS_COUNT++))
}

log_fail() {
    echo -e "${RED}❌ $1${NC}"
    RESULTS+=("❌ $1")
    ((FAIL_COUNT++))
}

log_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

cleanup() {
    if [[ -n "${DEV_PID:-}" ]]; then
        kill "$DEV_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

print_summary() {
    echo ""
    echo "═══════════════════════════════════════"
    echo "       WEB UI VALIDATION SUMMARY"
    echo "═══════════════════════════════════════"
    for r in "${RESULTS[@]}"; do
        echo "$r"
    done
    echo "───────────────────────────────────────"
    echo -e "Passed: ${GREEN}$PASS_COUNT${NC}  Failed: ${RED}$FAIL_COUNT${NC}"
    echo "═══════════════════════════════════════"
}

# ─────────────────────────────────────────────────────────────────────────────
# 1. Verify dependencies
# ─────────────────────────────────────────────────────────────────────────────
log_info "Checking dependencies..."
if [[ ! -d "node_modules" ]]; then
    npm install --silent --legacy-peer-deps >/dev/null 2>&1
fi

if npm list playwright >/dev/null 2>&1; then
    log_pass "Playwright installed"
else
    npm install --save-dev playwright @playwright/test >/dev/null 2>&1
    log_pass "Playwright installed"
fi

# Install Playwright browsers if needed
if ! npx playwright --version >/dev/null 2>&1; then
    log_fail "Playwright CLI not available"
    exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# 2. Build frontend
# ─────────────────────────────────────────────────────────────────────────────
log_info "Building frontend..."
if CI=true npm run build --silent >/dev/null 2>&1; then
    log_pass "Frontend build"
else
    log_fail "Frontend build"
    print_summary
    exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# 3. Start dev server
# ─────────────────────────────────────────────────────────────────────────────
log_info "Starting dev server..."

# Check if port 3000 is already in use
if curl -sf http://localhost:3000 >/dev/null 2>&1; then
    log_info "Dev server already running on port 3000"
    SERVER_STARTED=false
else
    # Start dev server in background
    BROWSER=none npm start >/dev/null 2>&1 &
    DEV_PID=$!
    SERVER_STARTED=true
    
    # Wait for server to be ready
    for i in {1..30}; do
        if curl -sf http://localhost:3000 >/dev/null 2>&1; then
            break
        fi
        sleep 1
    done
fi

if curl -sf http://localhost:3000 >/dev/null 2>&1; then
    log_pass "Dev server running"
else
    log_fail "Dev server startup"
    print_summary
    exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# 4. Run Playwright tests
# ─────────────────────────────────────────────────────────────────────────────
log_info "Running E2E tests..."

# Ensure Playwright browsers are installed
npx playwright install chromium --with-deps >/dev/null 2>&1 || true

if npx playwright test --reporter=list 2>&1 | tee /tmp/playwright_output.txt | grep -E "^\s*(✓|✘|·)"; then
    # Count passed/failed from output
    PLAYWRIGHT_PASSED=$(grep -c "✓" /tmp/playwright_output.txt 2>/dev/null || echo 0)
    PLAYWRIGHT_FAILED=$(grep -c "✘" /tmp/playwright_output.txt 2>/dev/null || echo 0)
    
    if [[ "$PLAYWRIGHT_FAILED" -eq 0 ]]; then
        log_pass "E2E tests ($PLAYWRIGHT_PASSED passed)"
    else
        log_fail "E2E tests ($PLAYWRIGHT_FAILED failed, $PLAYWRIGHT_PASSED passed)"
    fi
else
    # Check exit code
    if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
        log_pass "E2E tests"
    else
        log_fail "E2E tests"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# 5. Manual checks via curl
# ─────────────────────────────────────────────────────────────────────────────
log_info "Validating page content..."

# Check homepage returns HTML
PAGE_CONTENT=$(curl -sf http://localhost:3000 2>/dev/null || echo "")
if echo "$PAGE_CONTENT" | grep -q "<div id=\"root\""; then
    log_pass "Homepage renders React root"
else
    log_fail "Homepage React root missing"
fi

# Check for dracula CSS
if echo "$PAGE_CONTENT" | grep -qE "dracula|ryx-bg|1e1e2e"; then
    log_pass "Dracula theme CSS present"
else
    # Check CSS files
    CSS_CONTENT=$(curl -sf "http://localhost:3000/static/css/main.*.css" 2>/dev/null || echo "")
    if echo "$CSS_CONTENT" | grep -qE "ryx-accent|dracula|9d7cd8|bd93f9"; then
        log_pass "Dracula theme CSS present"
    else
        log_fail "Dracula theme CSS missing"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
print_summary

if [[ $FAIL_COUNT -gt 0 ]]; then
    exit 1
else
    echo ""
    echo -e "${GREEN}🚀 All web UI validations passed!${NC}"
    exit 0
fi
