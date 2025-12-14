#!/bin/bash
# Quick rebuild script for RyxSurf

set -e

echo "🔨 Quick rebuilding RyxSurf..."

# Change to ryxsurf directory
cd "$(dirname "$0")"

# Make scripts executable
chmod +x main_optimized.py
chmod +x launch.sh 2>/dev/null || true

# Create symlink if needed
if [ ! -f "ryxsurf_fast" ]; then
    ln -s main_optimized.py ryxsurf_fast
    chmod +x ryxsurf_fast
fi

echo "✓ Rebuild complete!"
echo ""
echo "Run with: ./ryxsurf_fast"
echo "or: python3 main_optimized.py"
