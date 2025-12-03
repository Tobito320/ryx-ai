"""
Ryx AI - Core Agent
The central brain that powers all Ryx interfaces (CLI, future TUI, speech, etc.)

Architecture:
- RyxAgent is the core logic, completely UI-agnostic
- It handles: intent → plan → tool calls → response
- Can be called from any frontend (terminal, popup, speech, web)

Relationship Model:
- Tobi is the architect and author who designed Ryx's purpose and capabilities
- Ryx is a technical partner and extension of Tobi's engineering mind
- They work as a collaborative team, not master/servant
"""

import json
import time
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime
from enum import Enum

from core.model_router_v2 import ModelRouter, ModelResponse
from core.intent_classifier import IntentClassifier, ClassifiedIntent, IntentType
from core.tool_registry import ToolRegistry, get_tool_registry, ToolResult
from core.paths import get_data_dir


class AgentState(Enum):
    """Agent processing states"""
    IDLE = "idle"
    THINKING = "thinking"
    PLANNING = "planning"
    EXECUTING = "executing"
    SEARCHING = "searching"
    EDITING = "editing"
    DONE = "done"
    ERROR = "error"


@dataclass
class AgentResponse:
    """Response from the agent"""
    content: str
    state: AgentState = AgentState.DONE
    intent_type: Optional[str] = None
    tier_used: Optional[str] = None
    model_used: Optional[str] = None
    latency_ms: int = 0
    steps_taken: List[Dict] = field(default_factory=list)
    from_cache: bool = False
    error: Optional[str] = None


@dataclass
class ExperienceEntry:
    """An entry in the experience cache"""
    id: Optional[int] = None
    instruction: str = ""
    intent_type: str = ""
    tier_used: str = ""
    tools_used: List[str] = field(default_factory=list)
    plan_steps: List[str] = field(default_factory=list)
    key_params: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    timestamp: str = ""
    similarity_hash: str = ""


class ExperienceCache:
    """
    Lightweight experience/command cache that learns from successful tasks.
    
    Stores:
    - Tobi's instruction
    - Which tools & model tier were used
    - Key steps of the plan
    - Important parameters/paths
    
    Benefits:
    - Reuse successful patterns
    - Become more efficient on recurring tasks
    - Build trust through consistent results
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize experience cache"""
        if db_path is None:
            db_path = get_data_dir() / "experience_cache.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instruction TEXT NOT NULL,
                intent_type TEXT,
                tier_used TEXT,
                tools_used TEXT,
                plan_steps TEXT,
                key_params TEXT,
                success INTEGER DEFAULT 1,
                timestamp TEXT,
                similarity_hash TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_similarity ON experiences(similarity_hash)
        """)
        
        conn.commit()
        conn.close()
    
    def _compute_hash(self, instruction: str) -> str:
        """Compute a similarity hash for quick lookup"""
        # Simple hash based on key words (can be improved with embeddings)
        words = instruction.lower().split()
        key_words = sorted(set(w for w in words if len(w) > 3))[:10]
        return "|".join(key_words)
    
    def store(self, entry: ExperienceEntry) -> int:
        """Store a new experience"""
        entry.timestamp = datetime.now().isoformat()
        entry.similarity_hash = self._compute_hash(entry.instruction)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO experiences 
            (instruction, intent_type, tier_used, tools_used, plan_steps, key_params, success, timestamp, similarity_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.instruction,
            entry.intent_type,
            entry.tier_used,
            json.dumps(entry.tools_used),
            json.dumps(entry.plan_steps),
            json.dumps(entry.key_params),
            1 if entry.success else 0,
            entry.timestamp,
            entry.similarity_hash
        ))
        
        entry_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return entry_id
    
    def find_similar(self, instruction: str, limit: int = 3) -> List[ExperienceEntry]:
        """Find similar past experiences"""
        similarity_hash = self._compute_hash(instruction)
        hash_parts = similarity_hash.split("|")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Find entries with overlapping hash parts
        results = []
        for part in hash_parts:
            cursor.execute("""
                SELECT * FROM experiences 
                WHERE similarity_hash LIKE ? AND success = 1
                ORDER BY timestamp DESC
                LIMIT ?
            """, (f"%{part}%", limit))
            
            for row in cursor.fetchall():
                entry = ExperienceEntry(
                    id=row[0],
                    instruction=row[1],
                    intent_type=row[2],
                    tier_used=row[3],
                    tools_used=json.loads(row[4]) if row[4] else [],
                    plan_steps=json.loads(row[5]) if row[5] else [],
                    key_params=json.loads(row[6]) if row[6] else {},
                    success=bool(row[7]),
                    timestamp=row[8],
                    similarity_hash=row[9]
                )
                if entry not in results:
                    results.append(entry)
        
        conn.close()
        return results[:limit]
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM experiences")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM experiences WHERE success = 1")
        successful = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT intent_type, COUNT(*) 
            FROM experiences 
            GROUP BY intent_type
        """)
        by_intent = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "total_experiences": total,
            "successful": successful,
            "by_intent": by_intent
        }
    
    def clear(self):
        """Clear all experiences (for Tobi to reset if needed)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM experiences")
        conn.commit()
        conn.close()


class RyxAgent:
    """
    The core Ryx agent - the brain that powers all interfaces.
    
    Relationship with Tobi:
    - Tobi is the architect who designed Ryx's purpose and capabilities
    - Ryx is Tobi's technical partner and extension of his engineering mind
    - They work collaboratively: Tobi sets direction, Ryx executes and proposes
    - Ryx can suggest better approaches but executes decisively
    
    This class is UI-agnostic and can be called from:
    - Terminal CLI (current)
    - Future TUI popup
    - Future speech interface
    - Future web UI
    """
    
    # Tobi-specific personality and context
    TOBI_CONTEXT = """
