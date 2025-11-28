"""
Ryx AI - CLI Mode
Ultra-fast one-shot command execution
"""

import sys
import json
from pathlib import Path
from typing import Optional

from core.ai_engine_v2 import AIEngineV2
from core.ai_engine import ResponseFormatter
from core.rag_system import RAGSystem, FileFinder
from core.permissions import PermissionManager, CommandExecutor, InteractiveConfirm
from core.meta_learner import MetaLearner
import subprocess
import os
from core.paths import get_project_root, get_data_dir, get_config_dir, get_runtime_dir

class CLIMode:
    """Ultra-fast one-shot command execution mode"""

    def __init__(self) -> None:
        """Initialize CLI mode with AI engine and caching"""
        self.ai = AIEngineV2()
        self.rag = RAGSystem()
        self.file_finder = FileFinder(self.rag)
        self.perm_manager = PermissionManager()
        self.executor = CommandExecutor(self.perm_manager)
        self.formatter = ResponseFormatter()
        self.meta_learner = self.ai.meta_learner
    
    def handle_prompt(self, prompt: str):
        """Handle direct prompt with V2 engine"""

        # Check cache first (0-latency path)
        cached = self.rag.query_cache(prompt)
        if cached:
            print("\033[2m[cached]\033[0m")
            # Apply learned preferences to cached response
            cached = self.meta_learner.apply_preferences_to_response(cached)
            print(self.formatter.format_cli(cached))
            return

        # Check if it's a file operation
        if any(kw in prompt.lower() for kw in ["open", "edit", "show", "find"]):
            # Try file finder first
            file_info = self.file_finder.find(prompt)
            if file_info:
                file_path, confidence = file_info

                if confidence > 0.8:
                    # High confidence - just do it
                    if "open" in prompt.lower() or "edit" in prompt.lower():
                        # Get preferred editor
                        editor = self.meta_learner.get_preference("editor", "nvim")

                        # Check if new terminal is requested
                        open_in_new_terminal = any(kw in prompt.lower() for kw in ["new terminal", "new tab", "separate window"])

                        if open_in_new_terminal:
                            # Open in new terminal (kitty)
                            cmd = f"kitty -e {editor} {file_path} &"
                            print(f"\033[1;32m▸\033[0m Opening {file_path} in new terminal")
                            result = self.executor.execute(cmd, confirm=True)
                        else:
                            # For same terminal, print command for user to run
                            # (can't capture output from interactive editors)
                            cmd = f"{editor} {file_path}"
                            print(f"\033[1;32m▸\033[0m To open: \033[1;36m{cmd}\033[0m")
                            result = {"success": True, "stdout": "", "stderr": "", "exit_code": 0}

                        if result["success"]:
                            # Cache this for next time
                            self.rag.cache_response(prompt, f"```bash\n{cmd}\n```", "cached")
                            # Learn the file location
                            self.rag.learn_file_location(prompt, "config", file_path, confidence=confidence)
                        return

        # Query AI with V2 engine
        print("\033[2m[thinking...]\033[0m", end="\r")
        result = self.ai.query(prompt, context=None, use_cache=True, learn_preferences=True)
        print(" " * 20, end="\r")  # Clear "thinking"

        if result.error:
            print(f"\033[1;31m✗\033[0m {result.error_message}")
            return

        ai_text = result.response

        # Parse commands
        commands = self.executor.parse_commands(ai_text)

        if commands:
            # Show AI response first
            print(self.formatter.format_cli(ai_text))
            print()

            # Execute commands
            for cmd_info in commands:
                cmd = cmd_info["command"]
                level = cmd_info["level"]

                if cmd_info["auto_approve"]:
                    # Auto-execute
                    print(f"\033[1;32m▸\033[0m Executing: {cmd}")
                    result_exec = self.executor.execute(cmd, confirm=True)

                    if result_exec["success"]:
                        # Show output if there is any
                        if result_exec["stdout"].strip():
                            print(result_exec["stdout"])
                    else:
                        print(f"\033[1;31m✗\033[0m {result_exec['stderr']}")
                else:
                    # Ask confirmation
                    if InteractiveConfirm.confirm(cmd, level, cmd_info["reason"]):
                        result_exec = self.executor.execute(cmd, confirm=True)
                        if result_exec["success"]:
                            # Show output if there is any
                            if result_exec["stdout"].strip():
                                print(result_exec["stdout"])
                            else:
                                print("\033[1;32m✓\033[0m Done")
                        else:
                            print(f"\033[1;31m✗\033[0m {result_exec['stderr']}")
                    else:
                        print("\033[1;33m○\033[0m Skipped")
        else:
            # Just print response
            print(self.formatter.format_cli(ai_text))


