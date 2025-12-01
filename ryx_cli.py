#!/usr/bin/env python3
"""
Ryx AI - CLI Entry Point Module

This module provides the main entry point for the `ryx` command.
"""
import sys
import os
from pathlib import Path

# Auto-detect project root
PROJECT_ROOT = Path(__file__).resolve().parent

# Add project to path
sys.path.insert(0, str(PROJECT_ROOT))

# Set environment variable for other modules to use
os.environ['RYX_PROJECT_ROOT'] = str(PROJECT_ROOT)


def main():
    """Main entry point for the ryx CLI command."""
    # Import the actual main from ryx.bin
    from ryx_main import cli_main
    cli_main()


if __name__ == "__main__":
    main()
