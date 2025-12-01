#!/usr/bin/env python3
"""
Ryx AI - Main Entry Point Module

Production-grade local agentic CLI.
Primary interaction: `ryx` starts an interactive session.
"""
import sys
import os
from pathlib import Path

# Auto-detect project root (resolve symlinks first, then get parent)
PROJECT_ROOT = Path(__file__).resolve().parent

# Add project to path
sys.path.insert(0, str(PROJECT_ROOT))

# Set environment variable for other modules to use
os.environ['RYX_PROJECT_ROOT'] = str(PROJECT_ROOT)


def cli_main():
    """Main CLI entry point"""
    args = sys.argv[1:]

    # Parse global options
    safety_mode = "normal"
    silent_mode = False
    remaining_args = []

    for arg in args:
        if arg.startswith('--safety='):
            safety_mode = arg.split('=')[1]
        elif arg == '--strict':
            safety_mode = 'strict'
        elif arg == '--loose':
            safety_mode = 'loose'
        elif arg == '--silent' or arg == '-s':
            silent_mode = True
        elif arg == '--tier' and remaining_args:
            # Handle --tier <name> separately
            pass
        else:
            remaining_args.append(arg)

    # Main entry point logic
    if not remaining_args:
        # No args = Start interactive session (primary interaction)
        from core.session_loop import SessionLoop
        session = SessionLoop(safety_mode=safety_mode)
        session.run()

    elif remaining_args[0] in ['--help', '-h']:
        show_help()

    elif remaining_args[0] in ['--version', '-v']:
        print("Ryx AI v2.0.0 - Production-grade local agentic CLI")

    elif remaining_args[0] == 'start':
        # Service management: ryx start <service>
        handle_service_start(remaining_args[1:])

    elif remaining_args[0] == 'stop':
        # Service management: ryx stop <service>
        handle_service_stop(remaining_args[1:])

    elif remaining_args[0] == 'status':
        # Service status: ryx status [service]
        handle_service_status(remaining_args[1:])

    elif remaining_args[0].startswith("::"):
        # Legacy command mode (kept for backward compatibility)
        from modes.cli_mode import handle_command
        handle_command(remaining_args[0], remaining_args[1:])

    elif remaining_args[0].startswith('--tier'):
        # Direct tier specification: ryx --tier fast "prompt"
        if len(remaining_args) >= 3 and remaining_args[0] == '--tier':
            tier = remaining_args[1]
            prompt = " ".join(remaining_args[2:])
            from core.session_loop import SessionLoop
            session = SessionLoop(safety_mode=safety_mode)
            session.current_tier = session.router.get_tier_by_name(tier)
            session._process_input(prompt)
        else:
            print("Usage: ryx --tier <tier_name> \"prompt\"")

    else:
        # Direct prompt mode - run prompt and exit
        prompt = " ".join(remaining_args)
        if silent_mode:
            # Silent execution mode - minimal output
            handle_silent_prompt(prompt, safety_mode)
        else:
            from core.session_loop import SessionLoop
            session = SessionLoop(safety_mode=safety_mode)
            session._process_input(prompt)


def handle_service_start(args: list):
    """Handle service start command"""
    if not args:
        print("Usage: ryx start <service>")
        print("Available services: RyxHub, session")
        return

    service = args[0].lower()

    if service in ['ryxhub', 'hub']:
        from core.service_manager import ServiceManager
        manager = ServiceManager()
        result = manager.start_ryxhub()
        if result['success']:
            print("✅ Starting RyxHub...")
            for line in result.get('info', []):
                print(f"  ├─ {line}")
            print("✅ RyxHub is running")
        else:
            print(f"❌ Failed to start RyxHub: {result.get('error', 'Unknown error')}")

    elif service == 'session':
        from core.session_loop import SessionLoop
        session = SessionLoop()
        session.run()

    else:
        print(f"❌ Unknown service: {service}")
        print("Available services: RyxHub, session")


def handle_service_stop(args: list):
    """Handle service stop command"""
    if not args:
        print("Usage: ryx stop <service>")
        print("Available services: RyxHub")
        return

    service = args[0].lower()

    if service in ['ryxhub', 'hub']:
        from core.service_manager import ServiceManager
        manager = ServiceManager()
        result = manager.stop_ryxhub()
        if result['success']:
            print("✅ Stopped RyxHub")
        else:
            print(f"❌ Failed to stop RyxHub: {result.get('error', 'Unknown error')}")
    else:
        print(f"❌ Unknown service: {service}")
        print("Available services: RyxHub")


def handle_service_status(args: list):
    """Handle service status command"""
    from core.service_manager import ServiceManager
    manager = ServiceManager()

    if not args:
        # Show all services
        status = manager.get_status()
        print("🔍 Service Status:")
        for service, info in status.items():
            state = "🟢 Running" if info.get('running') else "🔴 Stopped"
            print(f"  {service}: {state}")
            if info.get('ports'):
                for port_info in info['ports']:
                    print(f"    └─ {port_info}")
    else:
        service = args[0].lower()
        status = manager.get_status()
        if service in status:
            info = status[service]
            state = "🟢 Running" if info.get('running') else "🔴 Stopped"
            print(f"{service}: {state}")
        else:
            print(f"❌ Unknown service: {service}")


def handle_silent_prompt(prompt: str, safety_mode: str):
    """Handle prompt in silent mode - minimal output"""
    from modes.cli_mode import CLIMode

    cli = CLIMode()

    # Override to minimal output mode
    original_print = __builtins__['print']
    output_lines = []

    def silent_print(*args, **kwargs):
        # Only capture meaningful output, skip thinking indicators
        text = ' '.join(str(a) for a in args)
        if '[thinking' not in text and '[searching' not in text and '[cached]' not in text:
            output_lines.append(text)

    try:
        __builtins__['print'] = silent_print
        cli.handle_prompt(prompt)
    finally:
        __builtins__['print'] = original_print

    # Print only essential output (max 3 lines)
    essential = [l for l in output_lines if l.strip() and not l.startswith('\033[2m')][:3]
    for line in essential:
        print(line)


def show_help():
    """Show help message"""
    print("""
🟣 Ryx AI - Local Agentic CLI

USAGE:
    ryx                      Start interactive session
    ryx "prompt"             Run single prompt and exit
    ryx -s "prompt"          Silent mode (max 3 lines output)
    ryx start RyxHub         Start backend + frontend services
    ryx stop RyxHub          Stop all services
    ryx status               Show service status
    ryx --tier fast "prompt" Run with specific model tier
    ryx --help               Show this help
    ryx --version            Show version

SERVICE COMMANDS:
    start RyxHub     Start FastAPI backend + React frontend
    stop RyxHub      Stop all RyxHub services
    start session    Start interactive session
    status           Show all service status

TIERS:
    fast         Quick responses (mistral:7b)
    balanced     Default coding (qwen2.5-coder:14b)
    powerful     Complex tasks (deepseek-coder-v2:16b)
    ultra        Heavy reasoning (Qwen3-Coder:30B)
    uncensored   Personal chat (gpt-oss:20b)

SESSION COMMANDS:
    /help        Show help
    /status      Show current status
    /tier <name> Switch model tier
    /models      List available models
    /quit        Exit session

EXAMPLES:
    ryx "open hyprland config"       # Opens file directly
    ryx start RyxHub                 # Start web interface
    ryx -s "what time is it"         # Quick query, minimal output
    ryx --tier fast "hello"          # Fast model response

For more info: https://github.com/ryx-ai
""")


if __name__ == "__main__":
    cli_main()
