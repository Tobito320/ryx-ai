#!/usr/bin/env python3
"""
Ryx AI v3 - Main Entry Point

Copilot-style local AI assistant.
- No hardcoded commands
- AI understands everything
- Asks when unclear, acts when clear
"""
import sys
import os
from pathlib import Path
from typing import Dict

# Auto-detect project root
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ['RYX_PROJECT_ROOT'] = str(PROJECT_ROOT)


def cli_main():
    """Main CLI entry point - AI interprets all commands"""
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
        elif arg in ['--help', '-h']:
            show_help()
            return
        elif arg in ['--version', '-v']:
            print("Ryx AI v3.0.0 - Copilot-style local AI assistant")
            return
        else:
            remaining_args.append(arg)

    # No args = Start interactive session (v3)
    if not remaining_args:
        from core.session_loop_v3 import SessionLoopV3
        session = SessionLoopV3(safety_mode=safety_mode)
        session.run()
        return

    # Everything else: Let brain understand and execute
    prompt = " ".join(remaining_args)
    
    from core.ryx_brain_v3 import get_brain_v3
    from core.ollama_client import OllamaClient
    from core.model_router import ModelRouter
    
    router = ModelRouter()
    ollama = OllamaClient(base_url=router.get_ollama_url())
    brain = get_brain_v3(ollama)
    
    action = brain.understand(prompt)
    success, result = brain.execute(action)
    
    if result:
        print(result)


def execute_action(action, safety_mode: str, silent_mode: bool):
    """
    Execute an AI-determined action.
    
    This is the ONLY place where actions are dispatched - 
    all routing is done by AI, not hardcoded patterns.
    """
    from core.ai_interpreter import AIAction
    
    action_type = action.action_type
    target = action.target
    
    if action_type == "start_service":
        _start_service(target or "ryxhub")
    
    elif action_type == "stop_service":
        _stop_service(target or "ryxhub")
    
    elif action_type == "service_status":
        _service_status(target)
    
    elif action_type == "self_heal":
        _run_self_healing(action.parameters.get("aggressive", False))
    
    elif action_type == "remember":
        _remember(target, action.parameters)
    
    elif action_type == "recall":
        _recall(target)
    
    elif action_type == "chat":
        # General conversation - use session
        if silent_mode:
            handle_silent_prompt(action.original_prompt, safety_mode)
        else:
            from core.session_loop import SessionLoop
            session = SessionLoop(safety_mode=safety_mode)
            session._process_input(action.original_prompt)
    
    elif action_type in ["open_file", "find_file", "code_help", "search_web", "system_task"]:
        # These all go through the session for full AI handling
        from core.session_loop import SessionLoop
        session = SessionLoop(safety_mode=safety_mode)
        session._process_input(action.original_prompt)
    
    elif action_type == "run_command":
        # Shell command execution (with safety)
        if action.parameters.get("confirm", True):
            confirm = input(f"Run command: {target}? [y/N] ")
            if confirm.lower() != 'y':
                print("Cancelled")
                return
        import subprocess
        subprocess.run(target, shell=True)
    
    else:
        # Unknown action type - fall back to chat
        from core.session_loop import SessionLoop
        session = SessionLoop(safety_mode=safety_mode)
        session._process_input(action.original_prompt)


def _start_service(service: str):
    """Start a service (internal helper)"""
    service = service.lower().replace(" ", "").replace("-", "").replace("_", "")
    
    # Normalize service name (AI might say "ryxhub", "hub", "web interface", etc.)
    if service in ["ryxhub", "hub", "webui", "webinterface", "frontend", "dashboard", "web"]:
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
    
    elif service in ["session", "interactive", "cli", "terminal"]:
        from core.session_loop import SessionLoop
        session = SessionLoop()
        session.run()
    
    else:
        print(f"❌ Unknown service: {service}")
        print("Available: ryxhub, session")


def _stop_service(service: str):
    """Stop a service (internal helper)"""
    service = service.lower().replace(" ", "").replace("-", "").replace("_", "")
    
    if service in ["ryxhub", "hub", "webui", "webinterface", "frontend", "dashboard", "web"]:
        from core.service_manager import ServiceManager
        manager = ServiceManager()
        result = manager.stop_ryxhub()
        if result['success']:
            print("✅ Stopped RyxHub")
        else:
            print(f"❌ Failed to stop RyxHub: {result.get('error', 'Unknown error')}")
    else:
        print(f"❌ Unknown service: {service}")


