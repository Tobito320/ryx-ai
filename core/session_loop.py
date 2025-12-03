"""
Ryx AI - Session Loop: Interactive Session

Copilot CLI / Claude Code style session.

Architecture:
- User prompt → Supervisor (7B) → Refines prompt → Assigns agents → Response
- Supervisor handles search queries with parallel workers
- Style system (normal/concise/explanatory/learning/formal) persisted

Features:
- @ for files, ! for shell
- /commands for control
- Minimal output
- Token streaming with stats
"""

import os
import sys
import json
import readline
import signal
import asyncio
from datetime import datetime
from typing import Optional

from core.paths import get_data_dir
from core.ryx_brain import RyxBrain, Plan, Intent, get_brain
from core.llm_backend import get_backend
from core.model_router import ModelRouter

# Supervisor for intelligent dispatch
try:
    from core.council.supervisor import get_supervisor, Supervisor, ResponseStyle
    HAS_SUPERVISOR = True
except ImportError:
    HAS_SUPERVISOR = False

# Use legacy CLI UI
try:
    from core.cli_ui import get_ui, get_cli, CLI
except ImportError:
    from core.rich_ui import get_ui, RyxUI as CLI
    get_cli = get_ui


class SessionLoop:
    """
    Copilot CLI style interactive session.
    
    Architecture:
    - Supervisor (7B) receives all queries
    - Supervisor refines prompts and dispatches to agents
    - For search: parallel workers via SearXNG
    - For code: uses brain with coding model
    """
    
    def __init__(self, safety_mode: str = "normal"):
        self.safety_mode = safety_mode
        self.cli = get_cli()
        self.router = ModelRouter()
        self.backend = get_backend()  # Auto-detects vLLM
        self.brain = get_brain(self.backend)
        
        # Supervisor for intelligent dispatch
        self.supervisor = None
        if HAS_SUPERVISOR:
            try:
                self.supervisor = get_supervisor()
            except Exception as e:
                pass  # Will fallback to brain
        
        self.running = True
        self.session_start = datetime.now()
        self.history = []
        
        self.stats = {
            'prompts': 0,
            'actions': 0,
            'files': 0,
            'urls': 0,
            'searches': 0,
            'scrapes': 0
        }
        
        # Ctrl+C handling - double tap to exit
        self._last_ctrl_c = 0.0
        self._interrupt_pending = False
        
        # Response style (persisted)
        self._style = self._load_style()
        
        # Last search sources
        self._last_sources = []
        
        self._setup_readline()
        self._setup_signals()
    
    def _load_style(self) -> str:
        """Load response style from config"""
        from pathlib import Path
        config_path = Path.home() / ".config" / "ryx" / "style.json"
        if config_path.exists():
            try:
                import json
                data = json.loads(config_path.read_text())
                return data.get("style", "normal")
            except:
                pass
        return "normal"
    
    def _save_style(self):
        """Save response style to config"""
        from pathlib import Path
        import json
        config_path = Path.home() / ".config" / "ryx" / "style.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps({"style": self._style}))
    
    def _setup_readline(self):
        history_file = get_data_dir() / "history" / "session"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            readline.read_history_file(history_file)
        except FileNotFoundError:
            pass
        
        readline.set_history_length(1000)
        import atexit
        atexit.register(readline.write_history_file, history_file)
    
    def _setup_signals(self):
        import time
        
        def handler(sig, frame):
            now = time.time()
            
            # Double Ctrl+C within 1 second = exit
            if now - self._last_ctrl_c < 1.0:
                print("\n")
                self._save()
                sys.exit(0)
            
            # Single Ctrl+C = interrupt current operation
            self._last_ctrl_c = now
            self._interrupt_pending = True
            print("\n[Ctrl+C to exit]")
        
        signal.signal(signal.SIGINT, handler)
    
    def run(self):
        """Main loop - with bottom bar layout"""
        self._show_welcome()
        self._health_check()
        self._restore()
        
        while self.running:
            try:
                user_input = self.cli.prompt()
                
                if not user_input.strip():
                    continue
                
                self._process(user_input.strip())
                # Single footer (bottom hints) after handling input
                self.cli.footer(msgs=len(self.history))
                
            except KeyboardInterrupt:
                print()
                self._save()
                break
            except Exception as e:
                self.cli.error(str(e))
    
    def _health_check(self):
        """Quick health check - vLLM preferred"""
        health = self.brain.health_check()
        
        if health.get("backend_available", False):
            return  # Backend is running, all good
        
        if health.get("vllm"):
            return  # vLLM is running
        
        # No backend available
        self.cli.error("No LLM backend. Start: ryx start vllm")
    
    def _show_welcome(self):
        """Show welcome - Copilot CLI style"""
        import subprocess
        from core.model_router import select_model
        
        model = select_model("hi").name
        
        # Get git branch
        branch = ""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True, text=True, timeout=1
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
        except:
            pass
        
        self.cli.welcome(model=model, branch=branch, cwd=os.getcwd())
    
    def _process(self, user_input: str):
        """
        Process user input through supervisor.
        
        Flow:
        1. Slash commands handled directly
        2. Search queries → Supervisor → Parallel agents → Synthesized response
        3. Code tasks → Brain (with coding model)
        4. Simple queries → Supervisor direct response
        """
        self.stats['prompts'] += 1
        self.history.append({'role': 'user', 'content': user_input, 'ts': datetime.now().isoformat()})
        self.brain.add_message('user', user_input)
        
        # Pass current style to brain
        self.brain.response_style = self._style
        
        # Slash commands
        if user_input.startswith('/'):
            self._slash_command(user_input)
            return
        
        # @ = file include
        if user_input.startswith('@'):
            self._file_include(user_input[1:])
            return
        
        # ! = shell command
        if user_input.startswith('!'):
            self._shell_command(user_input[1:])
            return
        
        # Handle "show sources" naturally (before other processing)
        lower = user_input.lower().strip()
        if lower in ['show sources', 'sources', 'quellen', 'zeig quellen']:
            self._show_sources()
            return
        
        # Natural language shortcuts (before brain.understand)
        
        # "fix it", "fix that", "fix please", "reparier das" etc.
        fix_patterns = ['fix it', 'fix that', 'fix this', 'fix please', 'please fix',
                       'reparier', 'fixe das', 'behebe', 'korrigiere']
        if any(p in lower for p in fix_patterns) or lower in ['fix', 'fix!']:
            self._fix("")
            return
        
        # ─────────────────────────────────────────────────────────────
        # SUPERVISOR DISPATCH: Route through supervisor if available
        # ─────────────────────────────────────────────────────────────
        
        if self.supervisor:
            try:
                result = self._supervisor_dispatch(user_input)
                if result and result.strip():
                    self.cli.assistant(result)
                    self.history.append({'role': 'assistant', 'content': result, 'ts': datetime.now().isoformat()})
                    self.brain.add_message('assistant', result[:500])
                    self.stats['actions'] += 1
                    return
                # Empty response from supervisor - fall through to brain
            except Exception as e:
                # Fallback to brain on supervisor error
                if "connect" not in str(e).lower():
                    self.cli.warn(f"Supervisor error: {e}")
        
        # ─────────────────────────────────────────────────────────────
        # FALLBACK: Use brain directly
        # ─────────────────────────────────────────────────────────────
        
        # Understand the input
        with self.cli.spinner():
            plan = self.brain.understand(user_input)
        
        # Execute
        success, result = self.brain.execute(plan)
        
        # Always sync sources from brain context (search can happen in CHAT too)
        if hasattr(self.brain, 'ctx') and hasattr(self.brain.ctx, 'pending_items'):
            if self.brain.ctx.pending_items:
                self._last_sources = self.brain.ctx.pending_items
        
        # Track stats
        self.stats['actions'] += 1
        if plan.intent == Intent.OPEN_FILE:
            self.stats['files'] += 1
        elif plan.intent == Intent.OPEN_URL:
            self.stats['urls'] += 1
        elif plan.intent == Intent.SEARCH_WEB:
            self.stats['searches'] += 1
        elif plan.intent in [Intent.SCRAPE, Intent.SCRAPE_HTML]:
            self.stats['scrapes'] += 1
        
        # Show result (skip if streamed)
        if result and result != "__STREAMED__":
            if success:
                if any(result.startswith(c) for c in ['✅', '✓', '📊', '●', '✗']):
                    self.cli.console.print(f"\n{result}")
                else:
                    self.cli.assistant(result)
            else:
                self.cli.error(result)
        
        # Store for history - for streamed responses, get the actual content from brain
        if result == "__STREAMED__":
            # Get the last assistant message from brain's recent messages
            if self.brain._recent_messages:
                for msg in reversed(self.brain._recent_messages):
                    if msg.get('role') == 'assistant':
                        history_result = msg.get('content', '(streamed)')
                        break
                else:
                    history_result = "(streamed)"
            else:
                history_result = "(streamed)"
        else:
            history_result = result
            
        self.history.append({'role': 'assistant', 'content': history_result, 'ts': datetime.now().isoformat()})
        
        # Don't add again if already added by _exec_chat
        if result != "__STREAMED__" and history_result:
            self.brain.add_message('assistant', history_result[:500])
    
    def _slash_command(self, cmd: str):
        """Handle /commands"""
        parts = cmd[1:].split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        cmds = {
            'help': self._help, 'h': self._help, '?': self._help,
            'quit': self._quit, 'exit': self._quit, 'q': self._quit,
            'clear': self._clear, 'c': self._clear,
            'status': self._status, 's': self._status,
            'models': self._models, 'm': self._models, 'model': self._models,
            'precision': lambda: self._precision(args),
            'browsing': lambda: self._browsing(args),
            'scrape': lambda: self._scrape(args),
            'search': lambda: self._search(args),
            'tools': self._tools,
            'undo': lambda: self._undo(args),
            'checkpoints': self._checkpoints, 'cp': self._checkpoints,
            'fix': lambda: self._fix(args),
            'memory': self._memory,
            'benchmark': lambda: self._benchmark(args),
            'style': lambda: self._set_style(args),
            'sources': self._show_sources,
            'metrics': self._metrics,
            'cleanup': self._cleanup,
        }
        
        handler = cmds.get(command)
        if handler:
            handler()
        else:
            self.cli.warn(f"Unknown: {command}")
    
    def _help(self):
        """Show help"""
        self.cli.help_box()
    
    def _quit(self):
        self._save()
        self.running = False
        self.cli.muted("Goodbye")
    
    def _clear(self):
        self.history = []
        self.brain.ctx = type(self.brain.ctx)()
        self.cli.success("Cleared")
    
    def _status(self):
        duration = datetime.now() - self.session_start
        minutes = int(duration.total_seconds() / 60)
        
        precision = "ON" if self.brain.precision_mode else "OFF"
        browsing = "ON" if self.brain.browsing_enabled else "OFF"
        
        self.cli.console.print(f"""
[accent bold]Status[/]
  Precision: {precision}
  Browsing: {browsing}
  Messages: {len(self.history)}
  Duration: {minutes}min
  Prompts: {self.stats['prompts']}
  Searches: {self.stats['searches']}
""")
    
    def _models(self):
        plan = Plan(intent=Intent.LIST_MODELS)
        _, result = self.brain.execute(plan)
        print(result)
    
    def _precision(self, args: str):
        if args.lower() in ['on', '1', 'true']:
            self.brain.precision_mode = True
            self.cli.success("Precision ON")
        elif args.lower() in ['off', '0', 'false']:
            self.brain.precision_mode = False
            self.cli.success("Precision OFF")
        else:
            self.cli.info(f"Precision: {'ON' if self.brain.precision_mode else 'OFF'}")
    
    def _browsing(self, args: str):
        if args.lower() in ['on', '1', 'true']:
            self.brain.browsing_enabled = True
            self.cli.success("Browsing ON")
        elif args.lower() in ['off', '0', 'false']:
            self.brain.browsing_enabled = False
            self.cli.success("Browsing OFF")
        else:
            self.cli.info(f"Browsing: {'ON' if self.brain.browsing_enabled else 'OFF'}")
    
    def _scrape(self, args: str):
        if not args:
            self.cli.error("Usage: /scrape <url>")
            return
        
        with self.cli.spinner("Scraping"):
            plan = Plan(intent=Intent.SCRAPE, target=args.strip())
            success, result = self.brain.execute(plan)
        
        if success:
            print(result)
        else:
            self.cli.error(result)
    
    def _search(self, args: str):
        if not args:
            self.cli.error("Usage: /search <query>")
            return
        
        plan = Plan(intent=Intent.SEARCH_WEB, target=args)
        success, result = self.brain.execute(plan)
        
        # Store sources for /sources command
        if success and hasattr(self.brain, 'ctx') and hasattr(self.brain.ctx, 'pending_items'):
            self._last_sources = self.brain.ctx.pending_items
        
        if success:
            print(result)
        else:
            self.cli.error(result)
    
    def _tools(self):
        """List tools"""
        self.cli.console.print("\n[accent bold]Tools[/]")
        tools = [("web_search", True), ("scrape", True), ("file_ops", True), ("shell", True)]
        for name, enabled in tools:
            status = "[success]ON[/]" if enabled else "[error]OFF[/]"
            self.cli.console.print(f"  {status} {name}")
    
    def _undo(self, args: str):
        """Undo checkpoints"""
        from core.checkpoints import get_checkpoint_manager
        
        cp_mgr = get_checkpoint_manager()
        
        if not cp_mgr.has_checkpoints():
            self.cli.warn("No checkpoints")
            return
        
        count = int(args) if args and args.isdigit() else 1
        results = cp_mgr.undo(count)
        
        for name, success, msg in results:
            if success:
                self.cli.success(f"Undone: {name}")
            else:
                self.cli.error(f"Failed: {name}")
    
    def _checkpoints(self):
        """List checkpoints"""
        from core.checkpoints import get_checkpoint_manager
        
        cp_mgr = get_checkpoint_manager()
        checkpoints = cp_mgr.list_checkpoints(limit=10)
        
        if not checkpoints:
            self.cli.info("No checkpoints")
            return
        
        self.cli.console.print("\n[accent bold]Checkpoints[/]")
        for cp in checkpoints:
            time_str = cp['timestamp'].split('T')[1][:5] if 'T' in cp['timestamp'] else ""
            self.cli.console.print(f"  [dim]{cp['id'][:8]}[/] {cp['name']} [{time_str}]")
    
    def _fix(self, args: str):
        """
        Fix the last error or a specific issue.
        
        Usage:
            /fix           - Fix last error automatically
            /fix <issue>   - Fix a specific issue
        """
        if args:
            # User described a problem - treat as code task
            fix_prompt = f"Fix this issue: {args}"
        else:
            # No args - try to fix last error from history
            last_error = None
            for msg in reversed(self.history):
                content = msg.get('content', '')
                if 'error' in content.lower() or 'failed' in content.lower():
                    last_error = content
                    break
            
            if last_error:
                fix_prompt = f"Fix this error that just occurred:\n{last_error}"
            else:
                self.cli.warn("No recent errors to fix. Use: /fix <description>")
                return
        
        self.cli.info("🔧 Analyzing and fixing...")
        
        # Use the brain to understand and execute the fix
        with self.cli.spinner():
            plan = self.brain.understand(fix_prompt)
        
        success, result = self.brain.execute(plan)
        
        if result and result != "__STREAMED__":
            if success:
                self.cli.success("Fix applied")
                self.cli.assistant(result)
            else:
                self.cli.error(f"Fix failed: {result}")
    
    def _memory(self):
        """Show experience memory stats"""
        try:
            from core.memory import get_memory
            
            memory = get_memory()
            stats = memory.get_stats()
            
            self.cli.console.print("\n[accent bold]Experience Memory[/]")
            self.cli.console.print(f"  Total experiences: {stats['total']}")
            self.cli.console.print(f"  Success rate: {stats['success_rate']:.1%}")
            
            if stats['by_type']:
                self.cli.console.print("\n  By type:")
                for t, count in stats['by_type'].items():
                    self.cli.console.print(f"    {t}: {count}")
            
            if stats['by_category']:
                self.cli.console.print("\n  By category:")
                for c, count in list(stats['by_category'].items())[:5]:
                    self.cli.console.print(f"    {c}: {count}")
                    
        except ImportError:
            self.cli.warn("Memory system not available")
        except Exception as e:
            self.cli.error(f"Memory error: {e}")
    
    def _benchmark(self, args: str):
        """Run a quick benchmark"""
        try:
            from core.benchmarks import BenchmarkRegistry
            
            if not args:
                # List benchmarks
                self.cli.console.print("\n[accent bold]Benchmarks[/]")
                for name in BenchmarkRegistry.list_all():
                    b = BenchmarkRegistry.create(name)
                    self.cli.console.print(f"  {name}: {len(b.problems)} problems")
                self.cli.console.print("\nUse: /benchmark <name>")
            else:
                self.cli.info(f"Run: ryx benchmark run {args}")
                
        except ImportError:
            self.cli.warn("Benchmark system not available")
        except Exception as e:
            self.cli.error(f"Benchmark error: {e}")
    
    def _set_style(self, args: str):
        """Set response style: normal, concise, explanatory, learning, formal"""
        valid_styles = ["normal", "concise", "explanatory", "learning", "formal"]
        
        if not args:
            self.cli.console.print(f"\n[accent bold]Response Style[/]")
            self.cli.console.print(f"  Current: {self._style}")
            self.cli.console.print(f"\n  Available:")
            for s in valid_styles:
                marker = "→" if s == self._style else " "
                self.cli.console.print(f"    {marker} {s}")
            self.cli.console.print(f"\nUse: /style <name>")
            return
        
        style = args.lower().strip()
        if style not in valid_styles:
            self.cli.error(f"Unknown style: {style}")
            self.cli.info(f"Available: {', '.join(valid_styles)}")
            return
        
        self._style = style
        self._save_style()
        self.cli.success(f"Style set to: {style}")
    
    def _metrics(self):
        """Show model performance metrics"""
        try:
            from core.council.metrics import ModelMetrics
            
            metrics = ModelMetrics()
            summary = metrics.get_summary()
            
            self.cli.console.print(f"\n[accent bold]Model Metrics[/]")
            self.cli.console.print(f"  Total models: {summary['total_models']}")
            self.cli.console.print(f"  Active: {summary['active_models']}")
            self.cli.console.print(f"  Fired: {summary['fired_models']}")
            self.cli.console.print(f"  Promoted: {summary['promoted_models']}")
            
            if summary['models']:
                self.cli.console.print(f"\n  [dim]Performance:[/]")
                for name, stats in summary['models'].items():
                    short_name = name.split('/')[-1] if '/' in name else name
                    self.cli.console.print(
                        f"    {stats['status']} {short_name}: "
                        f"{stats['success_rate']} success, "
                        f"{stats['avg_quality']} quality, "
                        f"{stats['avg_latency']}"
                    )
            else:
                self.cli.console.print(f"\n  [dim]No metrics yet. Run some tasks first.[/]")
                
        except ImportError:
            self.cli.warn("Metrics system not available")
        except Exception as e:
            self.cli.error(f"Metrics error: {e}")
    
    def _cleanup(self):
        """Cleanup Docker resources"""
        import subprocess
        
        self.cli.info("Cleaning up Docker resources...")
        try:
            # Run docker system prune
            result = subprocess.run(
                ["docker", "system", "prune", "-f"],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                self.cli.success("Docker cleanup complete")
                if result.stdout:
                    # Show space reclaimed
                    for line in result.stdout.split('\n'):
                        if 'reclaimed' in line.lower():
                            self.cli.console.print(f"  {line}")
            else:
                self.cli.error(f"Cleanup failed: {result.stderr}")
        except Exception as e:
            self.cli.error(f"Cleanup error: {e}")
    
    def _show_sources(self):
        """Show sources from last search"""
        # Check both local cache and brain context
        sources = self._last_sources or getattr(self.brain.ctx, 'pending_items', [])
        
        if not sources:
            self.cli.warn("No sources. Run a search first.")
            return
        
        self.cli.console.print(f"\n[accent bold]Sources ({len(sources)})[/]")
        for i, src in enumerate(sources, 1):
            title = src.get('title', 'Unknown')
            url = src.get('url', '')
            self.cli.console.print(f"  [{i}] {title}")
            self.cli.console.print(f"      [dim]{url}[/]")
    
    def _supervisor_dispatch(self, user_input: str) -> Optional[str]:
        """
        Dispatch query through supervisor.
        
        The supervisor:
        1. Refines the user's prompt (fixes typos, clarifies intent)
        2. Decides what type of task this is (search, chat, code)
        3. Assigns appropriate agents
        4. Synthesizes results based on style
        
        Returns:
            Response string, or None to fallback to brain
        """
        if not self.supervisor:
            return None
        
        # Map style string to enum
        style = None
        if HAS_SUPERVISOR:
            try:
                style = ResponseStyle(self._style)
            except:
                style = ResponseStyle.NORMAL
        
        # Build context for follow-up queries
        context = {}
        if self.history:
            # Get last assistant response for follow-ups
            for msg in reversed(self.history):
                if msg.get('role') == 'assistant':
                    context['last_response'] = msg.get('content', '')[:1000]
                    break
        
        # Run async supervisor in sync context
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Show spinner while processing
        with self.cli.spinner():
            result = loop.run_until_complete(
                self.supervisor.handle_query(user_input, style=style, context=context)
            )
        
        if not result:
            return None
        
        response = result.get("response", "")
        sources = result.get("sources", [])
        
        # Store sources for /sources command
        if sources:
            self._last_sources = [
                {"title": s.split("] ")[1].split(" - ")[0] if "] " in s else s,
                 "url": s.split(" - ")[-1] if " - " in s else ""}
                for s in sources if isinstance(s, str)
            ]
            # Also accept dict format
            if sources and isinstance(sources[0], dict):
                self._last_sources = sources
        
        # Track search stat
        if result.get("type") != "direct":
            self.stats['searches'] += 1
        
        return response if response else None

    def _file_include(self, path: str):
        """Include file contents with @"""
        path = os.path.expanduser(path.strip())
        
        if not os.path.exists(path):
            self.cli.error(f"Not found: {path}")
            return
        
        try:
            with open(path, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            preview = '\n'.join(lines[:15])
            if len(lines) > 15:
                preview += f"\n... ({len(lines) - 15} more lines)"
            
            self.cli.console.print(f"\n[dim]─ {path}[/]")
            self.cli.console.print(preview)
            
            self.brain.ctx.last_path = path
            
        except Exception as e:
            self.cli.error(str(e))
    
    def _shell_command(self, cmd: str):
        """Run shell command with !"""
        import subprocess
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                self.cli.console.print(f"[warning]{result.stderr}[/]")
            
            if result.returncode != 0:
                self.cli.warn(f"Exit: {result.returncode}")
                
        except subprocess.TimeoutExpired:
            self.cli.error("Timeout")
        except Exception as e:
            self.cli.error(str(e))
    
    def _save(self):
        state_file = get_data_dir() / "session_state.json"
        
        context_data = {
            'last_path': self.brain.ctx.last_path,
            'last_result': self.brain.ctx.last_result[:500] if self.brain.ctx.last_result else "",
            'last_intent': self.brain.ctx.last_intent.value if self.brain.ctx.last_intent else None,
            'created_files': getattr(self.brain.ctx, 'created_files', []),
        }
        
        state = {
            'history': self.history[-50:],
            'stats': self.stats,
            'precision_mode': self.brain.precision_mode,
            'browsing_enabled': self.brain.browsing_enabled,
            'context': context_data,
            'saved_at': datetime.now().isoformat()
        }
        
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _restore(self):
        state_file = get_data_dir() / "session_state.json"
        
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                
                self.history = state.get('history', [])
                self.brain.precision_mode = state.get('precision_mode', False)
                self.brain.browsing_enabled = state.get('browsing_enabled', True)
                
                ctx = state.get('context', {})
                if ctx:
                    self.brain.ctx.last_path = ctx.get('last_path', '')
                    self.brain.ctx.last_result = ctx.get('last_result', '')
                    if ctx.get('last_intent'):
                        try:
                            self.brain.ctx.last_intent = Intent(ctx['last_intent'])
                        except:
                            pass
                    self.brain.ctx.created_files = ctx.get('created_files', [])
                
                if self.history:
                    self.cli.muted(f"Restored ({len(self.history)} messages)")
                    
            except Exception:
                pass


def main():
    session = SessionLoop()
    session.run()


if __name__ == "__main__":
    main()