def show_status():
    """Show comprehensive system status"""
    from core.system_status import show_comprehensive_status
    show_comprehensive_status()

    print("\033[1;33mQuick Start:\033[0m")
    print("  \033[1;37mryx 'prompt'\033[0m          Direct command")
    print("  \033[1;37mryx ::session\033[0m         Interactive mode")
    print("  \033[1;37mryx ::help\033[0m            Show all commands")
    print()


def handle_command(command: str, args: list):
    """Handle special commands (::xxx)"""

    command = command.lower()

    if command in ["::help", "::h"]:
        show_help()

    elif command in ["::session", "::s"]:
        from modes.session_mode import SessionMode
        session = SessionMode()
        session.run()

    elif command in ["::status", "::stat"]:
        show_status()

    elif command in ["::health", "::check"]:
        show_health()

    elif command in ["::config", "::cfg"]:
        show_config()

    elif command in ["::models", "::m"]:
        show_models()

    elif command in ["::clean", "::cleanup", "::gc"]:
        run_cleanup()

    elif command in ["::stop", "::shutdown"]:
        stop_ryx()

    elif command in ["::resume", "::continue"]:
        handle_resume()

    elif command in ["::preferences", "::prefs"]:
        show_preferences()

    elif command in ["::metrics", "::stats"]:
        show_metrics()

    elif command in ["::scrape", "::sc"]:
        if not args:
            print("\033[1;31m✗\033[0m Usage: ryx ::scrape <url>")
            return
        from tools.scraper import WebScraper
        scraper = WebScraper()
        scraper.scrape(args[0])

    elif command in ["::browse", "::br"]:
        if not args:
            print("\033[1;31m✗\033[0m Usage: ryx ::browse <query>")
            return
        from tools.browser import WebBrowser
        browser = WebBrowser()
        browser.search(" ".join(args))

    elif command in ["::council", "::vote"]:
        if not args:
            print("\033[1;31m✗\033[0m Usage: ryx ::council <prompt>")
            return
        from tools.council import Council
        council = Council()
        council.vote(" ".join(args))

    elif command in ["::cache-check", "::validate", "::cache-validate"]:
        # Validate and fix cache
        from tools.cache_validator import run_cache_check
        auto_fix = "--fix" in args or "--auto-fix" in args or len(args) == 0
        run_cache_check(auto_fix=auto_fix, verbose=True)

    elif command in ["::cache-stats", "::cache-info"]:
        # Show cache statistics
        from tools.cache_validator import show_cache_stats
        show_cache_stats()

    else:
        print(f"\033[1;31m✗\033[0m Unknown command: {command}")
        print("  Run \033[1;37mryx ::help\033[0m for available commands")


def show_help():
    """Show comprehensive help"""
    print()
    print("\033[1;36m╭─────────────────────────────────────╮\033[0m")
    print("\033[1;36m│  Ryx AI - Command Reference         │\033[0m")
    print("\033[1;36m╰─────────────────────────────────────╯\033[0m")
    print()
    
    categories = {
        "Basic Usage": [
            ("ryx \"how do I reload hyprland?\"", "Ask questions in natural language"),
            ("ryx \"open my hyprland config\"", "AI interprets and opens files"),
            ("ryx \"find waybar themes\"", "AI searches your system"),
            ("ryx \"show me my keybinds\"", "AI finds and displays info"),
        ],
        "Examples": [
            ("ryx \"edit waybar config in new terminal\"", "Opens in separate window"),
            ("ryx \"what's taking up disk space?\"", "AI investigates and answers"),
            ("ryx \"fix my wifi connection\"", "AI helps troubleshoot"),
        ],
        "Modes": [
            ("ryx ::session", "Interactive chat mode with Ctrl+C support"),
            ("ryx ::s", "Short form: session"),
            ("ryx ::resume", "Resume interrupted task"),
        ],
        "System": [
            ("ryx ::status", "Show system status"),
            ("ryx ::health", "Show health & auto-repair status"),
            ("ryx ::metrics", "Show performance metrics"),
            ("ryx ::preferences", "Show learned preferences"),
            ("ryx ::help", "Show this help"),
            ("ryx ::config", "View/edit configuration"),
            ("ryx ::models", "List AI models"),
        ],
        "Maintenance": [
            ("ryx ::clean", "Run comprehensive cleanup"),
            ("ryx ::stop", "Graceful shutdown"),
        ],
        "Tools": [
            ("ryx ::scrape <url>", "Scrape webpage content"),
            ("ryx ::browse <query>", "Browse web for info"),
            ("ryx ::council <prompt>", "Multi-model consensus"),
        ],
        "Cache Management": [
            ("ryx ::cache-check", "Validate & fix cache"),
            ("ryx ::cache-stats", "Show cache statistics"),
        ]
    }
    
    for category, commands in categories.items():
        print(f"\033[1;33m{category}:\033[0m")
        for cmd, desc in commands:
            print(f"  \033[1;37m{cmd:<30}\033[0m {desc}")
        print()


