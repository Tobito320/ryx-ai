"""
Ryx AI - LLM-based Intent Classifier
Replaces brittle keyword lists with minimal rules + LLM classification
"""

import json
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class IntentType(Enum):
    """Intent types for routing"""
    CHAT = "CHAT"
    CODE_EDIT = "CODE_EDIT"
    CONFIG_EDIT = "CONFIG_EDIT"
    FILE_OPS = "FILE_OPS"
    WEB_RESEARCH = "WEB_RESEARCH"
    SYSTEM_TASK = "SYSTEM_TASK"
    KNOWLEDGE = "KNOWLEDGE"
    PERSONAL_CHAT = "PERSONAL_CHAT"


@dataclass
class ClassifiedIntent:
    """Result of intent classification"""
    intent_type: IntentType
    confidence: float
    needs_web: bool = False
    needs_rag: bool = False
    complexity: float = 0.5
    target: Optional[str] = None
    flags: Dict[str, Any] = field(default_factory=dict)
    original_prompt: str = ""
    tier_override: Optional[str] = None


class IntentClassifier:
    """
    LLM-centric intent classifier with minimal rule layer
    
    Strategy:
    1. Quick rule check for obvious patterns (greetings, short commands)
    2. LLM classification for ambiguous cases
    3. Returns intent type, confidence, and optional flags
    """
    
    # Minimal rule patterns for obvious cases only
    GREETING_PATTERNS = {
        'hello', 'hi', 'hey', 'howdy', 'greetings', 'sup', 'yo',
        'good morning', 'good evening', 'good afternoon'
    }
    
    # Obvious action verbs that strongly indicate intent
    CODE_EDIT_VERBS = {'refactor', 'implement', 'fix bug', 'add feature', 'write test', 'debug'}
    CONFIG_EDIT_VERBS = {'configure', 'update config', 'edit config', 'change settings'}
    FILE_OPS_VERBS = {'find file', 'create file', 'move file', 'delete file', 'list files', 'open'}
    SYSTEM_VERBS = {'run test', 'build', 'deploy', 'install', 'diagnose', 'cleanup'}
    WEB_VERBS = {'search web', 'look up', 'google', 'find online', 'research'}
    
    # Config file indicators
    CONFIG_INDICATORS = {
        'hyprland', 'waybar', 'kitty', '.config', 'dotfile', 'bashrc', 
        'zshrc', 'nvim', 'config', '.conf', 'settings'
    }
    
    # Personal/uncensored indicators
    PERSONAL_INDICATORS = {
        'personal', 'private', 'uncensored', 'honest opinion', 'no filter',
        'between us', 'off the record'
    }
    
    def __init__(self):
        """Initialize the intent classifier"""
        self.classification_prompt = self._build_classification_prompt()
    
    def _build_classification_prompt(self) -> str:
        """Build the system prompt for LLM-based classification"""
        return """You are an intent classifier for a CLI assistant.

Classify the user's prompt into ONE of these intent types:
- CHAT: General conversation, questions, brainstorming
- CODE_EDIT: Refactoring, adding features, fixing bugs, writing code
- CONFIG_EDIT: Editing system configs (Hyprland, Waybar, shell configs, dotfiles)
- FILE_OPS: Finding, opening, creating, moving files
- WEB_RESEARCH: Searching the web, scraping pages
- SYSTEM_TASK: Running tests, diagnostics, system commands
- KNOWLEDGE: Saving or searching notes/knowledge base
- PERSONAL_CHAT: Uncensored personal conversation

Respond ONLY with valid JSON:
{
  "intent_type": "CHAT|CODE_EDIT|CONFIG_EDIT|FILE_OPS|WEB_RESEARCH|SYSTEM_TASK|KNOWLEDGE|PERSONAL_CHAT",
  "confidence": 0.0-1.0,
  "needs_web": true/false,
  "needs_rag": true/false,
  "complexity": 0.0-1.0,
  "target": "optional target file/config/topic"
}

Examples:
"refactor the intent parser" -> {"intent_type": "CODE_EDIT", "confidence": 0.95, "needs_web": false, "needs_rag": false, "complexity": 0.7, "target": "intent parser"}
"what's the weather?" -> {"intent_type": "WEB_RESEARCH", "confidence": 0.9, "needs_web": true, "needs_rag": false, "complexity": 0.2, "target": null}
"update my hyprland config" -> {"intent_type": "CONFIG_EDIT", "confidence": 0.95, "needs_web": false, "needs_rag": false, "complexity": 0.5, "target": "hyprland config"}
"tell me about yourself" -> {"intent_type": "CHAT", "confidence": 0.9, "needs_web": false, "needs_rag": false, "complexity": 0.2, "target": null}
"""
    
    def classify(self, prompt: str, ollama_client=None) -> ClassifiedIntent:
        """
        Classify user prompt to determine intent
        
        Args:
            prompt: User's natural language prompt
            ollama_client: Optional Ollama client for LLM classification
            
        Returns:
            ClassifiedIntent with type, confidence, and flags
        """
        prompt_lower = prompt.lower().strip()
        prompt_stripped = prompt_lower.rstrip('!.,?')
        
        # Layer 1: Quick rule checks for obvious patterns
        
        # Check for greetings (instant response, no AI needed)
        if prompt_stripped in self.GREETING_PATTERNS or len(prompt_stripped.split()) <= 2:
            if any(g in prompt_stripped for g in self.GREETING_PATTERNS):
                return ClassifiedIntent(
                    intent_type=IntentType.CHAT,
                    confidence=1.0,
                    complexity=0.1,
                    original_prompt=prompt,
                    flags={'is_greeting': True}
                )
        
        # Check for tier override commands
        tier_override = self._check_tier_override(prompt_lower)
        if tier_override:
            return ClassifiedIntent(
                intent_type=IntentType.CHAT,
                confidence=1.0,
                complexity=0.1,
                original_prompt=prompt,
                tier_override=tier_override,
                flags={'tier_switch': True}
            )
        
        # Check for obvious action verbs
        rule_result = self._check_obvious_patterns(prompt_lower)
        if rule_result and rule_result.confidence >= 0.9:
            rule_result.original_prompt = prompt
            return rule_result
        
        # Layer 2: LLM-based classification for ambiguous cases
        if ollama_client:
            llm_result = self._classify_with_llm(prompt, ollama_client)
            if llm_result:
                llm_result.original_prompt = prompt
                return llm_result
        
        # Layer 3: Fallback to rule-based with lower confidence
        if rule_result:
            rule_result.original_prompt = prompt
            rule_result.confidence *= 0.8  # Lower confidence for fallback
            return rule_result
        
        # Default to CHAT with medium confidence
        return ClassifiedIntent(
            intent_type=IntentType.CHAT,
            confidence=0.6,
            complexity=self._estimate_complexity(prompt),
            original_prompt=prompt
        )
    
    def _check_tier_override(self, prompt_lower: str) -> Optional[str]:
        """Check if user is requesting a specific tier"""
        tier_patterns = {
            'fast': ['use fast', 'fast model', 'quick model', 'tier fast'],
            'balanced': ['use balanced', 'balanced model', 'tier balanced', 'default model'],
            'powerful': ['use powerful', 'powerful model', 'tier powerful', 'strong model'],
            'ultra': ['use ultra', 'ultra model', 'tier ultra', 'biggest model', 'best model'],
            'uncensored': ['use uncensored', 'uncensored model', 'tier uncensored', 'no filter']
        }
        
        for tier, patterns in tier_patterns.items():
            if any(p in prompt_lower for p in patterns):
                return tier
        
        return None
    
    def _check_obvious_patterns(self, prompt_lower: str) -> Optional[ClassifiedIntent]:
        """Check for obvious patterns that don't need LLM"""
        
        # Check CODE_EDIT patterns
        if any(v in prompt_lower for v in self.CODE_EDIT_VERBS):
            return ClassifiedIntent(
                intent_type=IntentType.CODE_EDIT,
                confidence=0.95,
                complexity=self._estimate_complexity(prompt_lower),
                target=self._extract_target(prompt_lower)
            )
        
        # Check CONFIG_EDIT patterns
        if any(v in prompt_lower for v in self.CONFIG_EDIT_VERBS):
            return ClassifiedIntent(
                intent_type=IntentType.CONFIG_EDIT,
                confidence=0.95,
                complexity=0.5,
                target=self._extract_config_target(prompt_lower)
            )
        
        # Check if mentions config files without explicit verbs
        if any(ind in prompt_lower for ind in self.CONFIG_INDICATORS):
            # Editing intent with config indicator
            if any(w in prompt_lower for w in ['edit', 'change', 'modify', 'update', 'fix']):
                return ClassifiedIntent(
                    intent_type=IntentType.CONFIG_EDIT,
                    confidence=0.85,
                    complexity=0.5,
                    target=self._extract_config_target(prompt_lower)
                )
            # Just looking at config
            elif any(w in prompt_lower for w in ['open', 'show', 'find', 'where', 'look at']):
                return ClassifiedIntent(
                    intent_type=IntentType.FILE_OPS,
                    confidence=0.85,
                    complexity=0.3,
                    target=self._extract_config_target(prompt_lower)
                )
        
        # Check FILE_OPS patterns
        if any(v in prompt_lower for v in self.FILE_OPS_VERBS):
            return ClassifiedIntent(
                intent_type=IntentType.FILE_OPS,
                confidence=0.9,
                complexity=0.3,
                target=self._extract_target(prompt_lower)
            )
        
        # Check SYSTEM_TASK patterns
        if any(v in prompt_lower for v in self.SYSTEM_VERBS):
            return ClassifiedIntent(
                intent_type=IntentType.SYSTEM_TASK,
                confidence=0.9,
                complexity=0.5,
                target=self._extract_target(prompt_lower)
            )
        
        # Check WEB_RESEARCH patterns
        if any(v in prompt_lower for v in self.WEB_VERBS):
            return ClassifiedIntent(
                intent_type=IntentType.WEB_RESEARCH,
                confidence=0.9,
                needs_web=True,
                complexity=0.4,
                target=self._extract_target(prompt_lower)
            )
        
        # Check PERSONAL_CHAT patterns
        if any(ind in prompt_lower for ind in self.PERSONAL_INDICATORS):
            return ClassifiedIntent(
                intent_type=IntentType.PERSONAL_CHAT,
                confidence=0.85,
                complexity=0.3
            )
        
        return None
    
    def _classify_with_llm(self, prompt: str, ollama_client) -> Optional[ClassifiedIntent]:
        """Use LLM for classification of ambiguous prompts"""
        try:
            # Use a fast model for classification
            response = ollama_client.generate(
                model="mistral:7b",  # Fast model for classification
                prompt=f"{self.classification_prompt}\n\nClassify this prompt:\n\"{prompt}\"",
                stream=False,
                options={
                    "temperature": 0.1,  # Low temperature for consistent classification
                    "num_predict": 256
                }
            )
            
            if response and 'response' in response:
                # Parse JSON from response
                response_text = response['response']
                # Extract JSON from response
                json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
                if json_match:
                    classification = json.loads(json_match.group())
                    
                    intent_type = IntentType[classification.get('intent_type', 'CHAT')]
                    
                    return ClassifiedIntent(
                        intent_type=intent_type,
                        confidence=float(classification.get('confidence', 0.7)),
                        needs_web=bool(classification.get('needs_web', False)),
                        needs_rag=bool(classification.get('needs_rag', False)),
                        complexity=float(classification.get('complexity', 0.5)),
                        target=classification.get('target')
                    )
        except Exception as e:
            # Silently fall back to rule-based
            pass
        
        return None
    
    def _estimate_complexity(self, prompt: str) -> float:
        """Estimate task complexity from prompt characteristics"""
        complexity = 0.3  # Base complexity
        
        words = prompt.split()
        
        # Length factor
        if len(words) > 20:
            complexity += 0.2
        elif len(words) > 10:
            complexity += 0.1
        
        # Complex indicators
        complex_words = ['refactor', 'architecture', 'design', 'analyze', 'optimize', 
                        'implement', 'multiple', 'all', 'entire', 'whole']
        if any(w in prompt.lower() for w in complex_words):
            complexity += 0.2
        
        # Code indicators
        if '```' in prompt or 'function' in prompt.lower() or 'class' in prompt.lower():
            complexity += 0.15
        
        # Multi-step indicators
        if ' and ' in prompt.lower() or ' then ' in prompt.lower():
            complexity += 0.1
        
        return min(1.0, complexity)
    
    def _extract_target(self, prompt_lower: str) -> Optional[str]:
        """Extract the target of the action"""
        # Remove common action words
        action_words = ['please', 'can you', 'could you', 'i want to', 'i need to',
                       'help me', 'show me', 'find', 'open', 'edit', 'create', 'move']
        
        result = prompt_lower
        for word in action_words:
            result = result.replace(word, ' ')
        
        # Clean up
        result = ' '.join(result.split())
        return result.strip() if result.strip() else None
    
    def _extract_config_target(self, prompt_lower: str) -> Optional[str]:
        """Extract config file target"""
        for config in self.CONFIG_INDICATORS:
            if config in prompt_lower:
                return config
        return None
