#!/usr/bin/env python3
"""
RyxSurf - AI-Integrated Minimalist Browser

A keyboard-driven browser for Hyprland users with full AI integration.
Built for Arch Linux, designed to work seamlessly with Ryx AI.

Features:
- Clean Adwaita UI with sidebar tabs
- Fullscreen by default, toggle UI with keybinds
- Tab sessions/groups (school/work/chill)
- AI can click, summarize, dismiss popups
- Firefox extension support (WebExtensions API)
- Auto-unload inactive tabs
- Synced with ryx CLI and RyxHub
"""

import sys
from pathlib import Path

# Add ryxsurf root to path
RYXSURF_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(RYXSURF_ROOT))


def main():
    """Main entry point for RyxSurf"""
    # Use new Adwaita-based browser
    from src.core.browser_adw import main as adw_main
    adw_main()


if __name__ == "__main__":
    main()