def show_config():
    """Show current configuration"""
    config_dir = get_project_root() / "configs"
    
    print()
    print("\033[1;36m╭─────────────────────────────────────╮\033[0m")
    print("\033[1;36m│  Configuration                      │\033[0m")
    print("\033[1;36m╰─────────────────────────────────────╯\033[0m")
    print()
    
    # Show settings
    with open(config_dir / "settings.json") as f:
        settings = json.load(f)
    
    print("\033[1;33mSettings:\033[0m")
    print(f"  Default model: \033[1;37m{settings['ai']['default_model']}\033[0m")
    print(f"  Compact mode: \033[1;37m{settings['ai']['compact_responses']}\033[0m")
    print(f"  Cache enabled: \033[1;37m{settings['cache']['enabled']}\033[0m")
    print()
    
    print(f"\033[2mEdit: nvim {config_dir}/settings.json\033[0m")
    print()


def show_models():
    """Show available AI models"""
    from core.ai_engine_v2 import AIEngineV2
    import subprocess

    # Get models from Ollama
    result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
    models = []
    for line in result.stdout.split('\n')[1:]:
        if line.strip():
            models.append(line.split()[0])
    ai = AIEngine()
    models = ai.get_available_models()
    
    print()
    print("\033[1;36m╭─────────────────────────────────────╮\033[0m")
    print("\033[1;36m│  Available Models                   │\033[0m")
    print("\033[1;36m╰─────────────────────────────────────╯\033[0m")
    print()
    
    if models:
        for i, model in enumerate(models, 1):
            print(f"  \033[1;32m{i}.\033[0m {model}")
    else:
        print("  \033[1;33mNo models installed\033[0m")
        print("  \033[2mInstall with: ollama pull <model>\033[0m")
    print()


def run_cleanup():
    """Run comprehensive cleanup tasks"""
    from core.cleanup_manager import CleanupManager

    print()
    print("\033[1;36m▸\033[0m Running comprehensive cleanup...")
    print()

    manager = CleanupManager()

    # Run full cleanup
    stats = manager.cleanup_all(aggressive=False)

    # Display report
    print(manager.format_cleanup_report(stats))

    # Disk usage after cleanup
    usage = manager.get_disk_usage()
    print(f"  \033[1;37mDisk Usage:\033[0m {usage['total_mb']:.2f} MB")
    print(f"    • Databases: {usage['databases_mb']:.2f} MB")
    print(f"    • Logs: {usage['logs_mb']:.2f} MB")
    print(f"    • Cache: {usage['cache_mb']:.2f} MB")
    print()


def stop_ryx():
    """Stop Ryx AI and cleanup"""
    from core.ai_engine_v2 import AIEngineV2

    print()
    print("\033[1;36m▸\033[0m Shutting down Ryx AI...")
    print()

    # Graceful shutdown
    ai = AIEngineV2()

    # Save any pending state
    if ai.task_manager.current_task:
        print("\033[1;33m⚠\033[0m Saving current task state...")
        ai.task_manager.pause_task(ai.task_manager.current_task)

    # Shutdown components
    ai.shutdown()

    print("\033[1;32m✓\033[0m Ryx AI stopped successfully")
    print()


def show_metrics():
    """Show performance metrics"""
    from core.metrics_collector import get_metrics

    metrics = get_metrics()
    print(metrics.format_metrics_for_display())


