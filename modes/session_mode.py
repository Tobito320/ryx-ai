"""
Ryx AI - Session Mode
Interactive Gemini CLI-like experience
"""

import sys
from typing import List, Dict

<<<<<<< HEAD
from core.ai_engine_v2 import AIEngineV2, ResponseFormatter
from core.rag_system import RAGSystem, FileFinder
from core.permissions import PermissionManager, CommandExecutor, InteractiveConfirm
from core.task_manager import InterruptionHandler

class SessionMode:
    def __init__(self):
        self.ai = AIEngineV2()
        self.rag = self.ai.rag  # Use RAG from integrated engine
        self.file_finder = self.ai.file_finder  # Use file finder from integrated engine
        self.perm_manager = PermissionManager()
        self.executor = CommandExecutor(self.perm_manager)
        self.formatter = ResponseFormatter()

        self.conversation_history = []
        self.pending_commands = []
        self.running = True

        # Install interrupt handler for Ctrl+C
        self.interrupt_handler = InterruptionHandler(self.ai.task_manager)
        self.interrupt_handler.install_handler()
=======
from core.ai_engine import AIEngine, ResponseFormatter
from core.rag_system import RAGSystem, FileFinder
from core.permissions import PermissionManager, CommandExecutor, InteractiveConfirm

class SessionMode:
    def __init__(self):
        self.ai = AIEngine()
        self.rag = RAGSystem()
        self.file_finder = FileFinder(self.rag)
        self.perm_manager = PermissionManager()
        self.executor = CommandExecutor(self.perm_manager)
        self.formatter = ResponseFormatter()
        
        self.conversation_history = []
        self.pending_commands = []
        self.running = True
