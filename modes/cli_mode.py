"""
Ryx AI - CLI Mode
Ultra-fast one-shot command execution
"""

import sys
import json
from pathlib import Path
from typing import Optional

from core.ai_engine import AIEngine, ResponseFormatter
from core.rag_system import RAGSystem, FileFinder
from core.permissions import PermissionManager, CommandExecutor, InteractiveConfirm

class CLIMode:
    def __init__(self):
        self.ai = AIEngine()
        self.rag = RAGSystem()
        self.file_finder = FileFinder(self.rag)
        self.perm_manager = PermissionManager()
        self.executor = CommandExecutor(self.perm_manager)
        self.formatter = ResponseFormatter()
    
    def handle_prompt(self, prompt: str):
        """Handle direct prompt"""
        
        # Check cache first (0-latency path)
        cached = self.rag.query_cache(prompt)
        if cached:
            print("\033[2m[cached]\033[0m")
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
                        cmd = f"nvim {file_path}"
                        print(f"\033[1;32m▸\033[0m Opening {file_path}")
                        result = self.executor.execute(cmd, confirm=True)
                        
                        if result["success"]:
                            # Cache this for next time
                            self.rag.cache_response(prompt, f"```bash\n{cmd}\n```", "cached")
                        return
        
        # Get context
        context = self.rag.get_context(prompt)
        
        # Query AI
        print("\033[2m[thinking...]\033[0m", end="\r")
        response = self.ai.query(prompt, context)
        print(" " * 20, end="\r")  # Clear "thinking"
        
        if response["error"]:
            print(f"\033[1;31m✗\033[0m {response['response']}")
            return
        
        ai_text = response["response"]
        
        # Cache response
        self.rag.cache_response(prompt, ai_text, response["model"])
        
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
                    result = self.executor.execute(cmd, confirm=True)
                    
                    if not result["success"]:
                        print(f"\033[1;31m✗\033[0m {result['stderr']}")
                else:
                    # Ask confirmation
                    if InteractiveConfirm.confirm(cmd, level, cmd_info["reason"]):
                        result = self.executor.execute(cmd, confirm=True)
                        if result["success"]:
                            print("\033[1;32m✓\033[0m Done")
                        else:
                            print(f"\033[1;31m✗\033[0m {result['stderr']}")
                    else:
                        print("\033[1;33m○\033[0m Skipped")
        else:
            # Just print response
            print(self.formatter.format_cli(ai_text))


def show_status():
    """Show system status and available commands"""
    print()
    print("\033[1;36m╭─────────────────────────────────────╮\033[0m")
    print("\033[1;36m│  Ryx AI - Arch Linux Assistant      │\033[0m")
    print("\033[1;36m╰─────────────────────────────────────╯\033[0m")
    print()
    
    # Check if AI is available
    ai = AIEngine()
    if ai.is_available():
        print("\033[1;32m●\033[0m AI Engine: \033[1;32mOnline\033[0m")
        models = ai.get_available_models()
        print(f"\033[2m  Models: {', '.join(models[:3])}\033[0m")
    else:
        print("\033[1;31m●\033[0m AI Engine: \033[1;31mOffline\033[0m")
        print("\033[1;33m  Start with: ollama serve\033[0m")
    
    # Get RAG stats
    rag = RAGSystem()
    stats = rag.get_stats()
    
    print(f"\033[1;32m●\033[0m Cache: {stats['cached_responses']} responses")
    print(f"\033[2m  Hit rate: {stats['total_cache_hits']} total hits\033[0m")
    
    print(f"\033[1;32m●\033[0m Knowledge: {stats['known_files']} learned files")
    
    rag.close()
    
    print()
    print("\033[1;33mUsage:\033[0m")
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
    
    elif command in ["::config", "::cfg"]:
        show_config()
    
    elif command in ["::models", "::m"]:
        show_models()
    
    elif command in ["::clean", "::gc"]:
        run_cleanup()
    
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
            ("ryx 'prompt'", "Ask AI and get instant response"),
            ("ryx open hyprland config", "Find and open files"),
            ("ryx find all waybar themes", "Search system"),
        ],
        "Modes": [
            ("ryx ::session", "Interactive chat mode"),
            ("ryx ::s", "Short form: session"),
        ],
        "System": [
            ("ryx ::status", "Show system status"),
            ("ryx ::help", "Show this help"),
            ("ryx ::config", "View/edit configuration"),
            ("ryx ::models", "List AI models"),
            ("ryx ::clean", "Run cleanup tasks"),
        ],
        "Tools": [
            ("ryx ::scrape <url>", "Scrape webpage content"),
            ("ryx ::browse <query>", "Browse web for info"),
            ("ryx ::council <prompt>", "Multi-model consensus"),
        ]
    }
    
    for category, commands in categories.items():
        print(f"\033[1;33m{category}:\033[0m")
        for cmd, desc in commands:
            print(f"  \033[1;37m{cmd:<30}\033[0m {desc}")
        print()


def show_config():
    """Show current configuration"""
    config_dir = Path.home() / "ryx-ai" / "configs"
    
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
    """Run cleanup tasks"""
    print()
    print("\033[1;36m▸\033[0m Running cleanup...")
    print()
    
    rag = RAGSystem()
    
    # Clean old cache
    deleted = rag.cleanup_old_cache(days=30)
    print(f"\033[1;32m✓\033[0m Removed {deleted} old cache entries")
    
    # Get stats
    stats = rag.get_stats()
    print(f"\033[1;32m✓\033[0m Current cache: {stats['cached_responses']} entries")
    
    rag.close()
    
    print()
    print("\033[1;32m✓\033[0m Cleanup complete")
    print()


def handle_prompt(prompt: str):
    """Entry point for direct prompts"""
    cli = CLIMode()
    cli.handle_prompt(prompt)