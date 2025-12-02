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
from core.memory import get_memory, RyxMemory


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
    - Advanced memory system (episodic + persistent + RAG)
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

        # Advanced memory system
        self.memory = get_memory()

        # Session state
        self.running = True
        self.current_tier: Optional[ModelTier] = None
        self.conversation_history: List[Dict[str, str]] = []
        self.context: Dict[str, Any] = {}
        self.safety_mode = safety_mode

        # Session file for persistence
        self.session_file = get_data_dir() / "session_state.json"

        # Initialize RyxAgent for UI-agnostic processing
        # This provides access to core agent functionality including tier management
        from core.ryx_agent import RyxAgent
        self.agent = RyxAgent()

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
        """Restore previous session if exists (silent by default)"""
        if not self.session_file.exists():
            return

        try:
            with open(self.session_file, 'r') as f:
                state = json.load(f)

            # Only restore last 10 messages to avoid bloat
            history = state.get('conversation_history', [])
            self.conversation_history = history[-10:] if len(history) > 10 else history

            tier_value = state.get('current_tier')
            if tier_value:
                self.current_tier = ModelTier(tier_value)

            self.context = state.get('context', {})

            # Silent restore - no verbose message

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
        """Handle simple greetings without AI query - instant response"""
        greetings = {
            'hello': 'Hello! How can I help?',
            'hi': 'Hi! What do you need?',
            'hey': 'Hey! Ready.',
            'howdy': 'Howdy!',
            'greetings': 'Greetings!',
            'sup': "What's up!",
            'whatsup': "Not much, what do you need?",
            'whats up': "Not much, what do you need?",
            "what's up": "Not much, what do you need?",
            'yo': 'Yo! What can I do?',
            'hola': 'Hola!',
            'hallo': 'Hallo!',
        }

        cleaned = user_input.lower().strip().rstrip('!.,?').replace("'", "")
        response = greetings.get(cleaned, "Hey! What do you need?")
        self.ui.assistant_message(response)

    def _handle_chat(self, user_input: str, intent: ClassifiedIntent):
        """Handle general chat with memory-augmented context"""
        self.ui.thinking()

        # Smart model selection based on query complexity
        model = self.router.select_model_for_query(user_input)
        
        # Get memory-augmented context
        memory_context = self.memory.get_context_for_query(user_input)
        context = self._build_context()
        
        # Build enhanced system prompt with memory
        system_prompt = self._get_system_prompt(intent)
        
        # Add relevant memories to context
        if memory_context["relevant_memories"]:
            memory_str = "\n".join([
                f"- {m['content']}" for m in memory_context["relevant_memories"]
            ])
            system_prompt += f"\n\nRelevant context from memory:\n{memory_str}"
        
        # Add user preferences
        prefs = memory_context["user_preferences"]
        if prefs.get("prefers_action"):
            system_prompt += "\n\nIMPORTANT: User prefers you to DO things, not explain how. Take action directly."

        response = self.ollama.generate(
            prompt=user_input,
            model=model.name,
            system=system_prompt,
            max_tokens=model.max_tokens,  # Use model's configured max_tokens
            temperature=0.1,  # Lower temperature for more focused responses
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
            
            # Learn from this interaction
            self.memory.learn_from_interaction(user_input, response.response, success=True)

    def _handle_file_ops(self, user_input: str, intent: ClassifiedIntent):
        """Handle file operations - FAST, no confirmation needed"""
        target = intent.target or user_input

        # Try to find the file first
        result = self.tools.execute_tool('find_file', {'query': target})

        if result.success:
            file_path = result.output
            self.ui.file_path(file_path, exists=True)

            # Open directly - no confirmation (user asked for it)
            import os
            import subprocess

            editor = os.environ.get('EDITOR', 'nvim')
            try:
                subprocess.run([editor, file_path], check=False)
            except FileNotFoundError:
                self.ui.error(f"Editor '{editor}' not found")
            except Exception as e:
                self.ui.error(f"Failed to open: {e}")
        else:
            # Just give the path directly
            self.ui.info(f"~/.config/hypr/hyprland.conf")
            self.ui.info("Run: nvim ~/.config/hypr/hyprland.conf")

    def _handle_code_task(self, user_input: str, intent: ClassifiedIntent):
        """Handle code editing tasks - just use fast chat"""
        self._handle_chat(user_input, intent)

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
        """Get system prompt based on intent - CONCISE and ACTION-ORIENTED"""
        base = """You are Ryx. Be EXTREMELY brief.

RULES:
1. MAX 1-2 sentences
2. NO filler, NO explanations
3. Direct answers only
4. Commands only when asked

Examples:
Q: "What time is it?" A: "Run: date"
Q: "What is Python?" A: "A programming language."
Q: "Open config" A: "nvim ~/.config/hypr/hyprland.conf"
"""

        if intent.intent_type in [IntentType.CODE_EDIT, IntentType.CONFIG_EDIT]:
            base += "\nCode: Show ONLY changed lines."

        return base

    def _is_greeting(self, text: str) -> bool:
        """Check if text is a simple greeting"""
        greetings = {'hello', 'hi', 'hey', 'howdy', 'greetings', 'sup', 'yo', 'hola', 'hallo',
                     'whatsup', 'whats up', "what's up"}
        cleaned = text.lower().strip().rstrip('!.,?').replace("'", "")
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
