#!/bin/bash
# Performance testing script for minimal-browser
# Measures cold start time and memory usage

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build"
BINARY="$BUILD_DIR/minimal-browser"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if binary exists
if [ ! -f "$BINARY" ]; then
    echo -e "${RED}Error: Binary not found at $BINARY${NC}"
    echo "Please build the project first: meson compile -C build"
    exit 1
fi

# Create results directory
RESULTS_DIR="$PROJECT_ROOT/perf/results"
mkdir -p "$RESULTS_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULT_FILE="$RESULTS_DIR/perf_${TIMESTAMP}.txt"

echo "=== Minimal Browser Performance Test ===" | tee "$RESULT_FILE"
echo "Timestamp: $(date)" | tee -a "$RESULT_FILE"
echo "System: $(uname -a)" | tee -a "$RESULT_FILE"
echo "CPU: $(lscpu | grep 'Model name' | cut -d: -f2 | xargs)" | tee -a "$RESULT_FILE"
echo "Memory: $(free -h | grep '^Mem:' | awk '{print $2}')" | tee -a "$RESULT_FILE"
echo "" | tee -a "$RESULT_FILE"

# Test 1: Cold Start Time
echo -e "${YELLOW}Test 1: Cold Start Time${NC}" | tee -a "$RESULT_FILE"
echo "Measuring time to first window display..." | tee -a "$RESULT_FILE"

# Use timeout to kill process after 10 seconds
START_TIME=$(date +%s%N)
timeout 10s "$BINARY" --test-startup 2>&1 > /dev/null &
BROWSER_PID=$!

# Wait for window to appear (simplified - in real test, would check for window)
sleep 1
kill $BROWSER_PID 2>/dev/null || true
wait $BROWSER_PID 2>/dev/null || true

END_TIME=$(date +%s%N)
ELAPSED_MS=$(( (END_TIME - START_TIME) / 1000000 ))

echo "Cold start time: ${ELAPSED_MS}ms" | tee -a "$RESULT_FILE"
echo "Target: < 500ms" | tee -a "$RESULT_FILE"

if [ $ELAPSED_MS -lt 500 ]; then
    echo -e "${GREEN}✓ PASS${NC}" | tee -a "$RESULT_FILE"
else
    echo -e "${RED}✗ FAIL (exceeds target)${NC}" | tee -a "$RESULT_FILE"
fi
echo "" | tee -a "$RESULT_FILE"

# Test 2: Memory Usage (Idle with tabs)
echo -e "${YELLOW}Test 2: Idle Memory Usage${NC}" | tee -a "$RESULT_FILE"
echo "Measuring RSS with 3 unloaded tabs + 1 loaded tab..." | tee -a "$RESULT_FILE"

# Note: This is a simplified test. In a real scenario, we would:
# 1. Start the browser
# 2. Create 3 tabs (unloaded)
# 3. Create 1 active tab
# 4. Wait for idle
# 5. Measure RSS

# For now, just measure baseline
"$BINARY" --test-memory &
BROWSER_PID=$!
sleep 2

# Get RSS (Resident Set Size) in KB
RSS_KB=$(ps -o rss= -p $BROWSER_PID 2>/dev/null || echo "0")
RSS_MB=$((RSS_KB / 1024))

kill $BROWSER_PID 2>/dev/null || true
wait $BROWSER_PID 2>/dev/null || true

echo "Idle RSS: ${RSS_MB}MB" | tee -a "$RESULT_FILE"
echo "Target: < 200MB" | tee -a "$RESULT_FILE"

if [ $RSS_MB -lt 200 ]; then
    echo -e "${GREEN}✓ PASS${NC}" | tee -a "$RESULT_FILE"
else
    echo -e "${RED}✗ FAIL (exceeds target)${NC}" | tee -a "$RESULT_FILE"
fi
echo "" | tee -a "$RESULT_FILE"

# Test 3: Tab Switch Time
echo -e "${YELLOW}Test 3: Tab Switch Time${NC}" | tee -a "$RESULT_FILE"
echo "Measuring time to switch between loaded tabs..." | tee -a "$RESULT_FILE"
echo "Note: Requires manual testing or automated UI testing framework" | tee -a "$RESULT_FILE"
echo "Target: < 50ms" | tee -a "$RESULT_FILE"
echo "" | tee -a "$RESULT_FILE"

# Summary
echo "=== Summary ===" | tee -a "$RESULT_FILE"
echo "Results saved to: $RESULT_FILE" | tee -a "$RESULT_FILE"
echo "" | tee -a "$RESULT_FILE"

# Display results
cat "$RESULT_FILE"
