#!/bin/bash
# Instant RyxSurf launcher - no vLLM checks
# AI features activate when vLLM is ready (started by Hyprland)
cd /home/tobi/ryx-ai
source venv/bin/activate 2>/dev/null
exec python3 -m ryxsurf.main "$@"
