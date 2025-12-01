"""
Ryx AI - Intent Parser
Parses user prompts to determine intended action before querying AI
"""

from dataclasses import dataclass
from typing import List, Optional
import re


@dataclass
class Intent:
    """Represents parsed user intent"""
    action: str  # 'chat', 'locate', 'execute', 'browse'
    target: Optional[str] = None  # What to act on (e.g., "hyprland config")
    modifiers: List[str] = None  # Additional flags like "new_terminal"
    original_prompt: str = ""  # Original user input
    model_switch: Optional[str] = None  # If user requested model switch

    def __post_init__(self):
        if self.modifiers is None:
            self.modifiers = []


class IntentParser:
    """Parse user intent from natural language prompts"""

    # Action keywords that determine what to do
    EXECUTE_KEYWORDS = ['open', 'edit', 'run', 'execute', 'launch', 'start']
    BROWSE_KEYWORDS = ['look up', 'browse', 'google', 'search', 'what is', 'who is', 'search for']
    LOCATE_KEYWORDS = ['find', 'where is', 'show me', 'locate', 'path to', 'where']

    # Non-action compound phrases containing action keywords (e.g., "open source" is not an action)
    # These phrases should be excluded from triggering action keyword detection.
    NON_ACTION_PHRASES = ['open source']

    # Modifier keywords that change how action is performed
    NEW_TERMINAL_KEYWORDS = ['new terminal', 'new window', 'separate terminal', 'separate window']

    # Model fallback chains (if preferred model not available, try these in order)
    MODEL_FALLBACKS = {
        'gpt-oss:20b': ['SimonPu/Qwen3-Coder:30B-Instruct_Q4_K_XL', 'deepseek-coder:6.7b', 'qwen2.5:3b', 'qwen2.5:1.5b'],
        'SimonPu/Qwen3-Coder:30B-Instruct_Q4_K_XL': ['gpt-oss:20b', 'deepseek-coder:6.7b', 'qwen2.5:3b', 'qwen2.5:1.5b'],
        'deepseek-coder:6.7b': ['qwen2.5:3b', 'qwen2.5:1.5b'],
        'qwen2.5:3b': ['qwen2.5:1.5b'],
        'qwen2.5:1.5b': [],  # Smallest model, no fallback
    }

    # Model switching keywords - maps user terms to actual model names
    MODEL_SWITCH_KEYWORDS = {
        # Specific model names
        'deepseek': 'deepseek-coder:6.7b',
        'qwen': 'qwen2.5:1.5b',
        'gpt-oss': 'gpt-oss:20b',
        'gpt oss': 'gpt-oss:20b',
        'llama': 'llama3.2:1b',
        'phi3': 'phi3:mini',

        # Size-based (try to find biggest available)
        'strongest': 'gpt-oss:20b',  # Largest model
        'smartest': 'gpt-oss:20b',   # Largest model
        'biggest': 'gpt-oss:20b',    # Largest model
        'best': 'gpt-oss:20b',       # Largest model
        'most powerful': 'gpt-oss:20b',
        'higher': 'deepseek-coder:6.7b',  # Next tier up
        'better': 'deepseek-coder:6.7b',  # Next tier up
        'stronger': 'deepseek-coder:6.7b',

        # Speed/performance
        'fast': 'qwen2.5:1.5b',
        'faster': 'qwen2.5:1.5b',
        'quick': 'qwen2.5:1.5b',
        'small': 'qwen2.5:1.5b',

        # Balanced
        'balanced': 'deepseek-coder:6.7b',
        'medium': 'deepseek-coder:6.7b',
        'moderate': 'deepseek-coder:6.7b',

        # Coding-specific
        'coder': 'deepseek-coder:6.7b',
        'coding': 'deepseek-coder:6.7b',

        # Compatibility with session mode names
        'powerful': 'gpt-oss:20b',
        'strong': 'deepseek-coder:6.7b',
    }

    def parse(self, prompt: str) -> Intent:
        """
        Parse prompt to determine user intent

        Args:
            prompt: User's natural language prompt

        Returns:
            Intent object with action, target, and modifiers
        """
        prompt_lower = prompt.lower()

        # Check for model switching first
        model_switch = self._detect_model_switch(prompt_lower)
        if model_switch:
            # Remove model switch request from prompt
            cleaned_prompt = self._remove_model_switch_text(prompt, prompt_lower)

            # If the cleaned prompt is empty or very short (just filler words), treat it as pure model switch
            cleaned_stripped = cleaned_prompt.strip()
            filler_words = ['please', 'now', 'i', 'want', 'to', 'the', 'model', 'a']
            remaining_words = [w for w in cleaned_stripped.lower().split() if w not in filler_words]

            if not cleaned_stripped or len(remaining_words) == 0:
                # Just a model switch request, no other action
                return Intent(
                    action='model_switch',
                    model_switch=model_switch,
                    original_prompt=prompt
                )
            else:
                # Continue with remaining prompt
                prompt = cleaned_prompt
                prompt_lower = prompt.lower()

        # Detect modifiers
        modifiers = []
        if any(kw in prompt_lower for kw in self.NEW_TERMINAL_KEYWORDS):
            modifiers.append('new_terminal')

        # Determine action based on keywords
        action = self._detect_action(prompt_lower)

        # Extract target (what user wants to act on)
        target = self._extract_target(prompt, action)

        return Intent(
            action=action,
            target=target,
            modifiers=modifiers,
            original_prompt=prompt,
            model_switch=model_switch
        )

    def _detect_action(self, prompt_lower: str) -> str:
        """Detect the intended action from prompt"""

        # Mask non-action compound phrases (e.g., "open source") to prevent false positives.
        # We replace them with placeholder text so action keywords within them are not detected.
        masked_prompt = prompt_lower
        for phrase in self.NON_ACTION_PHRASES:
            masked_prompt = masked_prompt.replace(phrase, '_MASKED_')

        # For informational queries containing 'find' (e.g., "where can I find X?"),
        # prefer 'locate' over 'execute' to avoid misclassifying questions as actions.
        if self._is_informational_find_query(prompt_lower):
            return 'locate'

        # Check execute keywords first (most specific), using masked prompt
        if any(kw in masked_prompt for kw in self.EXECUTE_KEYWORDS):
            return 'execute'

        # Check browse keywords, using masked prompt for consistency
        if any(kw in masked_prompt for kw in self.BROWSE_KEYWORDS):
            return 'browse'

        # Check locate keywords, using masked prompt for consistency
        if any(kw in masked_prompt for kw in self.LOCATE_KEYWORDS):
            return 'locate'

        # Check if prompt mentions a config file or path (implicit locate)
        if self._is_implicit_locate(prompt_lower):
            return 'locate'

        # Default to chat (just conversation)
        return 'chat'

    def _is_informational_find_query(self, prompt_lower: str) -> bool:
        """
        Check if the prompt is an informational query containing 'find'.
        Examples: "where can I find X?", "how do I find X?"
        These should return 'locate' rather than potentially triggering 'execute'.
        
        If explicit execute verbs (edit, run, execute, launch, start) are present,
        the query should be treated as an execute command, not an informational query.
        """
        import re
        
        # Question patterns that suggest the user is asking for location/information
        informational_patterns = ['where can i find', 'where do i find', 'how can i find', 'how do i find']
        
        if not any(pattern in prompt_lower for pattern in informational_patterns):
            return False
        
        # Check if explicit execute verbs are present (as whole words)
        # If so, the user wants to execute something, not just locate it
        explicit_execute_verbs = ['edit', 'run', 'execute', 'launch', 'start']
        for verb in explicit_execute_verbs:
            # Use word boundary matching to avoid false positives like 'startup' for 'start'
            if re.search(rf'\b{verb}\b', prompt_lower):
                return False
        
        return True

    def _is_implicit_locate(self, prompt_lower: str) -> bool:
        """
        Check if prompt is implicitly asking for file location
        e.g., "hyprland config" without "open" should just locate
        FIXED: Now excludes conversational patterns to prevent false positives
        """
        # Exclude common conversational patterns
        conversation_starters = [
            'i need', 'i want', 'help me', 'how do', 'how can',
            'what is', 'tell me', 'show me how', 'can you', 'could you'
        ]

        # If it starts with conversation, it's not a file query
        for starter in conversation_starters:
            if prompt_lower.startswith(starter):
                return False

        # Common file-related terms
        file_indicators = ['config', 'configuration', '.conf', 'settings', 'dotfile', 'rc']

        words = prompt_lower.split()

        # Tighter constraints: 2-3 words AND no action verbs
        if 2 <= len(words) <= 3:
            has_file_indicator = any(ind in prompt_lower for ind in file_indicators)
            has_action_verb = any(kw in prompt_lower for kw in
                                 self.EXECUTE_KEYWORDS + self.BROWSE_KEYWORDS)

            # Only locate if: has file indicator AND no action verb
            return has_file_indicator and not has_action_verb

        return False

    def _extract_target(self, prompt: str, action: str) -> Optional[str]:
        """Extract what the user wants to act on"""

        if action == 'chat':
            return None

        # Remove action keywords to get target
        prompt_lower = prompt.lower()

        # Remove execute keywords
        for kw in self.EXECUTE_KEYWORDS:
            if kw in prompt_lower:
                prompt = prompt.replace(kw, '', 1)
                prompt_lower = prompt.lower()

        # Remove browse keywords
        for kw in self.BROWSE_KEYWORDS:
            if kw in prompt_lower:
                prompt = prompt.replace(kw, '', 1)
                prompt_lower = prompt.lower()

        # Remove locate keywords
        for kw in self.LOCATE_KEYWORDS:
            if kw in prompt_lower:
                prompt = prompt.replace(kw, '', 1)
                prompt_lower = prompt.lower()

        # Remove modifier keywords
        for kw in self.NEW_TERMINAL_KEYWORDS:
            if kw in prompt_lower:
                prompt_lower = prompt_lower.replace(kw, '')
                prompt = re.sub(re.escape(kw), '', prompt, flags=re.IGNORECASE)

        # Clean up extra whitespace
        target = ' '.join(prompt.split())

        return target.strip() if target.strip() else None

    def _detect_model_switch(self, prompt_lower: str) -> Optional[str]:
        """Detect if user wants to switch models"""

        # Patterns that indicate model switching
        switch_patterns = [
            'switch to',
            'use',
            'change to',
            'let me talk to',
            'talk to',
            'i want to use',
            'i wanna use',
            'now use',
            'please use',
            'please switch to',
        ]

        # Check if any switch pattern is present
        has_switch_pattern = any(pattern in prompt_lower for pattern in switch_patterns)

        if has_switch_pattern:
            # Look for model keywords in order of specificity (most specific first)
            # Check multi-word patterns first
            for keyword, model in sorted(self.MODEL_SWITCH_KEYWORDS.items(), key=lambda x: -len(x[0])):
                if keyword in prompt_lower:
                    return model

        return None

    def get_best_available_model(self, requested_model: str, available_models: List[str]) -> Optional[str]:
        """
        Get the best available alternative if requested model is not available

        Args:
            requested_model: The model user requested
            available_models: List of available models

        Returns:
            Best available alternative, or None if no alternatives
        """
        # If requested model is available, return it
        if requested_model in available_models:
            return requested_model

        # Try fallback chain
        fallbacks = self.MODEL_FALLBACKS.get(requested_model, [])
        for fallback in fallbacks:
            if fallback in available_models:
                return fallback

        # No specific fallback found, try to find any available model in order of preference
        preference_order = [
            'gpt-oss:20b',
            'SimonPu/Qwen3-Coder:30B-Instruct_Q4_K_XL',
            'deepseek-coder:6.7b',
            'qwen2.5:3b',
            'qwen2.5:1.5b',
            'llama3.2:1b',
            'phi3:mini'
        ]

        for preferred in preference_order:
            if preferred in available_models:
                return preferred

        # Return first available model as last resort
        return available_models[0] if available_models else None

    def _remove_model_switch_text(self, prompt: str, prompt_lower: str) -> str:
        """Remove model switch request from prompt"""

        # Common patterns to remove (more comprehensive)
        patterns = [
            r'please\s+switch\s+to\s+\w+(?:\s+\w+)?',  # "please switch to X" or "please switch to X Y"
            r'switch\s+to\s+\w+(?:\s+\w+)?',           # "switch to X" or "switch to X Y"
            r'use\s+\w+(?:\s+\w+)?\s+model',           # "use X model" or "use X Y model"
            r'use\s+\w+(?:\s+\w+)?',                   # "use X" or "use X Y"
            r'change\s+to\s+\w+(?:\s+\w+)?',           # "change to X" or "change to X Y"
            r'let\s+me\s+talk\s+to\s+\w+(?:\s+\w+)?',  # "let me talk to X"
            r'talk\s+to\s+\w+(?:\s+\w+)?',             # "talk to X"
            r'i\s+want\s+to\s+use\s+\w+(?:\s+\w+)?',   # "i want to use X"
            r'i\s+wanna\s+use\s+\w+(?:\s+\w+)?',       # "i wanna use X"
            r'now\s+use\s+\w+(?:\s+\w+)?',             # "now use X"
        ]

        for pattern in patterns:
            prompt = re.sub(pattern, '', prompt, flags=re.IGNORECASE)

        # Clean up punctuation and extra spaces
        prompt = re.sub(r'\s*,\s*$', '', prompt)  # Remove trailing comma
        prompt = re.sub(r'\s+', ' ', prompt)  # Normalize whitespace
        prompt = re.sub(r'^\s*and\s+', '', prompt, flags=re.IGNORECASE)  # Remove leading "and"

        return prompt.strip()
