#!/usr/bin/env python3
"""
RyxSurf Adwaita Edition Launcher
Professional UI using libadwaita
"""

import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.browser_adw import main

if __name__ == "__main__":
    main()
