# Ryx AI V2 - Quick Start Guide

## Installation (3 Commands, ~17 Minutes)

```bash
cd ~/ryx-ai

# Step 1: Install models (~15 min)
./install_models.sh

# Step 2: Migrate to V2 (<1 min)
./migrate_to_v2.sh

# Step 3: Test everything (~1 min)
./test_v2.sh
```

## Quick Test

```bash
# Simple query (should use 1.5B model, ~50ms)
ryx "hello world"

# Check system health
ryx ::health

# Interactive mode with Ctrl+C support
ryx ::session
```

## New Commands

```bash
ryx ::health          # System health status
ryx ::resume          # Resume paused task
ryx ::preferences     # Show learned preferences
```

## In Session Mode

```bash
ryx ::session
You: [query]
/health              # Check health in session
/models              # Show model status
/resume              # Resume task
Ctrl+C               # Gracefully save and exit
```

## Teach Preferences

```bash
ryx "use nvim not nano"
ryx "I prefer bash over zsh"
ryx ::preferences     # Verify learned
```

## How It Works

- **Simple queries** → 1.5B model (always loaded, ~50ms)
- **Medium queries** → 7B model (loads on-demand, ~500ms)
- **Complex queries** → 14B model (loads rarely, ~2s)
- **Idle models** → Auto-unload after 5 minutes
- **Ollama issues** → Auto-fixes automatically
- **Ctrl+C** → Saves state, can resume later

## Verification

✅ System starts in <2 seconds
✅ Only 1.5B loaded at startup
✅ Bigger models load on-demand
✅ Preferences remembered forever
✅ Auto-fixes Ollama 404 errors
✅ Graceful Ctrl+C handling

## Files

- **Installation Guide**: `~/ryx-ai/V2_INTEGRATION_GUIDE.md`
- **Summary**: `~/ryx-ai/INSTALLATION_SUMMARY.md`
- **This Guide**: `~/ryx-ai/QUICK_START.md`

## Troubleshooting

```bash
# Ollama not running?
ollama serve

# Models missing?
./install_models.sh

# Tests failing?
./test_v2.sh
cat /tmp/ryx_v2_test_*.log
```

## Rollback

```bash
# Find backup
ls ~/ryx-ai-backups/

# Restore (replace TIMESTAMP)
cp -r ~/ryx-ai-backups/ryx-ai-v1-TIMESTAMP/configs/* ~/ryx-ai/configs/
cp -r ~/ryx-ai-backups/ryx-ai-v1-TIMESTAMP/data/* ~/ryx-ai/data/
```

---

**Ready to use!** Run `ryx "hello world"` to get started.
