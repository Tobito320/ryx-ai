"""
Ryx AI - LLM-based Intent Classifier
Production-grade intent classification using minimal rules + LLM fallback
"""

import re
import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class IntentType(Enum):
    """Intent types for Ryx AI"""
    CHAT = "chat"  # Short Q&A, brainstorming
    CODE_EDIT = "code_edit"  # Refactor, add features, fix bugs, write tests
    CONFIG_EDIT = "config_edit"  # System configs (Hyprland, Waybar, shell)
    FILE_OPS = "file_ops"  # Find/open/create/move files
    WEB_RESEARCH = "web_research"  # Search web, scrape pages
    SYSTEM_TASK = "system_task"  # Run tests, diagnostics, cleanup
    KNOWLEDGE_RAG = "knowledge_rag"  # Save/search notes
    PERSONAL_CHAT = "personal_chat"  # Uncensored personal conversation


@dataclass
class ClassifiedIntent:
    """Result of intent classification"""
    intent_type: IntentType
    confidence: float  # 0.0 - 1.0
    target: Optional[str] = None  # What to act on
    flags: Dict[str, Any] = field(default_factory=dict)
    original_prompt: str = ""
    tier_override: Optional[str] = None  # User requested tier
    needs_web: bool = False  # Whether web research is needed
    needs_confirmation: bool = False  # Whether action needs user confirmation


