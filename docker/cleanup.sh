#!/bin/bash
# Ryx AI - Auto-Cleanup Script
# Runs daily to keep system lean

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╭──────────────────────────────────────╮${NC}"
echo -e "${BLUE}│  Ryx AI - Auto Cleanup              │${NC}"
echo -e "${BLUE}╰──────────────────────────────────────╯${NC}"
echo

CLEANED_SPACE=0

# ================================
# 1. Clean Docker build cache
# ================================
echo -e "${YELLOW}▸${NC} Cleaning Docker build cache..."

BEFORE=$(docker system df --format "{{.Size}}" | head -1 || echo "0B")

docker builder prune -f --filter "until=24h" > /dev/null 2>&1

AFTER=$(docker system df --format "{{.Size}}" | head -1 || echo "0B")

echo -e "${GREEN}✓${NC} Docker build cache cleaned"

# ================================
# 2. Remove old Docker images
# ================================
echo -e "${YELLOW}▸${NC} Removing old Docker images..."

# Remove dangling images
docker image prune -f > /dev/null 2>&1

# Remove images older than 30 days
docker images --format "{{.Repository}}:{{.Tag}}|{{.CreatedAt}}" | \
while IFS='|' read -r image created; do
    # Calculate age in days
    created_epoch=$(date -d "$created" +%s 2>/dev/null || date -j -f "%Y-%m-%d" "$created" +%s 2>/dev/null || echo 0)
    now_epoch=$(date +%s)
    age_days=$(( (now_epoch - created_epoch) / 86400 ))
    
    if [ $age_days -gt 30 ]; then
        echo "  Removing old image: $image (${age_days} days old)"
        docker rmi "$image" 2>/dev/null || true
    fi
done

echo -e "${GREEN}✓${NC} Old images removed"

# ================================
# 3. Clean Ryx data cache
# ================================
echo -e "${YELLOW}▸${NC} Cleaning Ryx cache..."

RYX_DATA="$HOME/ryx-ai/data"

if [ -d "$RYX_DATA/cache" ]; then
    # Remove cache files older than 7 days
    find "$RYX_DATA/cache" -type f -mtime +7 -delete
    
    # Count removed
    echo -e "${GREEN}✓${NC} Ryx cache cleaned"
fi

# ================================
# 4. Trim RAG database
# ================================
echo -e "${YELLOW}▸${NC} Optimizing RAG database..."

python3 << 'PYTHON'
from pathlib import Path
import sqlite3
import sys

db_path = Path.home() / "ryx-ai" / "data" / "rag_knowledge.db"

if db_path.exists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Remove old cached responses (>30 days, low use count)
    cursor.execute("""
        DELETE FROM quick_responses
        WHERE datetime(created_at) < datetime('now', '-30 days')
        AND use_count < 3
    """)
    
    deleted = cursor.rowcount
    
    # Vacuum to reclaim space
    conn.execute("VACUUM")
    conn.commit()
    conn.close()
    
    print(f"Removed {deleted} old cache entries")
else:
    print("Database not found (OK if first run)")
PYTHON

echo -e "${GREEN}✓${NC} Database optimized"

# ================================
# 5. Compress old logs
# ================================
echo -e "${YELLOW}▸${NC} Compressing old logs..."

if [ -d "$RYX_DATA/history" ]; then
    find "$RYX_DATA/history" -name "*.log" -mtime +7 -exec gzip {} \; 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Logs compressed"
fi

# ================================
# 6. Summary
# ================================
echo
echo -e "${BLUE}╭──────────────────────────────────────╮${NC}"
echo -e "${BLUE}│  Cleanup Summary                     │${NC}"
echo -e "${BLUE}╰──────────────────────────────────────╯${NC}"
echo

# Get current disk usage
DOCKER_SIZE=$(docker system df --format "{{.Size}}" | head -1 || echo "0B")
RYX_SIZE=$(du -sh "$HOME/ryx-ai" 2>/dev/null | cut -f1 || echo "0")

echo -e "${GREEN}✓${NC} Docker system: $DOCKER_SIZE"
echo -e "${GREEN}✓${NC} Ryx data: $RYX_SIZE"
echo

echo -e "${GREEN}✓${NC} Cleanup complete!"
echo

# ================================
# 7. Schedule next run
# ================================
# Add to crontab if not already scheduled
if ! crontab -l 2>/dev/null | grep -q "ryx.*cleanup"; then
    echo
    echo -e "${YELLOW}Would you like to schedule daily auto-cleanup? (y/n)${NC}"
    read -r response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        # Add to crontab (3 AM daily)
        (crontab -l 2>/dev/null; echo "0 3 * * * $HOME/ryx-ai/docker/cleanup.sh >> $HOME/ryx-ai/data/cleanup.log 2>&1") | crontab -
        echo -e "${GREEN}✓${NC} Scheduled daily cleanup at 3 AM"
    fi
fi