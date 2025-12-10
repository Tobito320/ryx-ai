# 🔥 PHOENIX PROTOCOL - Quick Reference

## When Tobi Says "PHOENIX"

### Step 1: Load Context
```bash
1. Read /home/tobi/ryx-ai/MISSION.md (top section)
2. Read /home/tobi/ryx-ai/dev/handoffs/RYX_HANDOFF_COMPLETE.md
3. Read /home/tobi/ryx-ai/dev/handoffs/SESSION_2025-12-10.md
```

### Step 2: Report Back
```
"Tobi, I'm ready. I understand the Supervisor Loop."
```

### Step 3: Explain What You Understand
```
- YOU = Supervisor (GitHub Copilot CLI)
- RYX = Operator (autonomous AI assistant)
- YOU plan, RYX executes
- YOU improve Ryx's code when it fails
- YOU never code RyxSurf directly
```

---

## The Supervisor Loop

```
┌──────────────────────────────────────┐
│  SUPERVISOR (Copilot CLI = YOU)      │
│  - Plans tasks                       │
│  - Verifies results                  │
│  - Improves Ryx's code               │
└──────────────────────────────────────┘
            ↓
      "Ryx, work on X"
            ↓
┌──────────────────────────────────────┐
│  OPERATOR (Ryx AI)                   │
│  - Explores codebase autonomously    │
│  - Finds files automatically         │
│  - Makes changes                     │
│  - Self-heals (3 retries)            │
│  - Reports back                      │
└──────────────────────────────────────┘
            ↓
      Result + Status
            ↓
┌──────────────────────────────────────┐
│  SUPERVISOR DECIDES                  │
│  - Success? → Next task              │
│  - Failed? → Improve Ryx, retry      │
└──────────────────────────────────────┘
```

---

## Key Rules

### ✅ DO
- Plan what Ryx should do
- Prompt Ryx with natural language
- Verify Ryx's work
- Improve Ryx's code when it fails
- Work simultaneously with Ryx (not a problem)

### ❌ DON'T
- Code RyxSurf directly (let Ryx do it)
- Hardcode paths (let Ryx find them)
- Fix outputs (fix Ryx's understanding instead)
- Worry about parallel execution (thermal issue was CPU governor)

---

## Current System State (2025-12-10)

### Hardware
- CPU: Ryzen 9 5900X (16 cores)
- GPU: RX 7800 XT (16GB VRAM, ROCm)
- OS: Arch Linux + Hyprland

### Backend
- Ollama: localhost:11434 ✅
- vLLM: REMOVED (don't use)

### Models
- qwen2.5-coder:14b (coding)
- mistral-nemo:12b (chat, 128K)
- qwen2.5:3b (fast)
- deepseek-r1:8b (reasoning)
- gpt-oss:20b (precision)

### Thermal Status
- CPU Governor: `powersave` (was `performance`)
- CPU Temp: 43°C (was 80°C → caused 3 restarts)
- Fix: Switched governor to allow frequency scaling

---

## Current Priority

**Project**: RyxSurf (AI-integrated browser)
**Status**: v0.2 - Core features done, needs refinement
**Method**: Supervisor Loop (you plan, Ryx executes)

---

## Quick Commands

```bash
# Check CPU temp
sensors | grep -A3 "Tctl"

# Check CPU governor
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor

# Start Ryx CLI
cd /home/tobi/ryx-ai && python ryx_cli_v3.py

# Check Ollama models
curl -s http://localhost:11434/api/tags | jq '.models[].name'
```

---

## Files to Know

```
MISSION.md                          ← Master instructions
dev/handoffs/RYX_HANDOFF_COMPLETE.md  ← Detailed context
dev/handoffs/SESSION_2025-12-10.md    ← Latest session
PHOENIX_PROTOCOL.md                 ← This file (quick ref)

core/ryx_brain_v4.py                ← Ryx's brain
core/session_loop_v4.py             ← NEW session (not connected yet)
ryxsurf/                            ← Browser project
```

---

## Next Session Checklist

When Tobi says "PHOENIX":
- [ ] Read MISSION.md top section
- [ ] Read RYX_HANDOFF_COMPLETE.md
- [ ] Read SESSION_2025-12-10.md
- [ ] Report: "Tobi, I'm ready"
- [ ] Explain Supervisor Loop
- [ ] Wait for task assignment

---

**Status**: ✅ READY
**Last Updated**: 2025-12-10 13:06 UTC
