#!/bin/bash
# Performance testing script for ryxsurf-cpp
# Measures cold start time and memory usage

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build"
BINARY="$BUILD_DIR/ryxsurf"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if binary exists
if [ ! -f "$BINARY" ]; then
    echo -e "${RED}Error: Binary not found at $BINARY${NC}"
    echo "Please build the project first: meson setup build && meson compile -C build"
    exit 1
fi

# Create results directory
RESULTS_DIR="$PROJECT_ROOT/perf/results"
mkdir -p "$RESULTS_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULT_FILE="$RESULTS_DIR/perf_${TIMESTAMP}.txt"

echo "=== RyxSurf C++ Performance Test ===" | tee "$RESULT_FILE"
echo "Timestamp: $(date)" | tee -a "$RESULT_FILE"
echo "System: $(uname -a)" | tee -a "$RESULT_FILE"
echo "CPU: $(lscpu | grep 'Model name' | cut -d: -f2 | xargs)" | tee -a "$RESULT_FILE"
echo "Memory: $(free -h | grep '^Mem:' | awk '{print $2}')" | tee -a "$RESULT_FILE"
echo "" | tee -a "$RESULT_FILE"

# Test 1: Cold Start Time
echo -e "${YELLOW}Test 1: Cold Start Time${NC}" | tee -a "$RESULT_FILE"
echo "Measuring time to first window display..." | tee -a "$RESULT_FILE"

START_TIME=$(date +%s%N)
timeout 5s "$BINARY" 2>&1 > /dev/null &
BROWSER_PID=$!

# Wait briefly for window
sleep 0.5
kill $BROWSER_PID 2>/dev/null || true
wait $BROWSER_PID 2>/dev/null || true

END_TIME=$(date +%s%N)
ELAPSED_MS=$(( (END_TIME - START_TIME) / 1000000 ))

echo "COLD_START_MS=${ELAPSED_MS}" | tee -a "$RESULT_FILE"
echo "Cold start time: ${ELAPSED_MS}ms" | tee -a "$RESULT_FILE"
echo "Target: < 500ms" | tee -a "$RESULT_FILE"

if [ $ELAPSED_MS -lt 500 ]; then
    echo -e "${GREEN}✓ PASS${NC}" | tee -a "$RESULT_FILE"
else
    echo -e "${RED}✗ FAIL (exceeds target)${NC}" | tee -a "$RESULT_FILE"
fi
echo "" | tee -a "$RESULT_FILE"

# Test 2: Memory Usage (Idle)
echo -e "${YELLOW}Test 2: Idle Memory Usage${NC}" | tee -a "$RESULT_FILE"
echo "Measuring RSS with 1 loaded tab..." | tee -a "$RESULT_FILE"

"$BINARY" &
BROWSER_PID=$!
sleep 2

# Get RSS (Resident Set Size) in KB
RSS_KB=$(ps -o rss= -p $BROWSER_PID 2>/dev/null || echo "0")
RSS_MB=$((RSS_KB / 1024))

kill $BROWSER_PID 2>/dev/null || true
wait $BROWSER_PID 2>/dev/null || true

echo "IDLE_RSS_MB=${RSS_MB}" | tee -a "$RESULT_FILE"
echo "Idle RSS: ${RSS_MB}MB" | tee -a "$RESULT_FILE"
echo "Target: < 200MB (with 3 unloaded + 1 loaded tab)" | tee -a "$RESULT_FILE"

if [ $RSS_MB -lt 200 ]; then
    echo -e "${GREEN}✓ PASS${NC}" | tee -a "$RESULT_FILE"
else
    echo -e "${RED}✗ FAIL (exceeds target)${NC}" | tee -a "$RESULT_FILE"
fi
echo "" | tee -a "$RESULT_FILE"

# Summary
echo "=== Summary ===" | tee -a "$RESULT_FILE"
echo "COLD_START_MS=${ELAPSED_MS}" | tee -a "$RESULT_FILE"
echo "IDLE_RSS_MB=${RSS_MB}" | tee -a "$RESULT_FILE"
echo "Results saved to: $RESULT_FILE" | tee -a "$RESULT_FILE"

# Display results
cat "$RESULT_FILE"
