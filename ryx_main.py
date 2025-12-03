#!/usr/bin/env python3
"""
Ryx AI - Main Entry Point

Copilot CLI-style local AI assistant.
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
    """Main CLI entry point"""
    args = sys.argv[1:]

    # Parse global options
    safety_mode = "normal"
    remaining_args = []

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
            print("Ryx AI 1.0.0")
            return
        else:
            remaining_args.append(arg)

    # No args = Start interactive session
    if not remaining_args:
        from core.session_loop import SessionLoop
        session = SessionLoop(safety_mode=safety_mode)
        session.run()
        return

    # Handle special commands first
    first_arg = remaining_args[0].lower() if remaining_args else ""
    
    # Service commands: ryx start/stop/status
    if first_arg == "start":
        service = remaining_args[1] if len(remaining_args) > 1 else "ryxhub"
        _start_service(service)
        return
    elif first_arg == "stop":
        service = remaining_args[1] if len(remaining_args) > 1 else "ryxhub"
        _stop_service(service)
        return
    elif first_arg == "status":
        _service_status()
        return
    
    # Benchmark commands: ryx benchmark [list|run|compare]
    elif first_arg == "benchmark":
        _handle_benchmark(remaining_args[1:])
        return
    
    # RSI commands: ryx rsi [start|status|iterate]
    elif first_arg == "rsi":
        _handle_rsi(remaining_args[1:])
        return

    # Everything else: Let brain understand and execute
    prompt = " ".join(remaining_args).strip()
    
    if not prompt:
        print("Usage: ryx [prompt] or ryx --help")
        return
    
    from core.ryx_brain import get_brain
    from core.llm_backend import get_backend
    
    backend = get_backend()
    brain = get_brain(backend)
    
    plan = brain.understand(prompt)
    success, result = brain.execute(plan)
    
    if result and result != "__STREAMED__":
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
    
    # "ryx start" with no args = start all (vllm + searxng)
    if service in ["all", ""]:
        print("🚀 Starting all services...")
        _start_service("vllm")
        _start_service("searxng")
        return
    
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
    
    elif service in ["vllm", "llm", "model", "inference"]:
        from core.docker_services import start_service
        
        print("🚀 Starting vLLM (GPU inference)...")
        result = start_service("vllm")
        
        if result.get("success"):
            print("✅ vLLM started")
            print("   Port: http://localhost:8001")
            print("   Model: qwen2.5-7b-gptq")
        else:
            print(f"❌ Failed to start vLLM: {result.get('error', 'Unknown')}")
    
    elif service in ["searxng", "search", "websearch"]:
        from core.docker_services import start_service
        
        print("🔍 Starting SearXNG (web search)...")
        result = start_service("searxng")
        
        if result.get("success"):
            print("✅ SearXNG started")
            print("   Port: http://localhost:8888")
        else:
            print(f"❌ Failed to start SearXNG: {result.get('error', 'Unknown')}")
    
    elif service in ["session", "interactive", "cli", "terminal"]:
        from core.session_loop import SessionLoop
        session = SessionLoop()
        session.run()
    
    else:
        print(f"❌ Unknown service: {service}")
        print("Available: all, vllm, searxng, ryxhub, session")


def _stop_service(service: str):
    """Stop a service (internal helper)"""
    service = service.lower().replace(" ", "").replace("-", "").replace("_", "")
    
    # "ryx stop all" = stop everything
    if service in ["all", ""]:
        print("🛑 Stopping all services...")
        _stop_service("vllm")
        _stop_service("searxng")
        _stop_service("ryxhub")
        return
    
    if service in ["ryxhub", "hub", "webui", "webinterface", "frontend", "dashboard", "web"]:
        from core.service_manager import ServiceManager
        manager = ServiceManager()
        result = manager.stop_ryxhub()
        if result['success']:
            print("✅ Stopped RyxHub")
        else:
            print(f"❌ Failed to stop RyxHub: {result.get('error', 'Unknown error')}")
    
    elif service in ["vllm", "llm", "model", "inference"]:
        from core.docker_services import stop_service
        
        print("🛑 Stopping vLLM...")
        result = stop_service("vllm")
        
        if result.get("success"):
            print("✅ vLLM stopped")
        else:
            print(f"❌ Failed to stop vLLM: {result.get('error', 'Unknown')}")
    
    elif service in ["searxng", "search", "websearch"]:
        from core.docker_services import stop_service
        
        print("🛑 Stopping SearXNG...")
        result = stop_service("searxng")
        
        if result.get("success"):
            print("✅ SearXNG stopped")
        else:
            print(f"❌ Failed to stop SearXNG: {result.get('error', 'Unknown')}")
    
    else:
        print(f"❌ Unknown service: {service}")
        print("Available: all, vllm, searxng, ryxhub")


def _service_status(service: str = None):
    """Check service status (internal helper)"""
    from core.docker_services import get_docker_manager, service_status
    
    print("\n🔍 Service Status:\n")
    
    # Docker services status
    docker_status = service_status()
    
    if docker_status.get("success"):
        for svc_name, info in docker_status.get("services", {}).items():
            status = info.get("status", "unknown")
            if status == "running":
                urls = info.get("urls", [])
                url_str = f" ({urls[0]})" if urls else ""
                print(f"  {svc_name}: 🟢 Running{url_str}")
            elif status == "stopped":
                print(f"  {svc_name}: 🔴 Stopped")
            else:
                print(f"  {svc_name}: ⚪ {status}")
    else:
        print(f"  ⚠️ Could not get Docker status: {docker_status.get('error', 'Unknown')}")
    
    # Also show legacy service manager status
    try:
        from core.service_manager import ServiceManager
        manager = ServiceManager()
        legacy_status = manager.get_status()
        
        for svc, info in legacy_status.items():
            state = "🟢 Running" if info.get('running') else "🔴 Stopped"
            print(f"  {svc}: {state}")
    except:
        pass


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


def _handle_benchmark(args):
    """Handle benchmark commands"""
    import asyncio
    
    if not args:
        args = ["list"]
    
    cmd = args[0].lower()
    
    if cmd == "list":
        from core.benchmarks import BenchmarkRegistry
        print("\n📊 Available Benchmarks:\n")
        for name in BenchmarkRegistry.list_all():
            benchmark = BenchmarkRegistry.create(name)
            if benchmark:
                print(f"  • {name}")
                print(f"    {benchmark.description}")
                print(f"    Problems: {len(benchmark.problems)}")
                print()
    
    elif cmd == "run":
        from core.benchmarks import BenchmarkRunner, BenchmarkRegistry, RunConfig
        
        benchmark_name = args[1] if len(args) > 1 else "coding_tasks"
        dry_run = "--dry-run" in args
        verbose = "-v" in args or "--verbose" in args
        
        if benchmark_name not in BenchmarkRegistry.list_all():
            print(f"❌ Unknown benchmark: {benchmark_name}")
            print(f"Available: {', '.join(BenchmarkRegistry.list_all())}")
            return
        
        print(f"\n🚀 Running benchmark: {benchmark_name}")
        
        if dry_run:
            print("   (dry-run mode - using dummy executor)")
        
        runner = BenchmarkRunner()
        
        if dry_run:
            async def dummy_executor(problem, config):
                return f"# Placeholder\ndef placeholder(): pass"
            runner.set_executor(dummy_executor)
        else:
            # Try to connect to vLLM
            try:
                from core.benchmarks.executor import create_connected_executor
                executor = asyncio.get_event_loop().run_until_complete(
                    create_connected_executor()
                )
                if executor:
                    runner.set_executor(executor.run_problem)
                else:
                    print("❌ Cannot connect to vLLM. Use --dry-run or start vLLM first.")
                    print("   Run: ryx start vllm")
                    return
            except Exception as e:
                print(f"❌ Executor error: {e}")
                print("   Use --dry-run for testing without LLM")
                return
        
        config = RunConfig(verbose=verbose)
        
        try:
            result = asyncio.get_event_loop().run_until_complete(
                runner.run(benchmark_name, config)
            )
            print(result.summary())
            print(f"\n💾 Results saved: {result.run_id}")
        except Exception as e:
            print(f"❌ Benchmark failed: {e}")
    
    elif cmd == "history":
        from core.benchmarks import BenchmarkRunner
        runner = BenchmarkRunner()
        
        benchmark_name = args[1] if len(args) > 1 else None
        runs = runner.list_runs(benchmark_name)
        
        if not runs:
            print("ℹ️  No benchmark runs found")
            return
        
        print(f"\n📜 Benchmark History:\n")
        for run_id in runs[:10]:
            run = runner.load_run(run_id)
            if run:
                print(f"  {run_id}")
                print(f"    Score: {run.average_score:.2%} | Passed: {run.passed_count}/{run.total_problems}")
                print()
    
    elif cmd == "compare":
        if len(args) < 3:
            print("Usage: ryx benchmark compare <run_id_1> <run_id_2>")
            return
        
        from core.benchmarks import BenchmarkRunner
        runner = BenchmarkRunner()
        
        try:
            diff = runner.compare(args[1], args[2])
            print(f"\n📊 Comparison:\n")
            print(f"Score: {diff['run1_score']:.2%} → {diff['run2_score']:.2%} ({diff['score_diff']:+.2%})")
            print(f"Improved: {diff['improved_count']} problems")
            print(f"Regressed: {diff['regressed_count']} problems")
            
            if diff['is_improvement']:
                print("\n✅ Run 2 is an improvement!")
            else:
                print("\n⚠️  Run 2 has regressions")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    else:
        print(f"Unknown benchmark command: {cmd}")
        print("Available: list, run, history, compare")


def _handle_rsi(args):
    """Handle RSI (self-improvement) commands"""
    import asyncio
    
    if not args:
        args = ["status"]
    
    cmd = args[0].lower()
    
    if cmd == "status":
        from core.rsi import RSILoop
        rsi = RSILoop()
        
        summary = rsi.get_summary()
        print("\n🔄 RSI Status:\n")
        print(f"  Phase: {summary['current_phase']}")
        print(f"  Iterations: {summary['total_iterations']}")
        print(f"  Accepted: {summary['accepted']}")
        print(f"  Rejected: {summary['rejected']}")
        print(f"  Total improvement: {summary['total_improvement']:.2%}")
    
    elif cmd == "iterate":
        print("\n🔄 Starting RSI iteration...")
        print("   (This requires vLLM to be running)")
        
        from core.rsi import RSILoop, RSIConfig
        
        config = RSIConfig(
            benchmarks=["coding_tasks", "bug_fixing"],
            require_approval=True,
        )
        rsi = RSILoop(config)
        
        async def run_iteration():
            await rsi.initialize()
            return await rsi.iterate()
        
        try:
            result = asyncio.get_event_loop().run_until_complete(run_iteration())
            print(f"\n📊 Iteration complete:")
            print(f"   Baseline: {result.baseline_score:.2%}")
            print(f"   New: {result.new_score:.2%}")
            print(f"   Accepted: {result.accepted}")
        except Exception as e:
            print(f"❌ RSI iteration failed: {e}")
    
    elif cmd == "loop":
        max_iter = int(args[1]) if len(args) > 1 else 5
        print(f"\n🔄 Starting RSI loop ({max_iter} max iterations)...")
        
        from core.rsi import RSILoop, RSIConfig
        
        config = RSIConfig(require_approval=True)
        rsi = RSILoop(config)
        
        async def run_loop():
            await rsi.initialize()
            await rsi.run_loop(max_iterations=max_iter)
            return rsi.get_summary()
        
        try:
            summary = asyncio.get_event_loop().run_until_complete(run_loop())
            print(f"\n📊 RSI loop complete:")
            print(f"   Total iterations: {summary['total_iterations']}")
            print(f"   Improvements accepted: {summary['accepted']}")
        except Exception as e:
            print(f"❌ RSI loop failed: {e}")
    
    else:
        print(f"Unknown RSI command: {cmd}")
        print("Available: status, iterate, loop")


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
    """Show help - Copilot CLI style"""
    print("""