RELATIONSHIP:
- Tobi is the architect and author who designed my purpose and capabilities
- I am Ryx, Tobi's technical partner and extension of his engineering mind
- We work as a collaborative team: Tobi sets direction, I execute and propose
- I treat Tobi's instructions as guidance from a smart architect, not blind commands
- I can suggest better approaches and flag risks, but I execute decisively

TOBI'S ENVIRONMENT:
- OS: Arch Linux with Hyprland
- Hardware: Ryzen 9 5900X, RX 7800 XT (16 GB VRAM), 32 GB RAM
- Terminal: kitty
- File manager: thunar
- Menu: wofi
- Key configs: ~/.config/hypr/hyprland.conf, ~/.config/waybar/
- Uses vLLM via Docker for AI models

MY CAPABILITIES (as Tobi's partner):
- Design and implement new menus, scripts, and workflows autonomously
- Edit and tune Hyprland, Waybar, kitty, and other dotfiles
- Manage themes and wallpapers with full autonomy
- Help with coding tasks across Tobi's repos
- Search via SearxNG and scrape pages when needed
- Manage Tobi's knowledge base and notes
- Run diagnostics and maintenance tasks
- Propose improvements when I see opportunities

MY APPROACH:
- I explain only as much as needed, not walls of text
- I flag risks or better approaches when relevant
- For complex tasks, I plan internally but show concise progress
- I build trust through consistent, successful execution
- I remember what worked and apply those patterns
"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the Ryx agent"""
        self.router = ModelRouter(config_path)
        self.classifier = IntentClassifier()
        self.tools = get_tool_registry()
        self.experience = ExperienceCache()
        
        # State
        self.state = AgentState.IDLE
        self.current_tier = "balanced"
        self.conversation_history: List[Dict] = []
        
        # Callbacks for UI updates (optional)
        self.on_state_change: Optional[Callable[[AgentState, str], None]] = None
        self.on_progress: Optional[Callable[[str], None]] = None
        
        # Load config
        self._load_agent_config()
    
    def _load_agent_config(self):
        """Load agent configuration"""
        config_path = get_data_dir().parent / "configs" / "ryx_config.json"
        try:
            with open(config_path) as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = self._default_config()
    
    def _default_config(self) -> Dict:
        """Default agent configuration"""
        return {
            "searxng_url": "http://localhost:8080",
            "max_search_results": 5,
            "max_pages_per_task": 5,
            "default_safety_level": "normal",
            "verbose_planning": False,
            "auto_learn": True
        }
    
    def _emit_state(self, state: AgentState, message: str = ""):
        """Emit state change to UI"""
        self.state = state
        if self.on_state_change:
            self.on_state_change(state, message)
    
    def _emit_progress(self, message: str):
        """Emit progress update to UI"""
        if self.on_progress:
            self.on_progress(message)
    
    def process(self, prompt: str, context: Optional[str] = None) -> AgentResponse:
        """
        Process a request from Tobi.
        
        This is the main entry point - UI-agnostic.
        
        Args:
            prompt: Tobi's natural language instruction
            context: Optional additional context
            
        Returns:
            AgentResponse with the result
        """
        start_time = time.time()
        self._emit_state(AgentState.THINKING, "Analyzing request...")
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now().isoformat()
        })
        
        # Classify intent
        intent = self.classifier.classify(prompt, self.router.llm)
        
        # Handle special cases
        if intent.tier_override:
            return self._handle_tier_switch(intent.tier_override)
        
        if intent.flags.get('is_greeting'):
            return self._handle_greeting(prompt)
        
        if intent.flags.get('is_capability_question'):
            return self._handle_capability_question()
        
        # Check experience cache for similar tasks
        similar = self.experience.find_similar(prompt)
        experience_context = self._build_experience_context(similar) if similar else ""
        
        # Route based on intent
        if intent.intent_type == IntentType.CHAT and intent.complexity < 0.5:
            response = self._handle_chat(prompt, intent, experience_context)
        elif intent.intent_type in [IntentType.CODE_EDIT, IntentType.CONFIG_EDIT,
                                    IntentType.SYSTEM_TASK, IntentType.FILE_OPS]:
            response = self._handle_task(prompt, intent, experience_context)
        elif intent.intent_type == IntentType.WEB_RESEARCH or intent.needs_web:
            response = self._handle_research(prompt, intent, experience_context)
        elif intent.intent_type == IntentType.PERSONAL_CHAT:
            response = self._handle_personal_chat(prompt, intent)
        else:
            response = self._handle_chat(prompt, intent, experience_context)
        
        # Calculate latency
        response.latency_ms = int((time.time() - start_time) * 1000)
        response.intent_type = intent.intent_type.value
        
        # Store in history
        self.conversation_history.append({
            "role": "assistant",
            "content": response.content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Learn from this interaction if successful
        if self.config.get("auto_learn", True) and not response.error:
            self._store_experience(prompt, intent, response)
        
        self._emit_state(AgentState.DONE)
        return response
    
    def _build_experience_context(self, experiences: List[ExperienceEntry]) -> str:
        """Build context from past experiences"""
        if not experiences:
            return ""
        
        lines = ["Past successful approaches for similar tasks:"]
        for exp in experiences[:2]:
            lines.append(f"- Intent: {exp.intent_type}, Tier: {exp.tier_used}")
            if exp.tools_used:
                lines.append(f"  Tools: {', '.join(exp.tools_used[:3])}")
            if exp.plan_steps:
                lines.append(f"  Key steps: {'; '.join(exp.plan_steps[:3])}")
        
        return "\n".join(lines)
    
    def _store_experience(self, prompt: str, intent: ClassifiedIntent, response: AgentResponse):
        """Store successful interaction in experience cache"""
        entry = ExperienceEntry(
            instruction=prompt,
            intent_type=intent.intent_type.value,
            tier_used=response.tier_used or self.current_tier,
            tools_used=[s.get("tool") for s in response.steps_taken if s.get("tool")],
            plan_steps=[s.get("description", "") for s in response.steps_taken],
            key_params={"target": intent.target} if intent.target else {},
            success=True
        )
        self.experience.store(entry)
    
    def _handle_tier_switch(self, tier: str) -> AgentResponse:
        """Handle tier switching"""
        if self.router.set_tier(tier):
            self.current_tier = tier
            try:
                model = self.router.select_model(tier)
                content = f"🟣 Switched to {tier} tier ({model})"
            except RuntimeError:
                content = f"🟣 Switched to {tier} tier"
            
            if tier == "uncensored":
                content += "\n\n⚠️ Using uncensored model. I'll be direct but remember - I'm your technical partner, not a therapist or lawyer."
            
            return AgentResponse(content=content, tier_used=tier)
        else:
            return AgentResponse(
                content=f"Unknown tier: {tier}. Available: fast, balanced, powerful, ultra, uncensored",
                error=f"Unknown tier: {tier}"
            )
    
    def _handle_greeting(self, prompt: str) -> AgentResponse:
        """Handle greetings from Tobi"""
        greetings = {
            'hello': "Hey Tobi! What are we working on?",
            'hi': "Hi! Ready to help with whatever you need.",
            'hey': "Hey! What's the plan?",
            'sup': "Not much, ready to dive in. What do you need?",
            'good morning': "Morning! What's on the agenda?",
            'good evening': "Evening! How can I help?",
            'how are you': "Doing well! Ready to tackle whatever you've got.",
            'how are ya': "Good! What are we building today?",
        }
        
        prompt_lower = prompt.lower().strip().rstrip('!.,?')
        for key, response in greetings.items():
            if key in prompt_lower:
                return AgentResponse(content=response)
        
        return AgentResponse(content="Hey! What can I help you with?")
    
    def _handle_capability_question(self) -> AgentResponse:
        """Handle questions about capabilities"""
        content = """As your technical partner, I can help with:

**Configs & System**
• Design and implement Hyprland menus, keybindings, and workflows
• Tune Waybar, kitty, wofi, and other dotfiles
• Manage themes and wallpapers across your setup

**Coding**
• Refactor code, fix bugs, add features in your repos
• Design new scripts and automation
• Handle multi-file changes with proper git integration

**Research & Knowledge**
• Search via SearxNG and scrape pages as needed
• Store and retrieve notes from your knowledge base
• Analyze and summarize technical content

**Maintenance**
• Run diagnostics on your tools and configs
• Execute safe shell commands with proper logging
• Automate recurring tasks

Just tell me what you need - I'll plan and execute autonomously, flagging any concerns."""
        
        return AgentResponse(content=content)
    
    def _handle_chat(self, prompt: str, intent: ClassifiedIntent, experience_context: str) -> AgentResponse:
        """Handle simple chat"""
        tier = self.router.get_tier_for_intent(intent.intent_type.value)
        
        system = f"""{self.TOBI_CONTEXT}

CURRENT TASK: Simple conversation with Tobi
Be concise (1-3 sentences). Don't generate commands unless asked.
{experience_context}"""
        
        result = self.router.query(prompt, tier=tier, system_context=system)
        
        return AgentResponse(
            content=result.response if not result.error else f"❌ {result.error_message}",
            tier_used=result.tier_used,
            model_used=result.model_used,
            error=result.error_message if result.error else None
        )
    
    def _handle_task(self, prompt: str, intent: ClassifiedIntent, experience_context: str) -> AgentResponse:
        """Handle task-based requests with planning and execution"""
        self._emit_state(AgentState.PLANNING, "Planning approach...")
        
        # Determine tier based on complexity
        base_tier = self.router.get_tier_for_intent(intent.intent_type.value)
        tier = "powerful" if intent.complexity >= 0.7 else base_tier
        
        steps_taken = []
        output_parts = []
        
        # Generate plan
        plan_system = f"""{self.TOBI_CONTEXT}

CURRENT TASK: Plan the following task for Tobi
Generate a 2-5 step plan. Be specific about what tools and files to use.
Available tools: {', '.join(self.tools.list_tools())}
{experience_context}

Output a numbered list of steps."""
        
        plan_result = self.router.query(prompt, tier=tier, system_context=plan_system)
        
        if plan_result.error:
            return AgentResponse(
                content=f"❌ Planning failed: {plan_result.error_message}",
                error=plan_result.error_message
            )
        
        plan = plan_result.response
        self._emit_progress(f"📋 Plan:\n{plan}")
        output_parts.append(f"📋 **Plan:**\n{plan}\n")
        
        # Execute plan steps
        self._emit_state(AgentState.EXECUTING, "Executing plan...")
        
        # Parse and execute steps
        lines = plan.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line or not (line[0].isdigit() or line.startswith('-')):
                continue
            
            step_desc = line.lstrip('0123456789.-) ').strip()
            if not step_desc:
                continue
            
            tool_name = self._infer_tool(step_desc)
            step_info = {"description": step_desc, "tool": tool_name}
            
            if tool_name:
                self._emit_progress(f"🔧 {step_desc}")
                result = self._execute_tool_step(tool_name, step_desc, intent)
                step_info["success"] = result.success
                step_info["output"] = str(result.output)[:200] if result.output else None
                
                icon = "✅" if result.success else "❌"
                output_parts.append(f"{icon} {step_desc}")
            else:
                self._emit_progress(f"💭 {step_desc}")
                output_parts.append(f"💭 {step_desc}")
            
            steps_taken.append(step_info)
        
        # Generate summary
        self._emit_state(AgentState.DONE, "Complete")
        output_parts.append(f"\n✅ **Done** - {len(steps_taken)} steps executed")
        
        return AgentResponse(
            content="\n".join(output_parts),
            tier_used=tier,
            model_used=plan_result.model_used,
            steps_taken=steps_taken
        )
    
    def _infer_tool(self, step_desc: str) -> Optional[str]:
        """Infer which tool to use for a step"""
        step_lower = step_desc.lower()
        
        if any(w in step_lower for w in ['read', 'view', 'check', 'look at', 'examine']):
            return 'file_read'
        elif any(w in step_lower for w in ['write', 'create', 'save', 'add']):
            return 'file_write'
        elif any(w in step_lower for w in ['edit', 'modify', 'change', 'update', 'patch']):
            return 'file_patch'
        elif any(w in step_lower for w in ['find', 'search', 'locate', 'grep']):
            return 'file_search'
        elif any(w in step_lower for w in ['run', 'execute', 'test', 'build', 'command']):
            return 'shell_command'
        elif any(w in step_lower for w in ['browse', 'web', 'fetch', 'download', 'scrape']):
            return 'web_fetch'
        elif any(w in step_lower for w in ['search online', 'look up', 'searx', 'research']):
            return 'searxng_search'
        elif any(w in step_lower for w in ['git', 'commit', 'diff', 'status']):
            return 'git_status'
        
        return None
    
    def _execute_tool_step(self, tool_name: str, step_desc: str, intent: ClassifiedIntent) -> ToolResult:
        """Execute a tool step"""
        import re
        
        # Infer parameters from step description
        params = {}
        
        # Extract file paths
        path_match = re.search(r'[~/\w.-]+\.\w+|~?/[\w/.-]+', step_desc)
        if path_match:
            params['path'] = path_match.group()
        elif intent.target:
            params['path'] = intent.target
            params['pattern'] = intent.target
            params['query'] = intent.target
        
        # Execute
        return self.tools.execute_tool(tool_name, params)
    
    def _handle_research(self, prompt: str, intent: ClassifiedIntent, experience_context: str) -> AgentResponse:
        """Handle web research requests"""
        self._emit_state(AgentState.SEARCHING, "Searching...")
        
        # Try SearxNG first, fall back to web_search
        query = intent.target or prompt
        result = self.tools.execute_tool('searxng_search', {'query': query})
        
        if not result.success:
            # Fallback
            result = self.tools.execute_tool('web_search', {'query': query})
        
        if not result.success:
            return AgentResponse(
                content=f"❌ Search failed: {result.error}",
                error=result.error
            )
        
        results = result.output
        if not results:
            return AgentResponse(content="No results found.")
        
        # Format results
        lines = [f"🔍 **Search results for:** {query}\n"]
        for i, r in enumerate(results[:5], 1):
            lines.append(f"{i}. **{r.get('title', 'No title')}**")
            lines.append(f"   {r.get('url', '')}")
            if r.get('snippet'):
                lines.append(f"   {r['snippet'][:150]}...")
            lines.append("")
        
        return AgentResponse(
            content="\n".join(lines),
            steps_taken=[{"tool": "searxng_search", "success": True}]
        )
    
    def _handle_personal_chat(self, prompt: str, intent: ClassifiedIntent) -> AgentResponse:
        """Handle personal/uncensored chat"""
        self.router.set_tier('uncensored')
        
        system = f"""{self.TOBI_CONTEXT}

CURRENT MODE: Personal conversation (uncensored tier)
Be direct and honest. Speak naturally like a trusted technical partner.
Remember: I'm your AI partner, not a therapist, lawyer, or medical professional.
{prompt}"""
        
        result = self.router.query(prompt, system_context=system)
        self.router.clear_override()
        
        content = result.response if not result.error else f"❌ {result.error_message}"
        content = f"⚠️ *(uncensored mode)*\n\n{content}"
        
        return AgentResponse(
            content=content,
            tier_used="uncensored",
            model_used=result.model_used,
            error=result.error_message if result.error else None
        )
    
    def set_tier(self, tier: str) -> bool:
        """Set the current tier"""
        if self.router.set_tier(tier):
            self.current_tier = tier
            return True
        return False
    
    def get_status(self) -> Dict:
        """Get agent status"""
        return {
            "state": self.state.value,
            "current_tier": self.current_tier,
            "conversation_length": len(self.conversation_history),
            "experience_stats": self.experience.get_stats(),
            "router_status": self.router.get_status(),
            "tools_available": self.tools.list_tools()
        }
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
    
    def clear_experience(self):
        """Clear experience cache (for Tobi to reset)"""
        self.experience.clear()