class IntentClassifier:
    """
    LLM-based intent classifier with minimal rule layer

    Strategy:
    1. Fast rule-based classification for obvious cases (speed optimization)
    2. LLM-based classification for ambiguous cases
    3. Returns structured intent with confidence score

    NO giant keyword tables - uses semantic understanding instead.
    """

    # Minimal rule patterns for obvious cases (fast path)
    # NOTE: Order matters! More specific patterns (CONFIG_EDIT) must come before general ones (FILE_OPS)
    OBVIOUS_PATTERNS = {
        # Config editing - specific config mentions (MUST be checked before FILE_OPS)
        # Extended to cover: "edit my X config", "update X settings", "change X configuration"
        IntentType.CONFIG_EDIT: [
            r'(hyprland|waybar|kitty|nvim|zsh|bash)\s*(config|settings?)',
            r'(edit|update|change|modify)\s+(my\s+)?(hyprland|waybar|kitty|nvim|zsh|bash)',
            r'~/.config/',
        ],
        # File operations - very clear verbs
        # Extended to cover: open, edit, show, find, locate, create, move, copy, delete file(s)
        IntentType.FILE_OPS: [
            r'^(open|edit|show|find|where is|locate)\s+',
            r'^(create|touch|make|new)\s+(file|folder|directory)',
            r'^(move|copy|delete|remove)\s+(file|folder)',
            r'\.conf$|\.yaml$|\.json$|\.toml$|config\s*$',
        ],
        # Code editing - obvious code-related verbs
        IntentType.CODE_EDIT: [
            r'^(refactor|debug|implement|fix bug|write test|add test)',
            r'(function|class|method|module)\s+(to|that|which)',
        ],
        # System tasks - obvious system verbs
        # Extended to cover: build, test, compile, lint, format
        IntentType.SYSTEM_TASK: [
            r'^(run tests?|check|diagnose|cleanup|optimize)',
            r'^(install|update|remove|uninstall)\s+',
            r'^build\s+(the\s+)?project',
            r'^(build|compile|lint|format)\s+',
        ],
        # Web research - explicit research requests
        # NOTE: "what is X" is still handled as CHAT unless combined with search keywords
        IntentType.WEB_RESEARCH: [
            r'^search\s+(the\s+)?web\s+for\s+',
            r'^search\s+for\s+',  # "search for X" triggers web research
            r'^(look\s+up|research|google|browse)\s+',
            r'^(find|search)\s+(information|info|articles?|docs?)\s+(about|on|for)',
            r'^scrape\s+(this\s+)?(url|page|site|website)',
            r'search\s+online\s+for',
            r'searxng\s+search',
        ],
    }
    
    # Conversational patterns that should NEVER trigger web search
    # These are questions directed at the AI itself
    CONVERSATIONAL_PATTERNS = [
        # Questions about the AI
        r"^(what('s| is)?\s+)?your\s+name",
        r"^who\s+are\s+you",
        r"^(what|how)\s+(are|can)\s+you",
        r"^(can|could|would)\s+you\s+",
        r"^(tell|talk)\s+(me\s+)?(about\s+)?yourself",
        r"^what('s| is)?\s+your\s+(purpose|job|role|function)",
        # Greetings and social
        r"^(how\s+are\s+you|how('s| is)\s+it\s+going)",
        r"^(good\s+)?(morning|afternoon|evening|night)",
        r"^(thanks?|thank\s+you)",
        r"^(hi|hello|hey|howdy|sup)\b",
        # Simple yes/no / opinion
        r"^(yes|no|okay|ok|sure|maybe|perhaps)\b",
        r"^(i\s+think|i\s+believe|in\s+my\s+opinion)",
        # Help requests about the tool
        r"^(how\s+do\s+i|how\s+can\s+i|how\s+to)\s+use\s+(you|this|ryx)",
        r"^(what\s+can\s+you\s+do|what\s+are\s+your\s+capabilities)",
        # Generic what/who that are likely conversational
        r"^what\s+do\s+you\s+(think|know|mean)",
        r"^what('s| is)\s+(up|happening|new)",
    ]

    # Time-sensitive patterns that require current information from the web
    # These should trigger web search even if not explicitly asking to "search"
    TIME_SENSITIVE_PATTERNS = [
        r'\b(current|currently)\b',
        r'\b(latest|recent|recently)\b',
        r'\b(today|now|right now)\b',
        r'\bas of\s+(today|now|\d{4})',
        r'\b(this|last)\s+(week|month|year|quarter)\b',
        r'\b(20(2[4-9]|[3-9]\d))\b',  # Years 2024-2099
        r'\bwhat\s+(is|are)\s+the\s+(current|latest)',
        r'\bwho\s+(is|are)\s+the\s+current\b',
    ]

    # Slash command mappings
    SLASH_COMMANDS = {
        '/help': 'show_help',
        '/status': 'show_status',
        '/tier': 'set_tier',
        '/quit': 'quit',
        '/exit': 'quit',
        '/q': 'quit',
        '/clear': 'clear_context',
        '/save': 'save_note',
        '/search': 'search_notes',
        '/models': 'show_models',
        '/webtest': 'web_search_health',
    }

    # Tier keywords for user tier override detection
    TIER_KEYWORDS = {
        'fast': 'fast',
        'quick': 'fast',
        'small': 'fast',
        'balanced': 'balanced',
        'default': 'balanced',
        'powerful': 'powerful',
        'strong': 'powerful',
        'big': 'powerful',
        'ultra': 'ultra',
        'heavy': 'ultra',
        '30b': 'ultra',
        'uncensored': 'uncensored',
        'abliterated': 'uncensored',
        'personal': 'uncensored',
    }

    def __init__(self, llm_client=None):
        """
        Initialize intent classifier

        Args:
            llm_client: Optional vLLM client for LLM-based classification
        """
        self.llm_client = llm_client

    def classify(self, prompt: str, context: Optional[Dict] = None) -> ClassifiedIntent:
        """
        Classify user intent from prompt

        Args:
            prompt: User's natural language prompt
            context: Optional context (conversation history, current file, etc.)

        Returns:
            ClassifiedIntent with type, confidence, and metadata
        """
        prompt = prompt.strip()

        # Handle empty prompt
        if not prompt:
            return ClassifiedIntent(
                intent_type=IntentType.CHAT,
                confidence=1.0,
                original_prompt=prompt
            )

        # Handle slash commands
        if prompt.startswith('/'):
            return self._handle_slash_command(prompt)

        # Check for tier override request
        tier_override = self._detect_tier_override(prompt)

        # Check for simple greetings FIRST (fast path, sets is_greeting flag)
        if self._is_greeting(prompt):
            return ClassifiedIntent(
                intent_type=IntentType.CHAT,
                confidence=1.0,
                original_prompt=prompt,
                tier_override=tier_override,
                flags={'is_greeting': True}
            )

        # IMPORTANT: Check for conversational patterns BEFORE web research patterns
        # This prevents "what is your name" from triggering web search
        if self._is_conversational(prompt):
            return ClassifiedIntent(
                intent_type=IntentType.CHAT,
                confidence=0.95,
                original_prompt=prompt,
                tier_override=tier_override,
                needs_web=False
            )

        # Try fast rule-based classification first
        rule_result = self._classify_by_rules(prompt)
        if rule_result and rule_result.confidence >= 0.8:
            rule_result.tier_override = tier_override
            return rule_result

        # Check for time-sensitive queries that require current information
        if self._requires_current_info(prompt):
            return ClassifiedIntent(
                intent_type=IntentType.WEB_RESEARCH,
                confidence=0.9,
                original_prompt=prompt,
                tier_override=tier_override,
                needs_web=True,
                target=prompt
            )

        # Check for short conversational prompts
        if len(prompt.split()) < 5 and not self._has_action_indicators(prompt):
            return ClassifiedIntent(
                intent_type=IntentType.CHAT,
                confidence=0.85,
                original_prompt=prompt,
                tier_override=tier_override
            )

        # Use LLM for ambiguous cases
        if self.llm_client:
            llm_result = self._classify_by_llm(prompt, context)
            llm_result.tier_override = tier_override
            return llm_result

        # Fallback to rule-based with lower confidence
        if rule_result:
            rule_result.confidence = min(rule_result.confidence, 0.6)
            rule_result.tier_override = tier_override
            return rule_result

        # Default to chat
        return ClassifiedIntent(
            intent_type=IntentType.CHAT,
            confidence=0.5,
            original_prompt=prompt,
            tier_override=tier_override
        )

    def _handle_slash_command(self, prompt: str) -> ClassifiedIntent:
        """Handle slash commands"""
        parts = prompt.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd in self.SLASH_COMMANDS:
            return ClassifiedIntent(
                intent_type=IntentType.SYSTEM_TASK,
                confidence=1.0,
                target=self.SLASH_COMMANDS[cmd],
                flags={'args': args, 'is_slash_command': True},
                original_prompt=prompt
            )

        # Handle /tier specifically
        if cmd == '/tier' and args:
            tier = self._detect_tier_override(args)
            return ClassifiedIntent(
                intent_type=IntentType.SYSTEM_TASK,
                confidence=1.0,
                target='set_tier',
                flags={'tier': tier, 'is_slash_command': True},
                original_prompt=prompt,
                tier_override=tier
            )

        # Unknown slash command - treat as chat
        return ClassifiedIntent(
            intent_type=IntentType.CHAT,
            confidence=0.7,
            original_prompt=prompt,
            flags={'unknown_command': cmd}
        )

    def _detect_tier_override(self, prompt: str) -> Optional[str]:
        """Detect if user wants to override model tier"""
        prompt_lower = prompt.lower()

        # Check for explicit tier keywords
        for keyword, tier in self.TIER_KEYWORDS.items():
            # Only match if part of a tier request pattern
            patterns = [
                f'use {keyword}',
                f'switch to {keyword}',
                f'tier {keyword}',
                f'--tier {keyword}',
                f'{keyword} model',
                f'{keyword} mode',
            ]
            for pattern in patterns:
                if pattern in prompt_lower:
                    return tier

        return None

    def _classify_by_rules(self, prompt: str) -> Optional[ClassifiedIntent]:
        """Fast rule-based classification for obvious cases"""
        prompt_lower = prompt.lower()

        for intent_type, patterns in self.OBVIOUS_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, prompt_lower, re.IGNORECASE):
                    target = self._extract_target(prompt, intent_type)
                    return ClassifiedIntent(
                        intent_type=intent_type,
                        confidence=0.85,
                        target=target,
                        original_prompt=prompt,
                        needs_web=intent_type == IntentType.WEB_RESEARCH
                    )

        return None

    def _classify_by_llm(self, prompt: str, context: Optional[Dict] = None) -> ClassifiedIntent:
        """Use LLM to classify ambiguous prompts"""
        classification_prompt = self._build_classification_prompt(prompt, context)

        try:
            response = self.llm_client.generate(
                prompt=classification_prompt,
                system="You are an intent classifier. Respond ONLY with valid JSON.",
                max_tokens=200,
                temperature=0.1
            )

            result = self._parse_llm_classification(response, prompt)
            return result

        except Exception as e:
            # Fallback to chat on error
            return ClassifiedIntent(
                intent_type=IntentType.CHAT,
                confidence=0.5,
                original_prompt=prompt,
                flags={'classification_error': str(e)}
            )

    def _build_classification_prompt(self, prompt: str, context: Optional[Dict] = None) -> str:
        """Build prompt for LLM classification"""
        return f"""Classify this user request into one intent type.

User Request: "{prompt}"

Intent Types:
- CHAT: General conversation, questions, brainstorming
- CODE_EDIT: Refactoring, bug fixes, writing code/tests
- CONFIG_EDIT: Editing system configs (hyprland, waybar, shell)
- FILE_OPS: Finding, opening, creating, moving files
- WEB_RESEARCH: Searching web, scraping pages
- SYSTEM_TASK: Running tests, diagnostics, cleanup
- KNOWLEDGE_RAG: Saving or searching personal notes
- PERSONAL_CHAT: Personal/uncensored conversation

Respond with JSON only:
{{"type": "INTENT_TYPE", "confidence": 0.0-1.0, "target": "what to act on or null", "needs_web": true/false}}"""

    def _parse_llm_classification(self, response: str, original_prompt: str) -> ClassifiedIntent:
        """Parse LLM classification response"""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response)
            if json_match:
                data = json.loads(json_match.group())

                intent_type_str = data.get('type', 'CHAT').upper()
                intent_type = IntentType[intent_type_str] if intent_type_str in IntentType.__members__ else IntentType.CHAT

                return ClassifiedIntent(
                    intent_type=intent_type,
                    confidence=float(data.get('confidence', 0.7)),
                    target=data.get('target'),
                    original_prompt=original_prompt,
                    needs_web=data.get('needs_web', False)
                )

        except (json.JSONDecodeError, KeyError, ValueError):
            pass

        # Default fallback
        return ClassifiedIntent(
            intent_type=IntentType.CHAT,
            confidence=0.5,
            original_prompt=original_prompt
        )

    def _extract_target(self, prompt: str, intent_type: IntentType) -> Optional[str]:
        """Extract target from prompt based on intent type"""
        prompt_lower = prompt.lower()

        # Remove common action verbs to get target
        action_verbs = [
            'open', 'edit', 'find', 'show', 'locate', 'where is',
            'refactor', 'debug', 'implement', 'fix', 'write',
            'search', 'google', 'look up', 'browse', 'scrape',
            'run', 'check', 'diagnose', 'cleanup', 'optimize',
            'please', 'can you', 'could you', 'i want to', 'i need to'
        ]

        target = prompt
        for verb in action_verbs:
            target = re.sub(rf'^{verb}\s+', '', target, flags=re.IGNORECASE)
            target = re.sub(rf'\s+{verb}\s+', ' ', target, flags=re.IGNORECASE)

        target = target.strip()
        return target if target and target != prompt_lower else None

    def _is_conversational(self, prompt: str) -> bool:
        """
        Check if the prompt is conversational and should NOT trigger web search.

        This includes:
        - Questions about the AI itself ("what is your name")
        - Greetings and social exchanges
        - Simple responses (yes, no, ok)
        - Help requests about the tool
        """
        prompt_lower = prompt.lower().strip()

        for pattern in self.CONVERSATIONAL_PATTERNS:
            if re.search(pattern, prompt_lower, re.IGNORECASE):
                return True

        return False

    def _requires_current_info(self, prompt: str) -> bool:
        """
        Check if the prompt requires current/real-time information from the web.

        This includes queries with time-sensitive keywords like:
        - "current", "latest", "recent"
        - "today", "now", "as of today"
        - References to current years
        - "What is the current/latest..."
        """
        prompt_lower = prompt.lower().strip()

        for pattern in self.TIME_SENSITIVE_PATTERNS:
            if re.search(pattern, prompt_lower, re.IGNORECASE):
                return True

        return False

    def _is_greeting(self, prompt: str) -> bool:
        """Check if prompt is a simple greeting"""
        greetings = {
            'hello', 'hi', 'hey', 'howdy', 'greetings', 'sup',
            'good morning', 'good afternoon', 'good evening',
            'hallo', 'moin', 'servus', 'guten tag'
        }
        cleaned = prompt.lower().strip().rstrip('!.,?')
        return cleaned in greetings

    def _has_action_indicators(self, prompt: str) -> bool:
        """Check if prompt contains action indicators"""
        action_indicators = [
            'open', 'edit', 'find', 'show', 'run', 'check',
            'refactor', 'debug', 'search', 'browse', 'fix',
            'create', 'delete', 'move', 'copy', 'install',
            'configure', 'setup', 'analyze', 'optimize'
        ]
        prompt_lower = prompt.lower()
        return any(indicator in prompt_lower for indicator in action_indicators)