def handle_resume():
    """Handle resume command"""
    from core.ai_engine_v2 import AIEngineV2

    print()
    print("\033[1;36m▸\033[0m Checking for resumable tasks...")
    print()

    ai = AIEngineV2()
    resumable = ai.get_resumable_tasks()

    if not resumable:
        print("\033[1;33m○\033[0m No tasks to resume")
        print()
        return

    print("\033[1;36mResumable Tasks:\033[0m")
    for i, task in enumerate(resumable, 1):
        print(f"  [{i}] {task.description}")
        print(f"      Status: {task.status.value}, Step: {task.current_step}/{task.total_steps}")
        print(f"      Last updated: {task.updated_at}")
        print()

    choice = input("Resume which task? (number or 'cancel'): ").strip()

    if choice.lower() == 'cancel':
        return

    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(resumable):
            task = resumable[idx]
            resumed = ai.resume_task(task.id)
            if resumed:
                print(f"\033[1;32m✓\033[0m Task resumed: {resumed.description}")
                print(f"   Continue with: ryx ::session")
            else:
                print("\033[1;31m✗\033[0m Failed to resume task")
        else:
            print("\033[1;31m✗\033[0m Invalid task number")
    else:
        print("\033[1;31m✗\033[0m Invalid input")

    print()


def show_health():
    """Show system health status"""
    from core.ai_engine_v2 import AIEngineV2

    print()
    print("\033[1;36m╭─────────────────────────────────────╮\033[0m")
    print("\033[1;36m│  System Health Status               │\033[0m")
    print("\033[1;36m╰─────────────────────────────────────╯\033[0m")
    print()

    ai = AIEngineV2()
    health = ai.health_monitor.get_status()

    # Overall status
    status = health['overall_status']
    if status == 'healthy':
        icon = "\033[1;32m✓\033[0m"
    elif status == 'degraded':
        icon = "\033[1;33m⚠\033[0m"
    else:
        icon = "\033[1;31m✗\033[0m"

    print(f"  Overall: {icon} {status.upper()}")
    print()

    # Components
    print("\033[1;37m  Components:\033[0m")
    for name, check in health['checks'].items():
        if check['status'] == 'healthy':
            icon = "\033[1;32m✓\033[0m"
        elif check['status'] == 'degraded':
            icon = "\033[1;33m⚠\033[0m"
        elif check['status'] == 'critical':
            icon = "\033[1;31m✗\033[0m"
        else:
            icon = "\033[2m?\033[0m"

        print(f"    {icon} {name}: {check['message']}")

    # Model status
    print()
    print("\033[1;37m  Model Orchestrator:\033[0m")
    model_status = ai.orchestrator.get_status()

    for model in model_status['loaded_models']:
        print(f"    \033[1;32m●\033[0m {model['model']} ({model['tier']})")
        print(f"      VRAM: {model['vram_mb']}MB")

    print()


def show_preferences():
    """Show learned preferences"""
    from core.ai_engine_v2 import AIEngineV2

    print()
    print("\033[1;36m╭─────────────────────────────────────╮\033[0m")
    print("\033[1;36m│  Learned Preferences                │\033[0m")
    print("\033[1;36m╰─────────────────────────────────────╯\033[0m")
    print()

    ai = AIEngineV2()
    stats = ai.meta_learner.get_stats()

    if stats['learned_preferences'] == 0:
        print("  \033[2mNo preferences learned yet\033[0m")
        print()
        print("  \033[1;33mTip:\033[0m Tell Ryx your preferences:")
        print("    • 'use nvim not nano'")
        print("    • 'I prefer bash over zsh'")
        print("    • 'always use dark theme'")
        print()
        return

    print(f"  Total preferences: {stats['learned_preferences']}")
    print()

    if stats['top_preferences']:
        print("\033[1;37m  Top Preferences:\033[0m")
        for pref in stats['top_preferences']:
            print(f"    • {pref['key']} = {pref['value']}")
            print(f"      Used {pref['usage_count']} times")

    print()
    print(f"  Total interactions: {stats['total_interactions']}")
    print(f"  Success rate: {stats['success_rate'] * 100:.1f}%")
    print()


def handle_prompt(prompt: str):
    """Entry point for direct prompts"""
    cli = CLIMode()
    cli.handle_prompt(prompt)