def _service_status(service: str = None):
    """Check service status (internal helper)"""
    from core.service_manager import ServiceManager
    manager = ServiceManager()
    status = manager.get_status()
    
    print("🔍 Service Status:")
    for svc, info in status.items():
        state = "🟢 Running" if info.get('running') else "🔴 Stopped"
        print(f"  {svc}: {state}")
        if info.get('ports'):
            for port_info in info['ports']:
                print(f"    └─ {port_info}")


def _run_self_healing(aggressive: bool = False):
    """Run AI-driven self-healing on knowledge/cache"""
    print("🧠 Running self-healing...")
    print()
    
    from core.self_healer import run_self_healing
    result = run_self_healing(aggressive=aggressive)
    
    for detail in result.details:
        print(detail)
    
    print()
    print(result.summary)


def _remember(content: str, parameters: Dict):
    """Store something in long-term memory"""
    from core.memory import get_memory
    
    memory = get_memory()
    memory_type = parameters.get("type", "fact")
    
    # If it's a preference with key/value, update profile
    if memory_type == "preference" and "key" in parameters:
        memory.learn_preference(
            parameters["key"], 
            parameters.get("value", content),
            source="explicit"
        )
        print(f"✅ Remembered preference: {parameters['key']} = {parameters.get('value', content)}")
    else:
        # Store as general memory
        memory_id = memory.remember(content, memory_type=memory_type, importance=0.8)
        print(f"✅ Remembered: {content[:50]}...")


def _recall(query: str):
    """Recall information from memory"""
    from core.memory import get_memory
    
    memory = get_memory()
    
    # Get user profile
    profile = memory.profile
    print("🧠 What I know about you:")
    print()
    
    print(f"  Environment:")
    print(f"    • OS: {profile.os} ({profile.distro})")
    print(f"    • WM: {profile.wm}")
    print(f"    • Shell: {profile.shell}")
    print(f"    • Editor: {profile.editor}")
    print(f"    • Terminal: {profile.terminal}")
    print()
    
    print(f"  Preferences:")
    print(f"    • Response style: {profile.response_length}")
    print(f"    • Tone: {profile.tone}")
    print(f"    • Prefers action over explanation: {not profile.prefers_explanations}")
    print()
    
    # Get relevant memories
    memories = memory.recall(query, limit=5)
    if memories:
        print(f"  Related memories ({len(memories)}):")
        for m in memories:
            print(f"    • [{m.memory_type}] {m.content[:60]}...")
    else:
        print("  No specific memories found for this query.")


def handle_silent_prompt(prompt: str, safety_mode: str):
    """Handle prompt in silent mode - minimal output"""
    import io
    import sys
    from contextlib import redirect_stdout
    from modes.cli_mode import CLIMode

    cli = CLIMode()

    # Capture output using redirect_stdout
    captured = io.StringIO()
    with redirect_stdout(captured):
        try:
            cli.handle_prompt(prompt)
        except Exception:
            pass

    # Get output and filter
    output = captured.getvalue()
    output_lines = []
    for line in output.split('\n'):
        # Skip thinking indicators and empty lines
        if line.strip() and '[thinking' not in line and '[searching' not in line and '[cached]' not in line:
            # Skip ANSI escape sequences for "thinking" style text
            if not line.startswith('\033[2m'):
                output_lines.append(line)

    # Print only essential output (max 3 lines)
    for line in output_lines[:3]:
        print(line)


def show_help():
    """Show help message"""
    print("""
🟣 Ryx AI v3 - Copilot-Style Local AI

USAGE:
    ryx                      Start interactive session
    ryx "prompt"             Run command in natural language
    ryx -s "prompt"          Silent mode (minimal output)

EXAMPLES:
    ryx "open youtube"                    # Open website
    ryx "hyprland config"                 # Open config file
    ryx "hyprland config new terminal"    # Open in new terminal
    ryx "where is .zshrc"                 # Find file
    ryx "search for IPv6"                 # Web search
    ryx "scrape arch wiki"                # Scrape webpage
    ryx "set zen as default browser"      # Save preference
    ryx "use gpt 20b as default"          # Change model
    ryx "mach mir einen lernzettel"       # Create document (German)

FEATURES:
    • Understands typos and natural language
    • Asks when unclear, acts when clear
    • German and English support
    • Web browsing and scraping
    • File operations
    • Model switching

SESSION COMMANDS (/):
    /help        Show help
    /models      List available models
    /precision   Toggle precision mode
    /browsing    Toggle web browsing
    /scrape      Scrape webpage
    /search      Web search
    /learn       Learn from scraped content
    /smarter     Self-improvement
    /status      Show statistics
    /quit        Exit session

SPECIAL SYNTAX:
    @file        Include file contents
    !command     Run shell command
    y/n          Quick confirmation
    1, 2, 3      Select from list
""")


if __name__ == "__main__":
    cli_main()