>>>>>>> 9776c4f33e86c9cd995868ae5ae5bf0c8cd7a6b8
    
    def run(self):
        """Main session loop"""
        self.show_header()
        
        while self.running:
            try:
                # Get user input
                prompt = input("\n\033[1;32mYou:\033[0m ").strip()
                
                if not prompt:
                    continue
                
                # Check for session commands
                if prompt.startswith('/'):
                    self.handle_session_command(prompt)
                    continue
                
                # Add to conversation
                self.conversation_history.append({
                    "role": "user",
                    "content": prompt
                })
                
                # Check cache
                cached = self.rag.query_cache(prompt)
                if cached:
                    print("\033[2m[cached]\033[0m")
                    self.display_response(cached)
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": cached
                    })
                    continue
                
                # Build context from conversation
                context = self.build_conversation_context()
                context += "\n" + self.rag.get_context(prompt)
                
                # Query AI
                print("\033[1;34mRyx:\033[0m ", end="")
                sys.stdout.flush()
                
                response = self.ai.query(prompt, context)
                
                if response["error"]:
                    print(f"\n\033[1;31m✗\033[0m {response['response']}")
                    continue
                
                ai_text = response["response"]
                
                # Display response
                self.display_response(ai_text)
                
                # Add to conversation
                self.conversation_history.append({
                    "role": "assistant",
                    "content": ai_text
                })
                
                # Cache response
                self.rag.cache_response(prompt, ai_text, response["model"])
                
                # Parse commands
                commands = self.executor.parse_commands(ai_text)
                
                if commands:
                    self.pending_commands = commands
                    self.show_pending_commands()
                
            except KeyboardInterrupt:
                print("\n\n\033[1;33mUse /quit to exit\033[0m")
                continue
            except EOFError:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\n\033[1;31m✗ Error:\033[0m {str(e)}")
    
    def show_header(self):
        """Show session header"""
        print()
        print("\033[1;36m╭──────────────────────────────────────────╮\033[0m")
        print("\033[1;36m│  Ryx AI - Interactive Session           │\033[0m")
        print("\033[1;36m╰──────────────────────────────────────────╯\033[0m")
        print()
        print("\033[2mCommands: /help /quit /clear /exec /undo\033[0m")
        print("\033[2mJust type naturally - I'm here to help\033[0m")
    
    def display_response(self, response: str):
        """Display AI response with formatting"""
        formatted = self.formatter.format_cli(response)
        print(formatted)
    
    def build_conversation_context(self) -> str:
        """Build context from recent conversation"""
        # Keep last 6 messages (3 exchanges)
        recent = self.conversation_history[-6:]
        
        context_lines = []
        for msg in recent:
            role = "User" if msg["role"] == "user" else "Assistant"
            context_lines.append(f"{role}: {msg['content']}")
        
        return "\n".join(context_lines)
    
    def show_pending_commands(self):
        """Show commands ready to execute"""
        print()
        print("\033[1;33m⚡ Detected Actions:\033[0m")
        
        for i, cmd_info in enumerate(self.pending_commands, 1):
            cmd = cmd_info["command"]
            level = cmd_info["level"].value
            
            if cmd_info["auto_approve"]:
                marker = "\033[1;32m✓\033[0m"
            else:
                marker = "\033[1;33m?\033[0m"
            
            print(f"  {marker} [{i}] {cmd}")
            print(f"      \033[2m{cmd_info['reason']}\033[0m")
        
        print()
        print("\033[2mRun with: /exec [number] or /exec all\033[0m")
    
    def handle_session_command(self, command: str):
        """Handle session-specific commands"""
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd in ['/quit', '/exit', '/q']:
            print("\nGoodbye! 👋")
            self.running = False
        
        elif cmd == '/clear':
            self.conversation_history = []
            self.pending_commands = []
            print("\n\033[1;32m✓\033[0m Conversation cleared")
        
        elif cmd == '/help':
            self.show_session_help()
        
        elif cmd == '/exec':
            self.execute_pending(parts[1] if len(parts) > 1 else "all")
        
        elif cmd == '/undo':
            if self.conversation_history:
                self.conversation_history.pop()
                if self.conversation_history:
                    self.conversation_history.pop()  # Remove AI response too
                print("\033[1;32m✓\033[0m Last exchange undone")
            else:
                print("\033[1;33m○\033[0m Nothing to undo")
        
        elif cmd == '/status':
            self.show_session_status()
        
        elif cmd == '/save':
            filename = parts[1] if len(parts) > 1 else "conversation.txt"
            self.save_conversation(filename)
<<<<<<< HEAD

        elif cmd == '/resume' or cmd == '::resume':
            self.handle_resume()

        elif cmd == '/health' or cmd == '::health':
            self.show_health_status()

        elif cmd == '/models' or cmd == '::models':
            self.show_model_status()

=======
        
>>>>>>> 9776c4f33e86c9cd995868ae5ae5bf0c8cd7a6b8
        else:
            print(f"\033[1;31m✗\033[0m Unknown command: {cmd}")
            print("  Type /help for available commands")
    
    def execute_pending(self, which: str = "all"):
        """Execute pending commands"""
        if not self.pending_commands:
            print("\033[1;33m○\033[0m No pending commands")
            return
        
        to_execute = []
        
        if which == "all":
            to_execute = self.pending_commands
        elif which.isdigit():
            idx = int(which) - 1
            if 0 <= idx < len(self.pending_commands):
                to_execute = [self.pending_commands[idx]]
            else:
                print(f"\033[1;31m✗\033[0m Invalid command number: {which}")
                return
        else:
            print(f"\033[1;31m✗\033[0m Usage: /exec [number|all]")
            return
        
        print()
        for cmd_info in to_execute:
            cmd = cmd_info["command"]
            
            # Check if confirmation needed
            if not cmd_info["auto_approve"]:
                if not InteractiveConfirm.confirm(
                    cmd, 
                    cmd_info["level"], 
                    cmd_info["reason"]
                ):
                    print("\033[1;33m○\033[0m Skipped")
                    continue
            
            # Execute
            print(f"\033[1;32m▸\033[0m {cmd}")
            result = self.executor.execute(cmd, confirm=True)
            
            if result["success"]:
                print("\033[1;32m✓\033[0m Done")
                if result["stdout"]:
                    print(f"\033[2m{result['stdout']}\033[0m")
            else:
                print(f"\033[1;31m✗\033[0m {result['stderr']}")
        
        self.pending_commands = []
    
    def show_session_help(self):
        """Show session help"""
        print()
        print("\033[1;36m╭─────────────────────────────────────╮\033[0m")
        print("\033[1;36m│  Session Commands                   │\033[0m")
        print("\033[1;36m╰─────────────────────────────────────╯\033[0m")
        print()
        
        commands = [
            ("/quit, /exit, /q", "Exit session"),
            ("/clear", "Clear conversation history"),
            ("/help", "Show this help"),
            ("/exec [number|all]", "Execute pending commands"),
            ("/undo", "Undo last exchange"),
            ("/status", "Show session status"),
            ("/save [filename]", "Save conversation to file"),
<<<<<<< HEAD
            ("/resume, ::resume", "Resume paused/interrupted task"),
            ("/health, ::health", "Show system health status"),
            ("/models, ::models", "Show model orchestrator status"),
=======
>>>>>>> 9776c4f33e86c9cd995868ae5ae5bf0c8cd7a6b8
        ]
        
        for cmd, desc in commands:
            print(f"  \033[1;37m{cmd:<25}\033[0m {desc}")
        print()
    
    def show_session_status(self):
        """Show current session status"""
        print()
        print(f"\033[1;36mSession Status:\033[0m")
        print(f"  Messages: {len(self.conversation_history)}")
        print(f"  Pending commands: {len(self.pending_commands)}")
        
        # Get cache stats
        stats = self.rag.get_stats()
        print(f"  Cache hits: {stats['total_cache_hits']}")
        print()
    
    def save_conversation(self, filename: str):
        """Save conversation to file"""
        from datetime import datetime
<<<<<<< HEAD

        output_path = Path.home() / "ryx-ai" / "data" / "history" / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            f.write(f"# Ryx AI Conversation\n")
            f.write(f"# Saved: {datetime.now().isoformat()}\n\n")

=======
        
        output_path = Path.home() / "ryx-ai" / "data" / "history" / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(f"# Ryx AI Conversation\n")
            f.write(f"# Saved: {datetime.now().isoformat()}\n\n")
            
>>>>>>> 9776c4f33e86c9cd995868ae5ae5bf0c8cd7a6b8
            for msg in self.conversation_history:
                role = msg["role"].title()
                content = msg["content"]
                f.write(f"## {role}\n\n{content}\n\n")
<<<<<<< HEAD

        print(f"\033[1;32m✓\033[0m Saved to: {output_path}")

    def handle_resume(self):
        """Handle resume command - resume paused tasks"""
        resumable = self.ai.get_resumable_tasks()

        if not resumable:
            print("\033[1;33m○\033[0m No tasks to resume")
            return

        print()
        print("\033[1;36mResumable Tasks:\033[0m")
        for i, task in enumerate(resumable, 1):
            print(f"  [{i}] {task.description}")
            print(f"      Status: {task.status.value}, Step: {task.current_step}/{task.total_steps}")
            print(f"      Updated: {task.updated_at}")

        print()
        choice = input("Resume which task? (number or 'cancel'): ").strip()

        if choice.lower() == 'cancel':
            return

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(resumable):
                task = resumable[idx]
                resumed = self.ai.resume_task(task.id)
                if resumed:
                    print(f"\033[1;32m✓\033[0m Resumed task: {resumed.description}")
                else:
                    print("\033[1;31m✗\033[0m Failed to resume task")
            else:
                print("\033[1;31m✗\033[0m Invalid task number")
        else:
            print("\033[1;31m✗\033[0m Invalid input")

    def show_health_status(self):
        """Show system health status"""
        health = self.ai.health_monitor.get_status()

        print()
        print("\033[1;36m╭─────────────────────────────────────╮\033[0m")
        print("\033[1;36m│  System Health Status               │\033[0m")
        print("\033[1;36m╰─────────────────────────────────────╯\033[0m")
        print()

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

        # Component checks
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

        # Recent incidents
        if health['recent_incidents']:
            print()
            print("\033[1;37m  Recent Incidents:\033[0m")
            for incident in health['recent_incidents'][-3:]:
                auto_fixed = "✓ auto-fixed" if incident['auto_fixed'] else "✗ not fixed"
                print(f"    • {incident['type']}: {incident['description']}")
                print(f"      {auto_fixed}")

        print()

    def show_model_status(self):
        """Show model orchestrator status"""
        status = self.ai.orchestrator.get_status()

        print()
        print("\033[1;36m╭─────────────────────────────────────╮\033[0m")
        print("\033[1;36m│  Model Status                       │\033[0m")
        print("\033[1;36m╰─────────────────────────────────────╯\033[0m")
        print()

        # Loaded models
        print("\033[1;37m  Loaded Models:\033[0m")
        if status['loaded_models']:
            for model in status['loaded_models']:
                last_used = int(model['last_used'])
                print(f"    \033[1;32m●\033[0m {model['model']} ({model['tier']})")
                print(f"      VRAM: {model['vram_mb']}MB, Last used: {last_used}s ago")
        else:
            print("    \033[2mNo models loaded\033[0m")

        print()

        # Available models
        print("\033[1;37m  Available Models:\033[0m")
        for model in status['available_models']:
            if model['loaded']:
                icon = "\033[1;32m●\033[0m"
            else:
                icon = "\033[2m○\033[0m"

            print(f"    {icon} {model['model']} ({model['tier']})")
            print(f"      VRAM: {model['vram_mb']}MB")

        print()
        print(f"  Query history: {status['query_history']} queries")
        print()

=======
        
        print(f"\033[1;32m✓\033[0m Saved to: {output_path}")

>>>>>>> 9776c4f33e86c9cd995868ae5ae5bf0c8cd7a6b8

def main():
    """Entry point for session mode"""
    session = SessionMode()
    session.run()