Ryx AI - Local AI Assistant

USAGE:
    ryx                    Start interactive session
    ryx "prompt"           Execute prompt directly

SERVICES:
    ryx start vllm         Start vLLM (GPU inference)
    ryx start ryxhub       Start web dashboard
    ryx stop vllm          Stop vLLM
    ryx stop ryxhub        Stop web dashboard
    ryx status             Show all service status

BENCHMARKS:
    ryx benchmark list     List available benchmarks
    ryx benchmark run      Run a benchmark
    ryx benchmark history  Show past runs
    ryx benchmark compare  Compare two runs

RSI (Self-Improvement):
    ryx rsi status         Show RSI status
    ryx rsi iterate        Run one improvement iteration
    ryx rsi loop [n]       Run n improvement iterations

SHORTCUTS:
    @                      Include file contents
    !                      Run shell command
    Ctrl+c                 Interrupt current operation
    Ctrl+c twice           Exit session

SESSION COMMANDS:
    /help                  Show help
    /clear                 Clear conversation
    /model                 Show/change model
    /style <name>          Set style (normal/concise/explanatory/learning/formal)
    /sources               Show sources from last search
    /status                Show statistics
    /quit                  Exit session

EXAMPLES:
    ryx                          Interactive session
    ryx "open hyprland config"   Open config file
    ryx "search recursion"       Web search
    ryx "create login.py"        Generate code
    ryx start vllm               Start GPU inference
    ryx benchmark run            Run coding benchmark
""")


if __name__ == "__main__":
    cli_main()
