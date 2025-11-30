"""
Ryx AI - Session Loop
Main interactive session for the Ryx AI CLI
"""

import sys
import signal
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from core.intent_classifier import IntentClassifier, IntentType, ClassifiedIntent
from core.model_router import ModelRouter, ModelTier
from core.ollama_client import OllamaClient
from core.tool_registry import ToolRegistry
from core.ui import RyxUI, Color, Emoji
from core.paths import get_project_root, get_data_dir


class SessionLoop:
    """
    Main interactive session loop for Ryx AI

    Features:
    - Natural language interaction (no weird syntax)
    - Automatic intent classification
    - Intelligent model routing
    - Tool orchestration
    - Purple-themed UI with emoji indicators
    - Graceful interrupts
    """

    def __init__(self, safety_mode: str = "normal"):
        """
        Initialize session

        Args:
            safety_mode: 'strict', 'normal', or 'loose'
        """
        self.ui = RyxUI()
        self.router = ModelRouter()
        self.ollama = OllamaClient(base_url=self.router.get_ollama_url())
        self.classifier = IntentClassifier(ollama_client=self.ollama)
        self.tools = ToolRegistry(safety_mode=safety_mode)

        # Session state
        self.running = True
        self.current_tier: Optional[ModelTier] = None
        self.conversation_history: List[Dict[str, str]] = []
        self.context: Dict[str, Any] = {}
        self.safety_mode = safety_mode

        # Session file for persistence
        self.session_file = get_data_dir() / "session_state.json"

        # Install signal handlers
        signal.signal(signal.SIGINT, self._handle_interrupt)

        # Try to restore previous session
        self._restore_session()

    def _handle_interrupt(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print()
        self.ui.warning("Session interrupted (Ctrl+C)")
        self._save_session()
        self.ui.info("Session saved. Run 'ryx' to continue.")
        sys.exit(0)

    def _save_session(self):
        """Save session state"""
        try:
            self.session_file.parent.mkdir(parents=True, exist_ok=True)

            state = {
                'saved_at': datetime.now().isoformat(),
                'conversation_history': self.conversation_history[-50:],
                'current_tier': self.current_tier.value if self.current_tier else None,
                'context': self.context
            }

            with open(self.session_file, 'w') as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            self.ui.error(f"Failed to save session: {e}")

    def _restore_session(self):
        """Restore previous session if exists"""
        if not self.session_file.exists():
            return

        try:
            with open(self.session_file, 'r') as f:
                state = json.load(f)

            self.conversation_history = state.get('conversation_history', [])

            tier_value = state.get('current_tier')
            if tier_value:
                self.current_tier = ModelTier(tier_value)

            self.context = state.get('context', {})

            if self.conversation_history:
                self.ui.info(f"Restored {len(self.conversation_history)} messages from previous session")

        except Exception:
            pass

    def run(self):
        """Main session loop"""
        # Show header
        model = self.router.get_model(self.current_tier)
        tier_name = self.current_tier.value if self.current_tier else "balanced"
        self.ui.header(
            tier=tier_name,
            model=model.name,
            repo=str(get_project_root()),
            safety=self.safety_mode
        )

        self.ui.info("Type naturally. Use /help for commands.")
        print()

        while self.running:
            try:
                # Get user input
                user_input = self.ui.prompt()

                if not user_input:
                    continue

                # Process input
                self._process_input(user_input)

            except KeyboardInterrupt:
                print()
                continue
            except EOFError:
                break

        self._save_session()
        self.ui.info("Goodbye!")

    def _process_input(self, user_input: str):
        """Process user input"""
        # Classify intent
        intent = self.classifier.classify(user_input, self.context)

        # Handle tier override
        if intent.tier_override:
            tier = self.router.get_tier_by_name(intent.tier_override)
            if tier:
                self.current_tier = tier
                model = self.router.get_model(tier)
                self.ui.success(f"Switched to {tier.value} tier ({model.name})")

        # Handle slash commands
        if intent.flags.get('is_slash_command'):
            self._handle_slash_command(intent)
            return

        # Handle simple greetings
        if intent.intent_type == IntentType.CHAT and self._is_greeting(user_input):
            self._handle_greeting(user_input)
            return

        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })

        # Route based on intent type
        if intent.intent_type == IntentType.CHAT:
            self._handle_chat(user_input, intent)
        elif intent.intent_type == IntentType.FILE_OPS:
            self._handle_file_ops(user_input, intent)
        elif intent.intent_type in [IntentType.CODE_EDIT, IntentType.CONFIG_EDIT]:
            self._handle_code_task(user_input, intent)
        elif intent.intent_type == IntentType.WEB_RESEARCH:
            self._handle_web_research(user_input, intent)
        elif intent.intent_type == IntentType.SYSTEM_TASK:
            self._handle_system_task(user_input, intent)
        elif intent.intent_type == IntentType.KNOWLEDGE_RAG:
            self._handle_rag(user_input, intent)
        elif intent.intent_type == IntentType.PERSONAL_CHAT:
            self._handle_personal_chat(user_input, intent)
        else:
            self._handle_chat(user_input, intent)

    def _handle_slash_command(self, intent: ClassifiedIntent):
        """Handle slash commands"""
        target = intent.target
        args = intent.flags.get('args', '')

        if target == 'show_help':
            self.ui.help()

        elif target == 'show_status':
            self._show_status()

        elif target == 'set_tier':
            tier_name = intent.flags.get('tier') or args
            if tier_name:
                tier = self.router.get_tier_by_name(tier_name)
                if tier:
                    self.current_tier = tier
                    model = self.router.get_model(tier)
                    self.ui.success(f"Switched to {tier.value} tier ({model.name})")
                else:
                    self.ui.error(f"Unknown tier: {tier_name}")
                    self.ui.info("Available tiers: fast, balanced, powerful, ultra, uncensored")
            else:
                self.ui.info("Usage: /tier <name>")
                self.ui.info("Available: fast, balanced, powerful, ultra, uncensored")

        elif target == 'quit':
            self.running = False

        elif target == 'clear_context':
            self.conversation_history = []
            self.context = {}
            self.ui.success("Context cleared")

        elif target == 'show_models':
            models = self.router.list_models()
            self.ui.models_list(models)

        elif target == 'save_note':
            if args:
                self._save_conversation_note(args)
            else:
                self.ui.info("Usage: /save <title>")

        elif target == 'search_notes':
            if args:
                self._search_notes(args)
            else:
                self.ui.info("Usage: /search <query>")

        elif target == 'web_search_health':
            self._handle_web_search_health()

        else:
            self.ui.warning(f"Unknown command: {intent.original_prompt}")

    def _handle_greeting(self, user_input: str):
        """Handle simple greetings without AI query"""
        greetings = {
            'hello': 'Hello! How can I help you today?',
            'hi': 'Hi there! What can I do for you?',
            'hey': 'Hey! Ready to help.',
            'howdy': 'Howdy! What do you need?',
            'greetings': 'Greetings! How may I assist you?',
            'sup': "What's up! Ask me anything.",
        }

        cleaned = user_input.lower().strip().rstrip('!.,?')
        response = greetings.get(cleaned, "Hello! How can I help?")
        self.ui.assistant_message(response)

    def _handle_chat(self, user_input: str, intent: ClassifiedIntent):
        """Handle general chat"""
        self.ui.thinking()

        model = self.router.get_model(self.current_tier, intent.intent_type.value)
        context = self._build_context()

        response = self.ollama.generate(
            prompt=user_input,
            model=model.name,
            system=self._get_system_prompt(intent),
            max_tokens=model.max_tokens,
            context=context
        )

        self.ui.clear_thinking()

        if response.error:
            self.ui.error(response.error)
        else:
            formatted = self.ui.format_response(response.response)
            self.ui.assistant_message(formatted, model.name)

            self.conversation_history.append({
                "role": "assistant",
                "content": response.response
            })

    def _handle_file_ops(self, user_input: str, intent: ClassifiedIntent):
        """Handle file operations"""
        target = intent.target or user_input

        # Try to find the file first
        result = self.tools.execute_tool('find_file', {'query': target})

        if result.success:
            file_path = result.output
            self.ui.file_path(file_path, exists=True)

            # Ask if user wants to open it
            if self.ui.confirm("Open in editor?", default=True):
                import os
                import subprocess
                import shlex

                editor = os.environ.get('EDITOR', 'nvim')

                # Validate file_path is a safe path (no shell metacharacters)
                # Use subprocess with list args to prevent injection
                try:
                    # Use subprocess.run with list of arguments to prevent command injection
                    subprocess.run([editor, file_path], check=False)
                except FileNotFoundError:
                    self.ui.error(f"Editor '{editor}' not found")
                except Exception as e:
                    self.ui.error(f"Failed to open file: {e}")
        else:
            # Couldn't find directly, ask AI for help
            self.ui.info("File not found directly, asking AI...")
            self._handle_chat(f"find the file for: {target}", intent)

    def _handle_code_task(self, user_input: str, intent: ClassifiedIntent):
        """Handle code editing tasks with agentic workflow"""
        self.ui.status(Emoji.PLAN, "Planning approach...", Color.PURPLE)

        model = self.router.get_model(self.current_tier or ModelTier.BALANCED, intent.intent_type.value)

        # Generate plan
        plan_prompt = f"""Task: {user_input}

Create a numbered step-by-step plan (3-7 steps) to accomplish this task.
Be specific about which files to examine and what changes to make.
Format: Return ONLY a JSON array of step descriptions."""

        plan_response = self.ollama.generate(
            prompt=plan_prompt,
            model=model.name,
            system="You are a coding assistant. Create concise, actionable plans. Return only JSON arrays.",
            max_tokens=500
        )

        if plan_response.error:
            self.ui.error(f"Failed to generate plan: {plan_response.error}")
            return

        # Parse plan
        try:
            import re
            json_match = re.search(r'\[.*\]', plan_response.response, re.DOTALL)
            if json_match:
                steps = json.loads(json_match.group())
            else:
                steps = [plan_response.response]
        except json.JSONDecodeError:
            steps = [plan_response.response]

        # Show plan
        self.ui.plan(steps if isinstance(steps, list) else [str(steps)])

        # Ask for confirmation
        if not self.ui.confirm("Execute this plan?", default=True):
            self.ui.info("Plan cancelled")
            return

        # Execute steps
        changes = []
        for i, step in enumerate(steps if isinstance(steps, list) else [steps], 1):
            self.ui.step(Emoji.RUNNING, f"Step {i}: {step}")

            # Execute step (simplified for now - full implementation would parse tool calls)
            step_prompt = f"""Execute this step: {step}

Context from previous steps: {changes}

If you need to modify a file, show the exact changes.
If you need to run a command, show the command."""

            step_response = self.ollama.generate(
                prompt=step_prompt,
                model=model.name,
                system="You are a coding assistant executing a plan step. Be precise and show exact changes.",
                max_tokens=2000
            )

            if step_response.error:
                self.ui.error(f"Step failed: {step_response.error}")
                continue

            # Show result
            formatted = self.ui.format_response(step_response.response)
            print(f"    {formatted}")
            changes.append(f"Step {i}: {step}")

        # Summary
        self.ui.summary(changes)

    def _handle_web_research(self, user_input: str, intent: ClassifiedIntent):
        """Handle web research with privacy-first SearxNG"""
        query = intent.target or user_input

        self.ui.status(Emoji.BROWSE, f"Searching: {query}", Color.CYAN)

        result = self.tools.execute_tool('web_search', {
            'query': query,
            'num_results': 5
        })

        if result.success and result.output:
            results = result.output
            # Show search source for transparency
            source = result.metadata.get('source', 'web')
            count = result.metadata.get('count', len(results))
            print()
            print(f"  {Color.PURPLE}🌐 {source} search: '{query}' ({count} results){Color.RESET}")
            print()
            
            for i, r in enumerate(results[:5], 1):
                print(f"  {Color.YELLOW_BOLD}[{i}]{Color.RESET} {r['title']}")
                print(f"      {Color.CYAN}{r['url']}{Color.RESET}")
                if r.get('snippet'):
                    print(f"      {Color.GRAY}{r['snippet'][:100]}...{Color.RESET}")
                print()

            # Offer to scrape
            choice = self.ui.select("Scrape a result for more details?",
                                    [r['title'][:50] for r in results[:5]] + ["Skip"])

            if choice is not None and choice < len(results):
                url = results[choice]['url']
                self.ui.status(Emoji.BROWSE, f"Scraping: {url}", Color.CYAN)

                scrape_result = self.tools.execute_tool('scrape_page', {
                    'url': url,
                    'extract_links': False
                })

                if scrape_result.success:
                    domain = scrape_result.output.get('domain', 'unknown')
                    text = scrape_result.output.get('text', '')[:2000]
                    
                    print(f"\n  {Color.PURPLE}📄 Scraped from {domain} (BeautifulSoup local parsing){Color.RESET}\n")

                    # Summarize with AI
                    model = self.router.get_model(ModelTier.FAST)
                    summary = self.ollama.generate(
                        prompt=f"Summarize this content in 2-3 paragraphs:\n\n{text}",
                        model=model.name,
                        max_tokens=500
                    )

                    if not summary.error:
                        self.ui.assistant_message(summary.response)
                else:
                    self.ui.error(f"Scraping failed: {scrape_result.error}")
        else:
            self.ui.error(f"Search failed: {result.error}")

    def _handle_web_search_health(self):
        """Handle /webtest command - check web search health"""
        print()
        self.ui.divider()
        print(f"  {Color.PURPLE_BOLD}Web Search Health Check{Color.RESET}")
        self.ui.divider()
        
        result = self.tools.execute_tool('web_search_health', {})
        
        if result.success:
            health = result.output
            overall = result.metadata.get('overall_status', 'unknown')
            
            # BeautifulSoup status
            bs_status = health.get('beautifulsoup', {})
            bs_color = Color.GREEN if bs_status.get('status') == 'healthy' else Color.RED
            print(f"  BeautifulSoup: {bs_color}{bs_status.get('status', 'unknown')}{Color.RESET}")
            if bs_status.get('message'):
                print(f"    {Color.GRAY}{bs_status['message']}{Color.RESET}")
            
            # SearxNG config status
            searxng_config = health.get('searxng_config', {})
            config_status = searxng_config.get('status', 'unknown')
            config_color = Color.GREEN if config_status == 'healthy' else (Color.YELLOW if config_status == 'not_configured' else Color.RED)
            print(f"  SearxNG Config: {config_color}{config_status}{Color.RESET}")
            if searxng_config.get('url'):
                print(f"    URL: {Color.CYAN}{searxng_config['url']}{Color.RESET}")
                print(f"    Timeout: {searxng_config.get('timeout', 10)}s, Max results: {searxng_config.get('max_results', 5)}")
                print(f"    DuckDuckGo fallback: {'enabled' if searxng_config.get('fallback_enabled') else 'disabled'}")
            elif searxng_config.get('message'):
                print(f"    {Color.GRAY}{searxng_config['message']}{Color.RESET}")
            
            # SearxNG connection status
            searxng_conn = health.get('searxng_connection', {})
            conn_status = searxng_conn.get('status', 'unknown')
            conn_color = Color.GREEN if conn_status == 'healthy' else (Color.YELLOW if conn_status in ['skipped', 'warning'] else Color.RED)
            print(f"  SearxNG Connection: {conn_color}{conn_status}{Color.RESET}")
            if searxng_conn.get('message'):
                print(f"    {Color.GRAY}{searxng_conn['message']}{Color.RESET}")
            
            # Overall status
            overall_color = Color.GREEN if overall == 'healthy' else (Color.YELLOW if overall == 'degraded' else Color.RED)
            print()
            print(f"  Overall: {overall_color}{overall.upper()}{Color.RESET}")
            
            if overall != 'healthy':
                print()
                print(f"  {Color.YELLOW}To enable web search:{Color.RESET}")
                print(f"    1. Start SearxNG: docker run -d -p 8080:8080 searxng/searxng")
                print(f"    2. Set URL: export SEARXNG_URL=http://localhost:8080")
                print(f"    3. Or edit: configs/ryx_config.json → search.searxng_url")
        else:
            self.ui.error(f"Health check failed: {result.error}")
        
        self.ui.divider()
        print()

    def _handle_system_task(self, user_input: str, intent: ClassifiedIntent):
        """Handle system tasks"""
        target = intent.target

        if 'health' in user_input.lower() or 'check' in user_input.lower():
            result = self.tools.execute_tool('health_check', {})
            if result.success:
                self._display_health(result.output)
            else:
                self.ui.error(f"Health check failed: {result.error}")

        elif 'cleanup' in user_input.lower() or 'clean' in user_input.lower():
            if self.ui.confirm("Run cleanup?", default=True):
                result = self.tools.execute_tool('cleanup_cache', {'aggressive': False})
                if result.success:
                    self.ui.success(result.output)
                else:
                    self.ui.error(f"Cleanup failed: {result.error}")

        elif 'log' in user_input.lower():
            result = self.tools.execute_tool('view_logs', {'lines': 20})
            if result.success:
                print(f"\n{Color.GRAY}{result.output}{Color.RESET}\n")
            else:
                self.ui.error(f"Failed to view logs: {result.error}")

        else:
            # Generic system task - let AI handle
            self._handle_chat(user_input, intent)

    def _handle_rag(self, user_input: str, intent: ClassifiedIntent):
        """Handle RAG/knowledge operations"""
        if 'save' in user_input.lower():
            self.ui.info("Use /save <title> to save current conversation as a note")
        elif 'search' in user_input.lower():
            query = intent.target or user_input.replace('search', '').strip()
            self._search_notes(query)
        else:
            self._handle_chat(user_input, intent)

    def _handle_personal_chat(self, user_input: str, intent: ClassifiedIntent):
        """Handle personal/uncensored chat"""
        self.ui.thinking()

        # Force uncensored tier
        model = self.router.get_model(ModelTier.UNCENSORED)

        self.ui.warning("Using uncensored model. Content may be unfiltered.")

        response = self.ollama.generate(
            prompt=user_input,
            model=model.name,
            system="You are a helpful assistant for personal conversations. Be honest and direct.",
            max_tokens=model.max_tokens
        )

        self.ui.clear_thinking()

        if response.error:
            self.ui.error(response.error)
        else:
            formatted = self.ui.format_response(response.response)
            self.ui.assistant_message(formatted, model.name)

    def _show_status(self):
        """Show current status"""
        print()
        self.ui.divider()
        print(f"  {Color.PURPLE_BOLD}Status{Color.RESET}")
        self.ui.divider()

        # Tier
        tier = self.current_tier or ModelTier.BALANCED
        model = self.router.get_model(tier)
        print(f"  Tier: {Color.CYAN}{tier.value}{Color.RESET} ({model.name})")

        # Conversation
        print(f"  Messages: {Color.CYAN}{len(self.conversation_history)}{Color.RESET}")

        # Safety
        print(f"  Safety: {Color.CYAN}{self.safety_mode}{Color.RESET}")

        # Ollama
        health = self.ollama.health_check()
        status_color = Color.GREEN if health['status'] == 'healthy' else Color.RED
        print(f"  Ollama: {status_color}{health['status']}{Color.RESET}")

        self.ui.divider()
        print()

    def _display_health(self, health: Dict):
        """Display health check results"""
        print()
        self.ui.divider()
        print(f"  {Color.PURPLE_BOLD}System Health{Color.RESET}")
        self.ui.divider()

        for component, status in health.items():
            if isinstance(status, dict):
                status_str = status.get('status', 'unknown')
                color = Color.GREEN if status_str == 'healthy' else Color.RED
                print(f"  {component}: {color}{status_str}{Color.RESET}")
            else:
                print(f"  {component}: {status}")

        self.ui.divider()
        print()

    def _save_conversation_note(self, title: str):
        """Save conversation as a note"""
        if not self.conversation_history:
            self.ui.warning("No conversation to save")
            return

        content = "\n\n".join([
            f"**{msg['role'].title()}**: {msg['content']}"
            for msg in self.conversation_history
        ])

        result = self.tools.execute_tool('save_note', {
            'title': title,
            'content': content,
            'tags': ['conversation', 'ryx']
        })

        if result.success:
            self.ui.success(f"Saved: {result.output}")
        else:
            self.ui.error(f"Failed to save: {result.error}")

    def _search_notes(self, query: str):
        """Search notes"""
        result = self.tools.execute_tool('search_notes', {'query': query})

        if result.success and result.output:
            notes = result.output
            print()
            for note in notes[:10]:
                print(f"  {Color.PURPLE_BOLD}{note['title']}{Color.RESET}")
                print(f"    {Color.GRAY}{note['preview'][:100]}...{Color.RESET}")
                print()
        elif result.success:
            self.ui.info("No notes found")
        else:
            self.ui.error(f"Search failed: {result.error}")

    def _build_context(self) -> Optional[list]:
        """Build context from conversation history"""
        # For now, return None (let Ollama handle context)
        # Could be extended to build proper context
        return None

    def _get_system_prompt(self, intent: ClassifiedIntent) -> str:
        """Get system prompt based on intent"""
        base = """You are Ryx, a helpful AI assistant for Arch Linux.

RULES:
1. Be concise - answer in 1-3 paragraphs max
2. For file operations, give exact paths
3. For commands, show exact commands in code blocks
4. Don't explain what you're doing, just do it
5. Use the user's preferred editor (nvim by default)
"""

        if intent.intent_type in [IntentType.CODE_EDIT, IntentType.CONFIG_EDIT]:
            base += """
CODING RULES:
- Show exact code changes
- Use minimal diffs when possible
- Test your suggestions mentally before showing
"""

        return base

    def _is_greeting(self, text: str) -> bool:
        """Check if text is a simple greeting"""
        greetings = {'hello', 'hi', 'hey', 'howdy', 'greetings', 'sup'}
        cleaned = text.lower().strip().rstrip('!.,?')
        return cleaned in greetings


def main(args: Optional[List[str]] = None):
    """Main entry point"""
    safety_mode = "normal"

    if args:
        for arg in args:
            if arg.startswith('--safety='):
                safety_mode = arg.split('=')[1]
            elif arg == '--strict':
                safety_mode = 'strict'
            elif arg == '--loose':
                safety_mode = 'loose'

    session = SessionLoop(safety_mode=safety_mode)
    session.run()


if __name__ == "__main__":
    main(sys.argv[1:])
