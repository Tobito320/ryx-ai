#!/usr/bin/env python3
"""
Ryx AI - Global CLI Entry Point (Copilot-style)

Usage:
  ryx                     # Interactive session
  ryx <prompt>            # One-shot command
  ryx start ryxhub        # Start services
  ryx --help              # Help

AI-powered, no hardcoded commands. The AI interprets everything.
"""
import sys
import os
from pathlib import Path

# Project root detection
PROJECT_ROOT = Path("/home/tobi/ryx-ai")

# Use venv if it exists
venv_path = PROJECT_ROOT / "venv" / "lib" / "python3.13" / "site-packages"
if venv_path.exists():
    sys.path.insert(0, str(venv_path))

sys.path.insert(0, str(PROJECT_ROOT))
os.environ['RYX_PROJECT_ROOT'] = str(PROJECT_ROOT)


def main():
    """Main entry point"""
    args = sys.argv[1:]
    
    # Parse CLI flags
    safety_mode = "normal"
    remaining = []
    
    for arg in args:
        if arg.startswith('--safety='):
            safety_mode = arg.split('=')[1]
        elif arg == '--strict':
            safety_mode = 'strict'
        elif arg == '--loose':
            safety_mode = 'loose'
        elif arg in ['--help', '-h']:
            show_help()
            return
        elif arg in ['--version', '-v']:
            print("Ryx AI v3.0.0 - Copilot-style local AI assistant")
            return
        else:
            remaining.append(arg)
    
    # ─────────────────────────────────────────────────────────────
    # No arguments = Interactive session
    # ─────────────────────────────────────────────────────────────
    
    if not remaining:
        from core.ryx_session import run_session
        run_session(safety_mode=safety_mode)
        return
    
    # ─────────────────────────────────────────────────────────────
    # One-shot command
    # ─────────────────────────────────────────────────────────────
    
    prompt = " ".join(remaining)
    prompt_lower = prompt.lower()
    
    # Check for "new terminal" flag
    new_terminal = any(x in prompt_lower for x in [
        "new terminal", "new term", "external terminal"
    ])
    
    # Handle service commands (start/stop ryxhub)
    if any(prompt_lower.startswith(x) for x in ["start ", "stop ", "status"]):
        handle_service_command(prompt_lower)
        return
    
    # Handle via engine
    from core.ryx_session import run_oneshot
    result = run_oneshot(prompt, new_terminal=new_terminal)
    print(result)


def handle_service_command(prompt: str):
    """Handle start/stop/status commands for services"""
    
    if prompt.startswith("start "):
        service = prompt[6:].strip()
        if any(x in service for x in ["ryxhub", "hub", "web", "ui", "frontend"]):
            start_ryxhub()
        else:
            print(f"Unknown service: {service}")
            print("Available: ryxhub")
    
    elif prompt.startswith("stop "):
        service = prompt[5:].strip()
        if any(x in service for x in ["ryxhub", "hub", "web", "ui", "frontend"]):
            stop_ryxhub()
        else:
            print(f"Unknown service: {service}")
    
    elif prompt.startswith("status"):
        show_status()


def start_ryxhub():
    """Start RyxHub web interface"""
    try:
        from core.service_manager import ServiceManager
        manager = ServiceManager()
        result = manager.start_ryxhub()
        
        if result.get('success'):
            print("✅ Starting RyxHub...")
            for line in result.get('info', []):
                print(f"  ├─ {line}")
            print("✅ RyxHub is running")
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")
    except ImportError:
        print("❌ ServiceManager not available")
    except Exception as e:
        print(f"❌ Error: {e}")


def stop_ryxhub():
    """Stop RyxHub"""
    try:
        from core.service_manager import ServiceManager
        manager = ServiceManager()
        result = manager.stop_ryxhub()
        
        if result.get('success'):
            print("✅ Stopped RyxHub")
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Error: {e}")


def show_status():
    """Show service status"""
    try:
        from core.service_manager import ServiceManager
        manager = ServiceManager()
        status = manager.get_status()
        
        print("🔍 Service Status:")
        for svc, info in status.items():
            state = "🟢 Running" if info.get('running') else "🔴 Stopped"
            print(f"  {svc}: {state}")
    except Exception as e:
        print(f"❌ Error: {e}")


def show_help():
    """Show help text"""
    print("""
Ryx AI - Local AI Assistant (Copilot-style)

USAGE:
  ryx                         Interactive session
  ryx <prompt>                One-shot command
  ryx start ryxhub            Start web interface
  ryx stop ryxhub             Stop web interface
  ryx status                  Show service status

EXAMPLES:
  ryx                         Start interactive session
  ryx open youtube            Open YouTube in browser
  ryx hyprland config         Open Hyprland config in nvim
  ryx "kitty in new terminal" Open kitty config in new terminal
  ryx find great wave         Find files matching 'great wave'
  ryx reddit                  Open Reddit in browser

SESSION COMMANDS (inside interactive mode):
  /help                       Show all commands
  /scrape <url>               Scrape webpage
  /search <query>             Web search (needs SearXNG)
  /smarter                    Self-improvement mode
  /quit                       Exit

SPECIAL SYNTAX:
  @path/to/file               Include file in context
  !command                    Run shell command directly

FLAGS:
  --help, -h                  Show this help
  --version, -v               Show version
  --safety=<mode>             Safety mode (normal/strict/loose)
""")


if __name__ == "__main__":
    main()
