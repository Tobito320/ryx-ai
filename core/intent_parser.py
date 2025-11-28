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

    # Modifier keywords that change how action is performed
    NEW_TERMINAL_KEYWORDS = ['new terminal', 'new window', 'separate terminal', 'separate window']

    # Model switching keywords
    MODEL_SWITCH_KEYWORDS = {
        'deepseek': 'deepseek-coder:6.7b',
        'qwen': 'qwen2.5:1.5b',
        'fast': 'qwen2.5:1.5b',
        'powerful': 'deepseek-coder:6.7b',
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
            if cleaned_prompt.strip():
                # Continue with remaining prompt
                prompt = cleaned_prompt
                prompt_lower = prompt.lower()
            else:
                # Just a model switch request, no other action
                return Intent(
                    action='model_switch',
                    model_switch=model_switch,
                    original_prompt=prompt
                )

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

        # Check execute keywords first (most specific)
        if any(kw in prompt_lower for kw in self.EXECUTE_KEYWORDS):
            return 'execute'

        # Check browse keywords
        if any(kw in prompt_lower for kw in self.BROWSE_KEYWORDS):
            return 'browse'

        # Check locate keywords
        if any(kw in prompt_lower for kw in self.LOCATE_KEYWORDS):
            return 'locate'

        # Check if prompt mentions a config file or path (implicit locate)
        if self._is_implicit_locate(prompt_lower):
            return 'locate'

        # Default to chat (just conversation)
        return 'chat'

    def _is_implicit_locate(self, prompt_lower: str) -> bool:
        """
        Check if prompt is implicitly asking for file location
        e.g., "hyprland config" without "open" should just locate
        """
        # Common file-related terms
        file_indicators = ['config', 'configuration', '.conf', 'settings', 'dotfile']

        # Check if prompt is short and mentions a file
        words = prompt_lower.split()
        if len(words) <= 4 and any(indicator in prompt_lower for indicator in file_indicators):
            return True

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

        # Check for explicit switch keywords
        if 'switch to' in prompt_lower or 'use' in prompt_lower or 'change to' in prompt_lower:
            for keyword, model in self.MODEL_SWITCH_KEYWORDS.items():
                if keyword in prompt_lower:
                    return model

        return None

    def _remove_model_switch_text(self, prompt: str, prompt_lower: str) -> str:
        """Remove model switch request from prompt"""

        # Common patterns to remove
        patterns = [
            r'switch to \w+',
            r'use \w+ model',
            r'use \w+',
            r'change to \w+',
            r'please switch to \w+',
            r'please use \w+',
        ]

        for pattern in patterns:
            prompt = re.sub(pattern, '', prompt, flags=re.IGNORECASE)

        # Clean up punctuation and extra spaces
        prompt = re.sub(r'\s*,\s*$', '', prompt)  # Remove trailing comma
        prompt = re.sub(r'\s+', ' ', prompt)  # Normalize whitespace

        return prompt.strip()
